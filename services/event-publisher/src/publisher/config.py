import os
from dataclasses import dataclass
from typing import Dict, Optional


def load_env_file(path: str) -> Dict[str, str]:
    """Read KEY=VALUE lines. Used for /etc/bus-edge/bus.env, pushed by Edge Manager."""
    out: Dict[str, str] = {}
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


@dataclass(frozen=True)
class Settings:
    bus_id: str
    kafka_bootstrap: str
    kafka_username: Optional[str]
    kafka_password: Optional[str]
    kafka_ca_path: Optional[str]
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_ca_bundle: Optional[str]
    outbox_path: str
    outbox_max_rows: int
    topic_safety: str
    topic_passenger: str
    topic_health: str
    health_targets: Dict[str, str]
    health_interval_s: int

    @classmethod
    def from_env(cls) -> "Settings":
        file_vals = load_env_file(os.environ.get("BUS_ENV_FILE", "/etc/bus-edge/bus.env"))

        def get(name: str, default: Optional[str] = None) -> Optional[str]:
            return os.environ.get(name, file_vals.get(name, default))

        targets: Dict[str, str] = {}
        for item in (get("HEALTH_TARGETS", "") or "").split(","):
            if "=" in item:
                name, url = item.split("=", 1)
                targets[name.strip()] = url.strip()

        return cls(
            bus_id=get("BUS_ID", "bus-demo-001"),
            kafka_bootstrap=get("KAFKA_BOOTSTRAP", "localhost:9092"),
            kafka_username=get("KAFKA_USERNAME"),
            kafka_password=get("KAFKA_PASSWORD"),
            kafka_ca_path=get("KAFKA_CA_PATH"),
            s3_endpoint=get("S3_ENDPOINT", "http://localhost:7480"),
            s3_access_key=get("S3_ACCESS_KEY", "s4admin"),
            s3_secret_key=get("S3_SECRET_KEY", "s4secret"),
            s3_bucket=get("S3_BUCKET", "bus-evidence"),
            s3_ca_bundle=get("S3_CA_BUNDLE"),
            outbox_path=get("OUTBOX_PATH", "/var/lib/outbox/outbox.db"),
            outbox_max_rows=int(get("OUTBOX_MAX_ROWS", "5000")),
            topic_safety=get("TOPIC_SAFETY", "bus.safety.events"),
            topic_passenger=get("TOPIC_PASSENGER", "bus.passenger.counts"),
            topic_health=get("TOPIC_HEALTH", "bus.edge.health"),
            health_targets=targets,
            health_interval_s=int(get("HEALTH_INTERVAL_S", "30")),
        )
