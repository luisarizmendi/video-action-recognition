"""Thin ZeroMQ SUB wrapper around the object-detection stream published by
services/inference-onnx (or -tensorrt / -tensorrt-jetson). Same wire format
across all three, so this client does not care which one is running."""
import json
from typing import Iterator

import zmq


def subscribe(host: str, port: int, topic: str) -> zmq.Socket:
    ctx = zmq.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.setsockopt_string(zmq.SUBSCRIBE, topic)
    sub.setsockopt(zmq.RCVTIMEO, 1000)
    sub.connect(f"tcp://{host}:{port}")
    return sub


def iter_messages(sub: zmq.Socket, topic: str) -> Iterator[dict]:
    """Yields decoded payload dicts, skipping timeouts silently (the caller's
    loop is expected to keep running and just gets no message that tick)."""
    while True:
        try:
            raw = sub.recv_string()
        except zmq.Again:
            yield None
            continue
        # wire format: "<topic> <json>"
        _, _, payload = raw.partition(" ")
        yield json.loads(payload)


def persons(detections: list, class_name: str = "person") -> list:
    return [d["bbox"] for d in detections if d.get("class_name") == class_name]
