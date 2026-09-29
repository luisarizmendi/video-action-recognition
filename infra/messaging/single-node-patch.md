# Small demo cluster (1 broker)
Edit `kafka.yaml` and `topics.yaml`:
- KafkaNodePool `replicas: 1`
- Kafka `config`: set the three replication factors to 1 and `min.insync.replicas: 1`
- Topics: `replicas: 1`, `min.insync.replicas: "1"`
