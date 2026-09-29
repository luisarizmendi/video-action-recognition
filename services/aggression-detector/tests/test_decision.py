import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from detector.decision import GateState, decide, frame_motion, tier1_gate  # noqa: E402


def box(cx, cy):
    return {"cx": cx, "cy": cy}


def test_decide_thresholds():
    assert decide(0.9) == "high"
    assert decide(0.6) == "suspicious"
    assert decide(0.2) == "low"


def test_frame_motion_matches_closest_and_ignores_unmatched():
    prev = [box(100, 100), box(500, 500)]
    now = [box(120, 100)]  # only one box now; the other left the frame
    m = frame_motion(prev, now)
    assert 15 < m < 25  # ~20px displacement from the matched pair only


def test_frame_motion_empty_is_zero():
    assert frame_motion([], []) == 0.0
    assert frame_motion([box(0, 0)], []) == 0.0


def test_gate_needs_persons_and_motion():
    state = GateState()
    # two people, not moving yet (first frame has no prior to compare)
    open1, m1 = tier1_gate(state, [box(0, 0), box(50, 50)], persons_min=2, motion_min=8.0)
    assert not open1
    # now they move a lot
    open2, m2 = tier1_gate(state, [box(60, 60), box(0, 0)], persons_min=2, motion_min=8.0)
    assert m2 > m1


def test_gate_blocks_on_too_few_persons():
    state = GateState()
    tier1_gate(state, [box(0, 0), box(50, 50)], persons_min=2, motion_min=1.0)
    open_, _ = tier1_gate(state, [box(200, 200)], persons_min=2, motion_min=1.0)
    assert not open_  # only one person now, gate must stay closed regardless of motion
