# Registry (Red Hat Quay)

All images build to `quay.io/luisarizmendi/video-action-recognition-<service>`
(see `.github/workflows/build-images.yaml`). The Jetson inference image and
every other edge service publish as multi-arch manifests (amd64 + arm64),
following the `build-all.sh` / manifest-list pattern from the original
object-detection-custom repo. `alert-service` and `ops-dashboard` are
datacenter-only and stay amd64.
