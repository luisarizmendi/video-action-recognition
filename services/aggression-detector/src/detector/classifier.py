"""Clip classifier. Replace StubClassifier with the real MoViNet A0 model.

Real model: load the streaming MoViNet A0 (TFLite or TensorFlow) from the
model directory the modelcar image mounts at /models, run it on the clip
saved by clip-recorder, return P(aggression). This is an action-recognition
model, separate from the per-frame object detector in services/inference-*;
it only runs on the few clips that pass the Tier 1 gate, not on every frame,
so it does not need to be real time.
"""
import os
from typing import Protocol


class Classifier(Protocol):
    name: str
    version: str

    def score(self, clip_path: str) -> float: ...


class StubClassifier:
    """Deterministic scores for demos. A clip name containing 'high' scores 0.93,
    'sus' scores 0.65, anything else 0.75 (Tier 1 already filtered for motion,
    so an unlabeled demo clip should usually still raise a Suspicious).
    DEMO_SCORE overrides all of it."""
    name = "stub"
    version = "0"

    def score(self, clip_path: str) -> float:
        forced = os.environ.get("DEMO_SCORE")
        if forced:
            return float(forced)
        n = os.path.basename(clip_path).lower()
        if "high" in n:
            return 0.93
        if "sus" in n:
            return 0.65
        return 0.75


def load_classifier() -> Classifier:
    # TODO: if os.path.isdir("/models/movinet-a0"): return MoViNetA0("/models/movinet-a0")
    return StubClassifier()
