import os
import threading

import cv2
import numpy as np

from .app import create_app
from .ring_buffer import RingBuffer
from .shm_frame import ShmFrameReader

SHM_NAME = os.environ.get("SHM_FRAME_NAME", "camera_frame")
PREROLL_S = float(os.environ.get("PREROLL_S", "8"))
ENCODE_QUALITY = int(os.environ.get("ENCODE_JPEG_QUALITY", "70"))

ring = RingBuffer(PREROLL_S)


def reader_loop():
    """Continuously fill the ring buffer, independent of any recording. Frames
    arrive as raw BGR or already-JPEG depending on VIEWER_JPEG_QUALITY on the
    capture side; normalize to JPEG here so the writer never needs to know."""
    reader = ShmFrameReader(name=SHM_NAME, timeout=30.0)
    while True:
        seq, w, h, ch, ts, data, jpeg_size = reader.read_frame(wait_new=True)
        if jpeg_size:
            jpeg = data
        else:
            frame = np.frombuffer(data, dtype=np.uint8).reshape(h, w, ch)
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, ENCODE_QUALITY])
            if not ok:
                continue
            jpeg = buf.tobytes()
        ring.push(ts, jpeg)


threading.Thread(target=reader_loop, daemon=True).start()
app = create_app(ring)
