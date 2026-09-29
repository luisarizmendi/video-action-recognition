# Optional: MicroShift instead of Podman + Quadlets

Same 6 services as `../quadlets/`, as MicroShift manifests, for anyone who
would rather manage the edge device with Kubernetes resources than systemd
units. Pick one approach per device, not both.

Apply at boot from `/etc/microshift/manifests.d/video-detector/`, or:
```bash
oc apply -k .
```

## The one big difference from a normal cluster app
camera-capture, inference-onnx and clip-recorder must share the host's real
`/dev/shm`, the same way the Quadlet units do with `Volume=/dev/shm:/dev/shm`.
A Kubernetes `emptyDir` would NOT do this: each pod gets its own private
tmpfs. These manifests use a `hostPath` volume instead, which only works
because this is a single-node edge device and every pod lands on that one
node. Do not lift this pattern into a multi-node cluster as-is.

## Not included here
- `stream-viewer` (debug-only, add a Deployment + Service on port 8080 the
  same way as `aggression-detector.yaml` if you want it)
- The Jetson `inference-tensorrt-jetson` variant — swap `inference-onnx.yaml`
  for a copy using that image and add `AddDevice`-equivalent GPU resource
  requests once MicroShift's NVIDIA device plugin is set up
