"""Main loop: consume the detection stream, run the Tier 1 gate per camera,
trigger clip-recorder on a rising edge, and classify + publish once the clip
is ready. Runs as a plain script (no HTTP server) plus a tiny FastAPI app for
health checks, matching the other services' probe shape.
"""
import json
import os
import threading
import time
import uuid
from typing import Dict

import requests
from fastapi import FastAPI, Request

from .classifier import load_classifier
from .decision import GateState, decide, tier1_gate
from .zmq_client import iter_messages, persons, subscribe

ZMQ_HOST = os.environ.get("ZMQ_SUB_HOST", "localhost")
ZMQ_PORT = int(os.environ.get("ZMQ_SUB_PORT", "5555"))
ZMQ_TOPIC = os.environ.get("ZMQ_TOPIC", "detections")
CAMERA_ID = os.environ.get("CAMERA_ID", "cam-1")
RECORDER_URL = os.environ.get("RECORDER_URL", "http://clip-recorder:8080")
PUBLISHER_URL = os.environ.get("PUBLISHER_URL", "http://event-publisher:8080")
HIGH = float(os.environ.get("THRESHOLD_HIGH", "0.85"))
SUSPICIOUS = float(os.environ.get("THRESHOLD_SUSPICIOUS", "0.50"))
PERSONS_MIN = int(os.environ.get("GATE_PERSONS_MIN", "2"))
MOTION_MIN = float(os.environ.get("GATE_MOTION_MIN", "8.0"))
COOLDOWN_S = float(os.environ.get("COOLDOWN_S", "30"))
POSTROLL_S = float(os.environ.get("POSTROLL_S", "4"))

clf = load_classifier()
last_trigger: Dict[str, float] = {}
pending_tier1: Dict[str, dict] = {}  # event_id -> tier1 context, until the clip callback


def create_app() -> FastAPI:
    app = FastAPI(title="aggression-detector")

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.post("/v1/clip-ready")
    def clip_ready(body: dict):
        """Called back by clip-recorder once a clip is written (or failed)."""
        event_id = body.get("event_id")
        ctx = pending_tier1.pop(event_id, None)
        if ctx is None:
            return {"ignored": True}
        if body.get("status") != "ready":
            return {"ignored": True, "reason": body.get("error")}
        score = clf.score(body["clip_path"])
        sev = decide(score, HIGH, SUSPICIOUS)
        if sev == "low":
            return {"decision": "low", "score": score}
        payload = {
            "severity": sev, "score": score, "camera_id": ctx["camera_id"],
            "clip_path": body["clip_path"],
            "tier1": {"motion_score": ctx["motion"], "persons": ctx["persons"]},
            "classifier": {"name": clf.name, "version": clf.version},
        }
        r = requests.post(f"{PUBLISHER_URL}/v1/safety-events", json=payload, timeout=5)
        r.raise_for_status()
        return {"decision": sev, "score": score, "event_id": r.json()["event_id"]}

    return app


def gate_loop(stop: threading.Event) -> None:
    sub = subscribe(ZMQ_HOST, ZMQ_PORT, ZMQ_TOPIC)
    state = GateState()
    while not stop.is_set():
        for msg in iter_messages(sub, ZMQ_TOPIC):
            if stop.is_set():
                return
            if msg is None:
                continue
            boxes = persons(msg.get("detections", []))
            gate_open, motion = tier1_gate(state, boxes, PERSONS_MIN, MOTION_MIN)
            now = time.time()
            if gate_open and now - last_trigger.get(CAMERA_ID, 0) > COOLDOWN_S:
                last_trigger[CAMERA_ID] = now
                event_id = str(uuid.uuid4())
                pending_tier1[event_id] = {
                    "camera_id": CAMERA_ID, "motion": round(motion, 2), "persons": len(boxes),
                }
                try:
                    requests.post(f"{RECORDER_URL}/v1/record", json={
                        "event_id": event_id, "camera_id": CAMERA_ID,
                        "postroll_s": POSTROLL_S}, timeout=5)
                except requests.RequestException as exc:
                    print(f"aggression-detector: clip-recorder unreachable: {exc}", flush=True)
                    pending_tier1.pop(event_id, None)
