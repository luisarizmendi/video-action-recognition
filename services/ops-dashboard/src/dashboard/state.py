import threading
from collections import deque


class State:
    """In-memory view for the demo. Read-only for users. Swap for a DB later."""

    def __init__(self, keep: int = 200):
        self._lock = threading.Lock()
        self._seq = 0
        self.items = deque(maxlen=keep)      # (seq, kind, payload)
        self.seen = set()
        self.buses = {}                      # bus_id -> latest passenger + health

    def add(self, kind: str, payload: dict) -> bool:
        with self._lock:
            eid = payload.get("event_id")
            if eid in self.seen:
                return False
            self.seen.add(eid)
            self._seq += 1
            self.items.append((self._seq, kind, payload))
            bus = self.buses.setdefault(payload.get("bus_id", "?"), {})
            if kind == "passenger":
                bus["occupancy"] = payload["occupancy"]
                bus["boarded"] = payload["boarded"]
                bus["alighted"] = payload["alighted"]
            elif kind == "health":
                bus["health"] = payload["components"]
                bus["outbox"] = payload["outbox"]
            elif kind == "safety":
                bus["last_alert"] = payload["severity"]
            return True

    def since(self, seq: int):
        with self._lock:
            return [i for i in self.items if i[0] > seq]

    def snapshot(self):
        with self._lock:
            return {"buses": dict(self.buses), "items": list(self.items)}
