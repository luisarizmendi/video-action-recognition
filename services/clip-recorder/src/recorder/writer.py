"""Encode a list of JPEG frames into an MP4 clip.

TODO for production: this decodes each JPEG then re-encodes with mp4v, which
is not a browser-playable codec. Swap cv2.VideoWriter's fourcc for H.264
(avc1) once an H.264-capable OpenCV/ffmpeg build is available in the image,
or shell out to ffmpeg to mux the JPEGs directly (faster, no re-decode).
"""
import os
from typing import List

import cv2
import numpy as np


def write_clip(frames_jpeg: List[bytes], path: str, fps: float = 10.0) -> str:
    if not frames_jpeg:
        raise ValueError("no frames to write")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    first = cv2.imdecode(np.frombuffer(frames_jpeg[0], np.uint8), cv2.IMREAD_COLOR)
    h, w = first.shape[:2]
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    out.write(first)
    for jpeg in frames_jpeg[1:]:
        frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            out.write(frame)
    out.release()
    return path
