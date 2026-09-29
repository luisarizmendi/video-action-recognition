"""HTTP API for the clip recorder.

POST /v1/record starts a recording for one event: it takes everything the
ring buffer currently holds (the pre-roll), keeps collecting new frames for
POSTROLL_S more seconds, writes the clip, then POSTs the result to
CALLBACK_URL. The call returns immediately (202) with the clip path the
caller should expect; the caller (aggression-detector) waits for the
callback rather than blocking the SHM reader thread.
"""
import os
import threading
import time
import uuid
from typing import Dict

import requests
from fastapi import FastAPI
from pydantic import BaseModel

from .ring_buffer import RingBuffer
from .writer import write_clip

CLIP_DIR = os.environ.get("CLIP_DIR", "/clips")
POSTROLL_S = float(os.environ.get("POSTROLL_S", "4"))
CLIP_FPS = float(os.environ.get("CLIP_FPS", "10"))
CALLBACK_URL = os.environ.get("CALLBACK_URL", "")


class RecordIn(BaseModel):
    event_id: str
    camera_id: str = "cam-1"
    postroll_s: float = POSTROLL_S


def create_app(ring: RingBuffer) -> FastAPI:
    app = FastAPI(title="clip-recorder")
    pending: Dict[str, bool] = {}

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "buffered_frames": len(ring.snapshot_since())}

    @app.post("/v1/record", status_code=202)
    def record(body: RecordIn):
        if pending.get(body.event_id):
            return {"event_id": body.event_id, "status": "already_recording"}
        pending[body.event_id] = True
        start_ts = ring.latest_ts() or time.time()
        preroll = ring.snapshot_since()  # everything currently buffered

        def finish():
            deadline = start_ts + body.postroll_s
            while (ring.latest_ts() or 0) < deadline:
                time.sleep(0.2)
            postroll = [f for f in ring.snapshot_since(start_ts) if f.ts > start_ts]
            frames = [f.jpeg for f in preroll] + [f.jpeg for f in postroll]
            path = os.path.join(CLIP_DIR, f"{body.camera_id}-{body.event_id}.mp4")
            try:
                write_clip(frames, path, fps=CLIP_FPS)
                result = {"event_id": body.event_id, "clip_path": path, "status": "ready"}
            except Exception as exc:  # empty buffer, decode error, disk full, etc.
                result = {"event_id": body.event_id, "status": "failed", "error": repr(exc)}
            pending.pop(body.event_id, None)
            if CALLBACK_URL:
                try:
                    requests.post(CALLBACK_URL, json=result, timeout=5)
                except requests.RequestException as exc:
                    print(f"clip-recorder: callback failed for {body.event_id}: {exc}", flush=True)

        threading.Thread(target=finish, daemon=True).start()
        expected_path = os.path.join(CLIP_DIR, f"{body.camera_id}-{body.event_id}.mp4")
        return {"event_id": body.event_id, "status": "recording", "clip_path": expected_path}

    return app
