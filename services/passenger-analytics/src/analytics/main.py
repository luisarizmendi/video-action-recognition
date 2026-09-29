"""Passenger analytics: subscribes to the object-detection ZeroMQ stream at a
door camera, tracks people with a centroid tracker, counts boarding and
alighting on line crossings, and posts a PassengerCount event per window to
event-publisher. Same event-publisher API as before, so nothing downstream
changes.
"""
import http.server
import json
import os
import threading
from datetime import datetime, timezone

import requests

from .tracker import LineCounter

ZMQ_HOST = os.environ.get("ZMQ_SUB_HOST", "localhost")
ZMQ_PORT = int(os.environ.get("ZMQ_SUB_PORT", "5555"))
ZMQ_TOPIC = os.environ.get("ZMQ_TOPIC", "detections")
CAMERA_ID = os.environ.get("CAMERA_ID", "door-1")
PUBLISHER_URL = os.environ.get("PUBLISHER_URL", "http://event-publisher:8080")
WINDOW_S = int(os.environ.get("WINDOW_S", "60"))
LINE_Y = float(os.environ.get("LINE_Y", "0.5"))
LINE_DIRECTION = os.environ.get("LINE_DIRECTION", "down")


class Health(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def person_centers(detections: list) -> list:
    out = []
    for d in detections:
        if d.get("class_name") == "person":
            b = d["bbox"]
            out.append({"cx": b["cx"], "cy": b["cy"]})
    return out


def zmq_subscribe():
    import zmq
    ctx = zmq.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.setsockopt_string(zmq.SUBSCRIBE, ZMQ_TOPIC)
    sub.setsockopt(zmq.RCVTIMEO, 1000)
    sub.connect(f"tcp://{ZMQ_HOST}:{ZMQ_PORT}")
    return sub


def run():
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Health)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    counter = LineCounter(line_y=LINE_Y, direction=LINE_DIRECTION)
    sub = zmq_subscribe()
    import zmq

    window_start = datetime.now(timezone.utc)
    boarded_total = alighted_total = 0

    while True:
        try:
            raw = sub.recv_string()
            _, _, payload = raw.partition(" ")
            msg = json.loads(payload)
            boxes = person_centers(msg.get("detections", []))
            b, a = counter.update(boxes)
            boarded_total += b
            alighted_total += a
        except zmq.Again:
            pass

        now = datetime.now(timezone.utc)
        if (now - window_start).total_seconds() >= WINDOW_S:
            body = {
                "camera_id": CAMERA_ID, "window_start": window_start.isoformat(),
                "window_end": now.isoformat(), "occupancy": counter.active_count(),
                "boarded": boarded_total, "alighted": alighted_total,
            }
            try:
                requests.post(f"{PUBLISHER_URL}/v1/passenger-counts", json=body, timeout=5)
            except requests.RequestException as exc:
                print("publisher unreachable:", exc, flush=True)
            window_start, boarded_total, alighted_total = now, 0, 0


if __name__ == "__main__":
    run()
