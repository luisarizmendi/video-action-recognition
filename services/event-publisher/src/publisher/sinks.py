import boto3
from botocore.config import Config
from confluent_kafka import Producer

from .config import Settings


class DeliveryError(Exception):
    pass


class KafkaSink:
    """Idempotent producer to AMQ Streams. The broker is in the datacenter."""

    def __init__(self, s: Settings):
        conf = {
            "bootstrap.servers": s.kafka_bootstrap,
            "enable.idempotence": True,
            "acks": "all",
            "message.timeout.ms": 30000,
            "socket.keepalive.enable": True,
        }
        if s.kafka_username:
            conf.update({
                "security.protocol": "SASL_SSL",
                "sasl.mechanisms": "SCRAM-SHA-512",
                "sasl.username": s.kafka_username,
                "sasl.password": s.kafka_password or "",
            })
            if s.kafka_ca_path:
                conf["ssl.ca.location"] = s.kafka_ca_path
        self._p = Producer(conf)

    def send(self, topic: str, key: str, value: bytes) -> None:
        errors = []

        def on_delivery(err, _msg):
            if err is not None:
                errors.append(err)

        self._p.produce(topic, key=key, value=value, on_delivery=on_delivery)
        remaining = self._p.flush(15)
        if remaining or errors:
            # A timeout can still deliver later. The retry may then create a duplicate.
            # Consumers dedupe on event_id, so this is safe.
            raise DeliveryError(f"kafka delivery failed: {errors or 'flush timeout'}")


class S3EvidenceStore:
    """Uploads clips to S4 (S3 compatible, Ceph RGW)."""

    def __init__(self, s: Settings):
        self._c = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint,
            aws_access_key_id=s.s3_access_key,
            aws_secret_access_key=s.s3_secret_key,
            region_name="us-east-1",
            verify=s.s3_ca_bundle if s.s3_ca_bundle else True,
            config=Config(signature_version="s3v4", retries={"max_attempts": 2},
                          connect_timeout=5, read_timeout=30,
                          s3={"addressing_style": "path"}),
        )

    def put(self, path: str, bucket: str, key: str) -> None:
        self._c.upload_file(path, bucket, key, ExtraArgs={"ContentType": "video/mp4"})
