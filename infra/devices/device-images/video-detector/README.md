# video-detector (x86_64, Podman + Quadlets)

The default, MicroShift-free way to run the edge device. `systemd` starts each
service directly from the Quadlet units in `quadlets/`, in dependency order:

```
camera-capture ──► inference-onnx ──► aggression-detector ──► event-publisher
                                  └──► passenger-analytics ──┘
                       clip-recorder ◄── aggression-detector (HTTP trigger)
```

## Build and enroll
```bash
podman build -f Containerfile -t quay.io/CHANGEME/video-action-recognition-os:latest ../../../..
```
Enroll the built image with Red Hat Edge Manager (see `../../device-management/`),
or `bootc switch` it directly on a test box.

## Try the quadlets without bootc first
On any RHEL/Fedora box with Podman 5+:
```bash
mkdir -p ~/.config/containers/systemd
cp quadlets/*.container ~/.config/containers/systemd/
systemctl --user daemon-reload
systemctl --user start camera-capture inference-onnx clip-recorder \
  aggression-detector passenger-analytics event-publisher
```

## Swapping the inference backend
Only one `inference-*` quadlet should run at a time (they share port 5555).
Replace `quadlets/inference-onnx.container` with a copy of
`../../../../services/inference-tensorrt` wiring for a desktop/server NVIDIA
GPU. For Jetson, use the `video-detector-jetson` device image instead — it
needs the L4T TensorRT base image, not this one.

## MicroShift instead of plain Podman
If you would rather run this as Kubernetes pods, see `microshift/`. It is the
same services, same images, as MicroShift manifests. Use one approach or the
other, not both, on the same box.

## Known work items
- GPU: NVIDIA driver + CDI in the bootc image if you are not on pure CPU ONNX.
- Pull secret for `quay.io/CHANGEME` in `/etc/containers/registries.conf`.
- `RTSP_URL` in `camera-capture.container` if the source is a VMS (e.g. Nx Witness)
  instead of a USB camera.
- Kafka/S3 endpoints and credentials for event-publisher: see
  `../../../../services/event-publisher` and `/etc/video-action-recognition/bus.env`.
