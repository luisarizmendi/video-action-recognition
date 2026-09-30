# video-action-recognition

Real-time aggression detection and passenger analytics for buses (or any fixed camera site),
built on Red Hat products plus a genuinely real-time video pipeline.

- Object detection: **ported from `object-detection-custom`** — real YOLO inference over
  shared memory and ZeroMQ, not a stand-in.
- Object store: **S4** (instead of MinIO).
- Messaging: **AMQ Streams in the datacenter** (no Kafka on the edge device).
- Edge deploy: **Podman + Quadlets by default, MicroShift optional.**
- Architectures: **x86_64 and NVIDIA Jetson.**

See [docs/architecture.md](docs/architecture.md) for the full diagram and event flow,
[docs/red-hat-vs-custom.md](docs/red-hat-vs-custom.md) for what is product, custom, or
third party, and [docs/demo-script.md](docs/demo-script.md) for a walkthrough.

## Layout
```
services/        11 services: camera-capture, inference-onnx/-tensorrt/-tensorrt-jetson,
                  stream-viewer, clip-recorder, aggression-detector, passenger-analytics,
                  event-publisher, alert-service, ops-dashboard
infra/
  messaging/      AMQ Streams (Kafka, topics, users) + contracts/events (JSON schemas)
  object-storage/ S4 install notes
  mlops/          OpenShift AI pipeline skeleton for the action classifier
  registry/       Quay / multi-arch build notes
  apps/           Datacenter deploy (alert-service, ops-dashboard) + GitOps root apps
  devices/
    device-images/
      video-detector/          x86_64: bootc Containerfile, Quadlets (default),
                                microshift/ (optional Kubernetes alternative)
      video-detector-jetson/   Jetson (aarch64): bootc Containerfile, Quadlets
    device-management/         Red Hat Edge Manager fleet definitions
models/           drop your .onnx / MoViNet files here for local testing
videos/           drop sample .mp4 files here (camera fallback source)
tools/            simulate.py — poke event-publisher directly for a quick datacenter test
compose.yaml      full realtime pipeline on a laptop (+ compose.nocam.yaml override)
```

## Status
| Piece | State |
| --- | --- |
| camera-capture (USB, video fallback) | Working, from object-detection-custom, unit tested |
| camera-capture (RTSP) | Added here. Needs a real RTSP source to verify (Nx Witness or similar) |
| inference-onnx / -tensorrt / -tensorrt-jetson | Working, from object-detection-custom, untouched |
| stream-viewer | Working, from object-detection-custom, untouched |
| clip-recorder | New. Working, unit tested (ring buffer + HTTP API, incl. async callback) |
| aggression-detector | Rewritten for ZeroMQ input. Tier 1 gate unit tested. Classifier is a stub |
| passenger-analytics | Rewritten for ZeroMQ input. Centroid tracker + line counter unit tested |
| event-publisher, alert-service, ops-dashboard | Unchanged, unit tested |
| Quadlets (x86_64 and Jetson) | Skeleton, check images/paths against your registry |
| MicroShift overlay | Skeleton, check `/dev/shm` hostPath caveat in its README |
| bootc images, Edge Manager fleet | Skeleton. Check against your versions |
| MoViNet A0 | Not included. Plug into `services/aggression-detector/src/detector/classifier.py` |

Nothing here was run on real hardware (a bus, a Jetson, a MicroShift cluster). The compose
stack is the only part actually exercised end to end (build + unit tests), and even that
needs a camera or a video file to see a full event.






## Try it on a laptop



need systemctl --user enable --now podman.socket 



```bash
make dev-up            # has a /dev/video0? this uses it
# or, no webcam:
make dev-up-nocam       # loops videos/*.mp4 instead — drop a clip there first
make bucket             # first run only
make sim-pax            # synthetic passenger windows, exercises the datacenter side alone
open http://localhost:8080   # dashboard
open http://localhost:8084   # stream viewer, live bounding boxes
```
To see a real safety event, put an `.mp4` with two people moving quickly into `videos/` before
`make dev-up-nocam` — the Tier 1 gate needs 2+ people and enough motion between frames.

## Run the unit tests
```bash
make test
```

## Deploy the datacenter side
1. Install operators (AMQ Streams, OpenShift AI, GitOps) on your OpenShift cluster.
2. Install S4: see `infra/object-storage/README.md`.
3. `oc apply -k infra/messaging` (or use `infra/apps/gitops-root-app.yaml`).
4. Copy the `dc-consumers` secret and the Kafka cluster CA into `video-detection-dc`, then
   `oc apply -k infra/apps`.
5. Get the Kafka external route host and the S4 route; you will need them on the edge device.

## Deploy the edge device
1. CI builds multi-arch images to GHCR (`.github/workflows/build-images.yaml`); point it and
   the Quadlet/MicroShift manifests at your own registry.
2. Pick x86_64 or Jetson: `infra/devices/device-images/video-detector/` or
   `.../video-detector-jetson/`. Build with `make edge-os` / `make edge-os-jetson`.
3. Enroll the device in Red Hat Edge Manager: `infra/devices/device-management/fleet.yaml`.
4. Read the device image's own `README.md` for open items (GPU/CDI, pull secret, RTSP URL if
   using a VMS instead of USB).

## Search and replace list
`CHANGEME` appears wherever you must put your own value (registry, routes, credentials).
