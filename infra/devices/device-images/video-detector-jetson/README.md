# video-detector-jetson (NVIDIA Jetson, JetPack 6.x, aarch64)

Same services as `../video-detector/`, with `inference-tensorrt-jetson`
instead of `inference-onnx`. Build with `--platform linux/arm64`, or natively
on the Jetson.

```bash
podman build --platform linux/arm64 -f Containerfile \
  -t quay.io/luisarizmendi/video-action-recognition-os-jetson:latest ../../../..
```

For the Jetson-specific base layer (L4T userspace, JetPack packages), follow
https://github.com/luisarizmendi/bootc-images/tree/main/rhel-jetson-object-detection
and adapt the `FROM` line and NVIDIA package steps here — that repo already
has a working Jetson bootc recipe; this Containerfile only adds the
video-action-recognition quadlets on top of it.

First boot builds the TensorRT `.engine` from the bundled ONNX model
(a few minutes); it is cached under `/var/home/detector/models`, so later
boots start instantly.
