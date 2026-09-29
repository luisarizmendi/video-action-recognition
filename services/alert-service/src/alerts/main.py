import json
import os

import requests
from confluent_kafka import Consumer

from .logic import Deduper, route

TOPIC = os.environ.get("TOPIC_SAFETY", "bus.safety.events")
WEBHOOK = os.environ.get("ALERT_WEBHOOK_URL")  # Slack, Teams, PagerDuty, etc. Optional.


def kafka_conf() -> dict:
    conf = {
        "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP"],
        "group.id": os.environ.get("KAFKA_GROUP", "bus-alert-service"),
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
    }
    if os.environ.get("KAFKA_USERNAME"):
        conf.update({
            "security.protocol": "SASL_SSL", "sasl.mechanisms": "SCRAM-SHA-512",
            "sasl.username": os.environ["KAFKA_USERNAME"],
            "sasl.password": os.environ["KAFKA_PASSWORD"],
        })
        if os.environ.get("KAFKA_CA_PATH"):
            conf["ssl.ca.location"] = os.environ["KAFKA_CA_PATH"]
    return conf


def notify(kind: str, ev: dict) -> None:
    text = (f"[{kind.upper()}] bus {ev['bus_id']} camera {ev['camera_id']} "
            f"score {ev['score']:.2f} at {ev['detected_at']} event {ev['event_id']}")
    print(text, flush=True)
    if WEBHOOK:
        requests.post(WEBHOOK, json={"text": text}, timeout=5)


def main():
    c = Consumer(kafka_conf())
    c.subscribe([TOPIC])
    dedupe = Deduper()
    while True:
        msg = c.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("kafka error:", msg.error(), flush=True)
            continue
        ev = json.loads(msg.value())
        if not dedupe.seen(ev["event_id"]):
            notify(route(ev), ev)
        c.commit(msg)  # commit after handling: at least once


if __name__ == "__main__":
    main()
