import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from recorder.app import create_app  # noqa: E402
from recorder.ring_buffer import RingBuffer  # noqa: E402


def _jpeg(color=(0, 0, 0)):
    frame = np.full((16, 16, 3), color, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", frame)
    assert ok
    return buf.tobytes()


def test_record_writes_clip_and_calls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIP_DIR", str(tmp_path))
    monkeypatch.setenv("POSTROLL_S", "0.3")
    callbacks = []
    import recorder.app as app_module
    monkeypatch.setattr(app_module, "CLIP_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "POSTROLL_S", 0.3)

    def fake_post(url, json, timeout):
        callbacks.append(json)
        class R:
            pass
        return R()
    monkeypatch.setattr(app_module.requests, "post", fake_post)
    monkeypatch.setattr(app_module, "CALLBACK_URL", "http://fake/callback")

    ring = RingBuffer(preroll_s=10)
    now = time.time()
    ring.push(now - 1, _jpeg())
    ring.push(now, _jpeg())

    client = TestClient(create_app(ring))
    r = client.post("/v1/record", json={"event_id": "e1", "camera_id": "cam1", "postroll_s": 0.3})
    assert r.status_code == 202
    assert r.json()["status"] == "recording"

    # simulate more frames arriving during the postroll window
    for i in range(3):
        time.sleep(0.15)
        ring.push(time.time(), _jpeg())

    deadline = time.time() + 3
    while not callbacks and time.time() < deadline:
        time.sleep(0.1)

    assert callbacks, "callback was never called"
    assert callbacks[0]["status"] == "ready"
    assert os.path.isfile(callbacks[0]["clip_path"])


def test_duplicate_event_id_is_ignored(tmp_path, monkeypatch):
    import recorder.app as app_module
    monkeypatch.setattr(app_module, "CLIP_DIR", str(tmp_path))
    monkeypatch.setattr(app_module, "CALLBACK_URL", "")
    ring = RingBuffer(preroll_s=10)
    ring.push(time.time(), _jpeg())
    client = TestClient(create_app(ring))
    r1 = client.post("/v1/record", json={"event_id": "dup", "postroll_s": 5})
    r2 = client.post("/v1/record", json={"event_id": "dup", "postroll_s": 5})
    assert r1.json()["status"] == "recording"
    assert r2.json()["status"] == "already_recording"
