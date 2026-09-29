"""Minimal centroid tracker with a line-crossing counter.

Not a production-grade tracker (no Kalman filter, no re-ID on long
occlusion), but stable enough for a door camera at a few fps: match each new
detection to the nearest existing track within MAX_MATCH_DIST, age out
tracks that go unseen for MAX_MISSES frames, and count a boarding/alighting
event the frame a track's centroid crosses the configured line.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Track:
    id: int
    cx: float
    cy: float
    misses: int = 0
    side: str = ""  # "above" or "below" the line, set on first sighting
    counted: bool = False


@dataclass
class LineCounter:
    """line_y is in the same coordinate space as the incoming boxes (typically
    normalized 0..1, or pixel y if you set it to match your camera resolution).
    direction "down" means crossing from above to below counts as boarded;
    set "up" if your door camera is mounted the other way."""
    line_y: float
    direction: str = "down"
    max_match_dist: float = 0.15
    max_misses: int = 5
    _next_id: int = field(default=0, repr=False)
    _tracks: Dict[int, Track] = field(default_factory=dict, repr=False)

    def update(self, boxes: List[dict]) -> Tuple[int, int]:
        """boxes: list of {"cx":..., "cy":...}. Returns (boarded, alighted) for
        this frame only (0 or more each, usually 0)."""
        boarded = alighted = 0
        unmatched = list(range(len(boxes)))
        for track in self._tracks.values():
            best_i, best_d = None, None
            for i in unmatched:
                b = boxes[i]
                d = ((b["cx"] - track.cx) ** 2 + (b["cy"] - track.cy) ** 2) ** 0.5
                if d < self.max_match_dist and (best_d is None or d < best_d):
                    best_d, best_i = d, i
            if best_i is not None:
                b = boxes[best_i]
                boarded_now, alighted_now = self._maybe_count(track, b["cy"])
                boarded += boarded_now
                alighted += alighted_now
                track.cx, track.cy, track.misses = b["cx"], b["cy"], 0
                unmatched.remove(best_i)
            else:
                track.misses += 1
        self._tracks = {tid: t for tid, t in self._tracks.items() if t.misses <= self.max_misses}
        for i in unmatched:
            b = boxes[i]
            side = "above" if b["cy"] < self.line_y else "below"
            self._tracks[self._next_id] = Track(id=self._next_id, cx=b["cx"], cy=b["cy"], side=side)
            self._next_id += 1
        return boarded, alighted

    def _maybe_count(self, track: Track, new_cy: float) -> Tuple[int, int]:
        new_side = "above" if new_cy < self.line_y else "below"
        if not track.side:
            track.side = new_side
            return 0, 0
        if new_side != track.side and not track.counted:
            track.side = new_side
            track.counted = True
            crossed_down = new_side == "below"
            if self.direction == "down":
                return (1, 0) if crossed_down else (0, 1)
            return (0, 1) if crossed_down else (1, 0)
        if new_side == track.side:
            track.counted = False  # allow re-counting if they cross back later
        track.side = new_side
        return 0, 0

    def active_count(self) -> int:
        return len(self._tracks)
