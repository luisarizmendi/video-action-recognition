import hashlib
import json
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .delivery import deliver_once
from .health import enqueue_health
from .outbox import (PRIORITY_HIGH, PRIORITY_PASSENGER, PRIORITY_SUSPICIOUS, Outbox)


class Tier1(BaseModel):
    motion_score: float = 0.0
    persons: int = 0


class Classifier(BaseModel):
    name: str = "movinet-a0"
    version: str = "0"


class SafetyEventIn(BaseModel):
    severity: Literal["high", "suspicious"]
    score: float = Field(ge=0, le=1)
    camera_id: str
    clip_path: Optional[str] = None
    detected_at: Optional[datetime] = None
    tier1: Tier1 = Tier1()
    classifier: Classifier = Classifier()


class PassengerCountIn(BaseModel):
    camera_id: str
    window_start: datetime
    window_end: datetime
    occupancy: int = Field(ge=0)
    boarded: int = Field(ge=0)
    alighted: int = Field(ge=0)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def create_app(settings, outbox: Outbox, store, sink, run_worker: bool = True) -> FastAPI:
    stop = threading.Event()

    def worker():
        last_health = 0.0
        while not stop.is_set():
            now = time.time()
            if now - last_health >= settings.health_interval_s:
                enqueue_health(outbox, settings)
                last_health = now
            for path in outbox.enforce_cap(settings.outbox_max_rows):
                try:
                    os.remove(path)
                except OSError:
                    pass
            res = deliver_once(outbox, store, sink)
            if res["delivered"] == 0:
                stop.wait(1.0)

    @asynccontextmanager
    async def lifespan(_app):
        t = None
        if run_worker:
            t = threading.Thread(target=worker, daemon=True)
            t.start()
        yield
        stop.set()
        if t:
            t.join(timeout=5)

    app = FastAPI(title="event-publisher", lifespan=lifespan)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/v1/stats")
    def stats():
        pending, oldest = outbox.stats()
        return {"pending": pending, "oldest_age_s": round(oldest, 1)}

    @app.post("/v1/safety-events", status_code=202)
    def safety_event(body: SafetyEventIn):
        event_id = str(uuid.uuid4())
        detected = (body.detected_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        evidence = None
        bucket = key = None
        if body.clip_path:
            if not os.path.isfile(body.clip_path):
                raise HTTPException(422, f"clip not found: {body.clip_path}")
            bucket = settings.s3_bucket
            key = f"evidence/{settings.bus_id}/{detected:%Y-%m-%d}/{event_id}.mp4"
            evidence = {"bucket": bucket, "key": key, "content_type": "video/mp4",
                        "sha256": _sha256(body.clip_path),
                        "size_bytes": os.path.getsize(body.clip_path)}
        payload = {
            "schema_version": 1, "event_id": event_id, "event_type": "aggression",
            "severity": body.severity, "bus_id": settings.bus_id, "camera_id": body.camera_id,
            "detected_at": detected.isoformat(), "score": body.score,
            "tier1": body.tier1.model_dump(), "classifier": body.classifier.model_dump(),
            "evidence": evidence,
        }
        prio = PRIORITY_HIGH if body.severity == "high" else PRIORITY_SUSPICIOUS
        outbox.enqueue(event_id, settings.topic_safety, settings.bus_id, json.dumps(payload),
                       prio, body.clip_path, bucket, key)
        return {"event_id": event_id}

    @app.post("/v1/passenger-counts", status_code=202)
    def passenger_count(body: PassengerCountIn):
        event_id = str(uuid.uuid4())
        payload = {
            "schema_version": 1, "event_id": event_id, "bus_id": settings.bus_id,
            "camera_id": body.camera_id, "window_start": body.window_start.isoformat(),
            "window_end": body.window_end.isoformat(), "occupancy": body.occupancy,
            "boarded": body.boarded, "alighted": body.alighted,
        }
        outbox.enqueue(event_id, settings.topic_passenger, settings.bus_id,
                       json.dumps(payload), PRIORITY_PASSENGER)
        return {"event_id": event_id}

    return app
