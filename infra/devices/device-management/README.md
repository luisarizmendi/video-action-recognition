# Device management (Red Hat Edge Manager)

Two fleets: `video-detector-x86` (desktop/server GPU or CPU-only) and
`video-detector-jetson`. Both push OS image updates and the identity file
event-publisher reads for its Kafka and S3 credentials. Rollback and canary
rollout are handled by Edge Manager, not by anything in this repo.
