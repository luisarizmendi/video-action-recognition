import json
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Dict

from .outbox import PRIORITY_HEALTH


def check_http(url: str, timeout: float = 2.0) -> str:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return "ok" if 200 <= r.status < 300 else "down"
    except Exception:
        return "down"


def build_health_event(bus_id: str, components: Dict[str, str], pending: int, oldest_age_s: float) -> dict:
    return {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "bus_id": bus_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "components": components,
        "outbox": {"pending": pending, "oldest_age_s": round(oldest_age_s, 1)},
    }


def enqueue_health(outbox, settings) -> None:
    components = {name: check_http(url) for name, url in settings.health_targets.items()}
    pending, oldest = outbox.stats()
    ev = build_health_event(settings.bus_id, components, pending, oldest)
    outbox.enqueue(ev["event_id"], settings.topic_health, settings.bus_id,
                   json.dumps(ev), PRIORITY_HEALTH)
