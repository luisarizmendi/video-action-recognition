import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi.testclient import TestClient  # noqa: E402

from publisher.api import create_app  # noqa: E402
from publisher.config import Settings  # noqa: E402
from publisher.delivery import deliver_once  # noqa: E402
from publisher.outbox import Outbox  # noqa: E402


class FakeStore:
    def __init__(self, fail=False):
        self.fail, self.puts = fail, []

    def put(self, path, bucket, key):
        if self.fail:
            raise RuntimeError("s4 down")
        self.puts.append((bucket, key))


class FakeSink:
    def __init__(self, fail=False):
        self.fail, self.sent = fail, []

    def send(self, topic, key, value):
        if self.fail:
            raise RuntimeError("kafka down")
        self.sent.append((topic, key, json.loads(value)))


def make(tmp_path):
    s = Settings.from_env()
    ob = Outbox(str(tmp_path / "o.db"))
    return s, ob


def test_event_survives_link_down_then_delivers(tmp_path):
    s, ob = make(tmp_path)
    clip = tmp_path / "c.mp4"
    clip.write_bytes(b"x" * 100)
    store, sink = FakeStore(), FakeSink(fail=True)
    client = TestClient(create_app(s, ob, store, sink, run_worker=False))
    r = client.post("/v1/safety-events", json={
        "severity": "high", "score": 0.93, "camera_id": "cam1", "clip_path": str(clip)})
    assert r.status_code == 202
    # link down: nothing delivered, row stays
    now = time.time()
    assert deliver_once(ob, store, sink, now=now)["failed"] == 1
    assert ob.stats()[0] == 1
    # evidence upload happened before the Kafka failure, and is not repeated
    assert len(store.puts) == 1
    # link back: delivered after backoff
    sink.fail = False
    res = deliver_once(ob, store, sink, now=now + 10)
    assert res["delivered"] == 1
    assert len(store.puts) == 1
    topic, key, payload = sink.sent[0]
    assert topic == "bus.safety.events" and payload["severity"] == "high"
    assert payload["evidence"]["key"].endswith(".mp4")
    assert ob.stats()[0] == 0


def test_priority_and_cap(tmp_path):
    s, ob = make(tmp_path)
    ob.enqueue("a", "t", "k", "{}", 5, now=1)
    ob.enqueue("b", "t", "k", "{}", 100, now=2)
    ob.enqueue("c", "t", "k", "{}", 50, now=3)
    assert [r.id for r in ob.due(10)] == ["b", "c", "a"]
    ob.enforce_cap(2)
    assert sorted(r.id for r in ob.due(10)) == ["b", "c"]


def test_missing_clip_is_rejected(tmp_path):
    s, ob = make(tmp_path)
    client = TestClient(create_app(s, ob, FakeStore(), FakeSink(), run_worker=False))
    r = client.post("/v1/safety-events", json={
        "severity": "suspicious", "score": 0.6, "camera_id": "c", "clip_path": "/nope.mp4"})
    assert r.status_code == 422
