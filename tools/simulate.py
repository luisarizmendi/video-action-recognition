#!/usr/bin/env python3
"""Fake passenger windows or a safety event against event-publisher directly,
bypassing the camera/inference/gate pipeline. Useful to check the datacenter
side (Kafka, S4, alert-service, ops-dashboard) independently of whether a
camera or the Tier 1 gate is producing real events yet.

  python tools/simulate.py --passengers 5
  python tools/simulate.py --severity high --clip sample.mp4

To exercise the REAL pipeline instead (camera → inference → gate → clip →
event), just show two people moving to the camera or a video in videos/ —
that is what aggression-detector and passenger-analytics are for.
"""
import argparse
import json
import subprocess
import sys
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publisher", default="http://localhost:8085")
    ap.add_argument("--severity", choices=["high", "suspicious"])
    ap.add_argument("--clip", help="local mp4 to use as evidence")
    ap.add_argument("--passengers", type=int, help="send N passenger windows")
    ap.add_argument("--via-container", default="", help="compose service that mounts /clips, e.g. event-publisher")
    ap.add_argument("--engine", default="podman")
    a = ap.parse_args()

    if a.severity:
        name = f"{a.severity[:3]}-{uuid.uuid4().hex[:6]}.mp4"
        clip_path = f"/clips/{name}"
        if a.via_container:
            local = a.clip or "/tmp/placeholder.mp4"
            if not a.clip:
                open(local, "wb").write(b"placeholder clip")
            subprocess.check_call([a.engine, "compose", "cp", local, f"{a.via_container}:{clip_path}"])
        elif a.clip:
            clip_path = a.clip
        else:
            clip_path = f"/tmp/{name}"
            open(clip_path, "wb").write(b"placeholder clip")
        print(post(f"{a.publisher}/v1/safety-events", {
            "severity": a.severity, "score": 0.93 if a.severity == "high" else 0.65,
            "camera_id": "cam-1", "clip_path": clip_path,
            "tier1": {"motion_score": 12.0, "persons": 3}}))

    if a.passengers:
        now = datetime.now(timezone.utc)
        occ = 4
        for i in range(a.passengers):
            b, l = (i * 3) % 5, (i * 2) % 4
            occ = max(0, occ + b - l)
            print(post(f"{a.publisher}/v1/passenger-counts", {
                "camera_id": "door-1", "window_start": (now + timedelta(minutes=i)).isoformat(),
                "window_end": (now + timedelta(minutes=i + 1)).isoformat(),
                "occupancy": occ, "boarded": b, "alighted": l}))

    if not a.severity and not a.passengers:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
