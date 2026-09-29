"""Movements below are in small per-frame steps, like a real detection stream
at a few fps, not one big jump. max_match_dist has to be small enough that
two different people never get confused, so a single huge jump between calls
is unrealistic and is not how the tracker is meant to be driven.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from analytics.tracker import LineCounter  # noqa: E402


def box(cx, cy):
    return {"cx": cx, "cy": cy}


def walk(counter, cx, cy_from, cy_to, steps=8):
    """Feed the counter a straight-line walk in `steps` small hops and return
    the (boarded, alighted) totals accumulated along the way."""
    boarded = alighted = 0
    for i in range(1, steps + 1):
        cy = cy_from + (cy_to - cy_from) * i / steps
        b, a = counter.update([box(cx, cy)])
        boarded += b
        alighted += a
    return boarded, alighted


def test_single_person_boards_crossing_downward():
    c = LineCounter(line_y=0.5, direction="down")
    c.update([box(0.5, 0.1)])  # first sighting, above the line
    b, a = walk(c, 0.5, 0.1, 0.9)
    assert (b, a) == (1, 0)


def test_single_person_alights_crossing_upward():
    c = LineCounter(line_y=0.5, direction="down")
    c.update([box(0.5, 0.9)])  # first sighting, below the line
    b, a = walk(c, 0.5, 0.9, 0.1)
    assert (b, a) == (0, 1)


def test_direction_flag_inverts_meaning():
    c = LineCounter(line_y=0.5, direction="up")
    c.update([box(0.5, 0.1)])
    b, a = walk(c, 0.5, 0.1, 0.9)
    assert (b, a) == (0, 1)


def test_does_not_double_count_while_staying_on_one_side():
    c = LineCounter(line_y=0.5, direction="down")
    c.update([box(0.5, 0.1)])
    walk(c, 0.5, 0.1, 0.9)          # counts as boarded
    b, a = c.update([box(0.5, 0.92)])  # still below, no new crossing
    assert (b, a) == (0, 0)


def test_can_count_again_after_crossing_back():
    c = LineCounter(line_y=0.5, direction="down")
    c.update([box(0.5, 0.1)])
    walk(c, 0.5, 0.1, 0.9)   # boarded
    c.update([box(0.5, 0.92)])  # settle below, re-arms
    b, a = walk(c, 0.5, 0.92, 0.1)  # walk back up and cross again
    assert (b, a) == (0, 1)


def test_tracks_are_matched_by_proximity_not_order():
    c = LineCounter(line_y=0.5, direction="down", max_match_dist=0.2)
    c.update([box(0.1, 0.1), box(0.9, 0.1)])
    boarded = 0
    for i in range(1, 9):
        cy = 0.1 + 0.8 * i / 8
        # order swapped each call: left person reported second, right person first
        b, a = c.update([box(0.9, cy), box(0.1, cy)])
        boarded += b
    assert boarded == 2


def test_active_count_ages_out_missing_tracks():
    c = LineCounter(line_y=0.5, max_misses=1)
    c.update([box(0.5, 0.2)])
    assert c.active_count() == 1
    c.update([])  # miss 1
    assert c.active_count() == 1
    c.update([])  # miss 2, exceeds max_misses
    assert c.active_count() == 0
