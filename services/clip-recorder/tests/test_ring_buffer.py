import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from recorder.ring_buffer import RingBuffer  # noqa: E402


def test_drops_frames_older_than_preroll():
    r = RingBuffer(preroll_s=5)
    r.push(0.0, b"a")
    r.push(3.0, b"b")
    r.push(10.0, b"c")  # cutoff is now 10 - 5 = 5, drops the first two
    frames = r.snapshot_since()
    assert [f.jpeg for f in frames] == [b"c"]


def test_snapshot_since():
    r = RingBuffer(preroll_s=100)
    for t in [1.0, 2.0, 3.0, 4.0]:
        r.push(t, f"f{t}".encode())
    assert [f.ts for f in r.snapshot_since(2.5)] == [3.0, 4.0]
    assert r.latest_ts() == 4.0
