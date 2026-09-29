import os

from .api import create_app
from .config import Settings
from .outbox import Outbox
from .sinks import KafkaSink, S3EvidenceStore

settings = Settings.from_env()
os.makedirs(os.path.dirname(settings.outbox_path), exist_ok=True)
app = create_app(settings, Outbox(settings.outbox_path), S3EvidenceStore(settings), KafkaSink(settings))
