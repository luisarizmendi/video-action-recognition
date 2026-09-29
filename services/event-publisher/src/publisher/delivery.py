import os
import time
from typing import Dict, Optional


def deliver_once(outbox, store, sink, now: Optional[float] = None, batch: int = 20,
                 cleanup_clips: bool = True) -> Dict[str, int]:
    """Try to deliver due rows. Order matters:
    1. upload evidence to S4
    2. publish the event to Kafka
    So a consumer never sees an event that points to missing evidence."""
    now = now if now is not None else time.time()
    delivered = failed = 0
    for row in outbox.due(now, batch):
        try:
            if row.clip_path and not row.evidence_done:
                store.put(row.clip_path, row.evidence_bucket, row.evidence_key)
                outbox.mark_evidence_done(row.id)
            sink.send(row.topic, row.key, row.payload.encode())
            outbox.mark_delivered(row.id)
            delivered += 1
            if cleanup_clips and row.clip_path:
                try:
                    os.remove(row.clip_path)
                except OSError:
                    pass
        except Exception as exc:  # link down, auth error, S4 down, etc.
            outbox.mark_failed(row.id, now, repr(exc))
            failed += 1
            break  # link is probably down, do not burn time on the rest of the batch
    return {"delivered": delivered, "failed": failed}
