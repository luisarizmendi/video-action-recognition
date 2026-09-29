"""Pre-roll ring buffer. Decoded frames are expensive to keep for long, so this
stores encoded JPEG bytes with their capture timestamp and drops frames older
than PREROLL_S once a recording is not in progress for them.
"""
import threading
from collections import deque
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Frame:
    ts: float       # capture timestamp (monotonic, from the SHM header)
    jpeg: bytes


class RingBuffer:
    def __init__(self, preroll_s: float):
        self._preroll_s = preroll_s
        self._lock = threading.Lock()
        self._frames: deque = deque()

    def push(self, ts: float, jpeg: bytes) -> None:
        with self._lock:
            self._frames.append(Frame(ts, jpeg))
            cutoff = ts - self._preroll_s
            while self._frames and self._frames[0].ts < cutoff:
                self._frames.popleft()

    def snapshot_since(self, since_ts: Optional[float] = None) -> List[Frame]:
        """Frames at or after since_ts, oldest first. None means everything held."""
        with self._lock:
            if since_ts is None:
                return list(self._frames)
            return [f for f in self._frames if f.ts >= since_ts]

    def latest_ts(self) -> Optional[float]:
        with self._lock:
            return self._frames[-1].ts if self._frames else None
