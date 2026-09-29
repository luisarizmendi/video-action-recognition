"""Unit tests for capture.py that don't need a real camera, RTSP server, or SHM.

Only select_best_mode() and the SOURCE_MODE env parsing are pure functions;
everything else touches a device, ffmpeg, or shared memory and is exercised
manually or in the compose-based laptop test (see tools/).
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_select_best_mode_prefers_fps_then_size_then_mjpeg():
    import capture
    modes = [
        {"fmt": "yuyv422", "size": "1920x1080", "fps": 30.0},
        {"fmt": "mjpeg", "size": "1280x720", "fps": 30.0},
        {"fmt": "mjpeg", "size": "1280x720", "fps": 15.0},
    ]
    best = capture.select_best_mode(modes, target_fps=30.0)
    # Same fps as the yuyv option but mjpeg ranks higher at equal size/fps distance...
    # actually size is compared before format, so the larger yuyv frame wins first.
    assert best["size"] == "1920x1080"


def test_select_best_mode_empty():
    import capture
    assert capture.select_best_mode([], target_fps=30.0) is None


def test_source_mode_env_parsing(monkeypatch):
    monkeypatch.setenv("SOURCE_MODE", "RTSP")  # case should not matter
    monkeypatch.setenv("RTSP_URL", "rtsp://demo/cam")
    sys.modules.pop("capture", None)
    import capture
    assert capture.SOURCE_MODE == "rtsp"
    assert capture.RTSP_URL == "rtsp://demo/cam"
    monkeypatch.delenv("SOURCE_MODE", raising=False)
    monkeypatch.delenv("RTSP_URL", raising=False)
    sys.modules.pop("capture", None)
