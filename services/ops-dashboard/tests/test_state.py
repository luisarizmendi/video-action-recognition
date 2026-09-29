import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dashboard.state import State  # noqa: E402


def test_dedupe_and_bus_view():
    s = State()
    assert s.add("passenger", {"event_id": "1", "bus_id": "b1", "occupancy": 7, "boarded": 2, "alighted": 1})
    assert not s.add("passenger", {"event_id": "1", "bus_id": "b1", "occupancy": 7, "boarded": 2, "alighted": 1})
    s.add("safety", {"event_id": "2", "bus_id": "b1", "severity": "high"})
    snap = s.snapshot()
    assert snap["buses"]["b1"]["occupancy"] == 7 and snap["buses"]["b1"]["last_alert"] == "high"
    assert len(s.since(1)) == 1
