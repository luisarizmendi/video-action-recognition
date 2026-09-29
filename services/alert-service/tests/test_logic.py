import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from alerts.logic import Deduper, route  # noqa: E402


def test_dedupe():
    d = Deduper(2)
    assert not d.seen("a") and d.seen("a")
    d.seen("b"); d.seen("c")
    assert not d.seen("a")  # evicted


def test_route():
    assert route({"severity": "high"}) == "page"
    assert route({"severity": "suspicious"}) == "review"
