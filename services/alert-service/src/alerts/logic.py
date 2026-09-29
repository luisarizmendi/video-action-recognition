from collections import OrderedDict


class Deduper:
    """Keeps the last N event ids. The edge may send an event twice after a retry."""

    def __init__(self, size: int = 10000):
        self._seen = OrderedDict()
        self._size = size

    def seen(self, event_id: str) -> bool:
        if event_id in self._seen:
            return True
        self._seen[event_id] = None
        if len(self._seen) > self._size:
            self._seen.popitem(last=False)
        return False


def route(event: dict) -> str:
    """high -> page now, suspicious -> review queue."""
    return "page" if event.get("severity") == "high" else "review"
