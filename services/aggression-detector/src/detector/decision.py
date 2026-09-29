"""Tier 1 gate and the High / Suspicious / Low decision.

Tier 1 now runs against a ZeroMQ object-detection stream (person boxes per
frame) instead of a single motion_score/persons pair from one clip. gate()
tracks a short rolling window of frames and gates on: enough people AND
enough movement between frames (a rough, cheap proxy for a physical
altercation, cheaper than running the action classifier on every frame).
"""
from dataclasses import dataclass, field
from typing import List, Tuple


def bbox_center(b: dict) -> Tuple[float, float]:
    return b["cx"], b["cy"]


def frame_motion(prev_boxes: List[dict], boxes: List[dict]) -> float:
    """Average center displacement between the closest-matching boxes in two
    consecutive frames, normalized by frame diagonal is left to the caller
    (this returns raw pixel displacement). Unmatched boxes (a person entering
    or leaving frame) are ignored, they are not motion within the scene."""
    if not prev_boxes or not boxes:
        return 0.0
    total = 0.0
    matched = 0
    remaining = list(boxes)
    for pb in prev_boxes:
        if not remaining:
            break
        px, py = bbox_center(pb)
        best_i, best_d = None, None
        for i, b in enumerate(remaining):
            bx, by = bbox_center(b)
            d = ((bx - px) ** 2 + (by - py) ** 2) ** 0.5
            if best_d is None or d < best_d:
                best_d, best_i = d, i
        if best_d is not None and best_d < 200:  # not a plausible match otherwise
            total += best_d
            matched += 1
            remaining.pop(best_i)
    return total / matched if matched else 0.0


@dataclass
class GateState:
    """Per-camera rolling state for tier1_gate()."""
    prev_boxes: List[dict] = field(default_factory=list)
    motion_ema: float = 0.0


def tier1_gate(state: GateState, person_boxes: List[dict],
                persons_min: int = 2, motion_min: float = 8.0,
                ema_alpha: float = 0.3) -> Tuple[bool, float]:
    """Update state with one frame's person boxes, return (gate_open, motion_ema).
    Cheap: no model inference, just box bookkeeping. This runs on every frame;
    the classifier only runs once the gate opens."""
    motion = frame_motion(state.prev_boxes, person_boxes)
    state.motion_ema = ema_alpha * motion + (1 - ema_alpha) * state.motion_ema
    state.prev_boxes = person_boxes
    gate_open = len(person_boxes) >= persons_min and state.motion_ema >= motion_min
    return gate_open, state.motion_ema


def decide(score: float, high: float = 0.85, suspicious: float = 0.50) -> str:
    if score >= high:
        return "high"
    if score >= suspicious:
        return "suspicious"
    return "low"
