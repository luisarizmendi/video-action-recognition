# What is Red Hat, what is custom, what is third party

| Layer | Component | Source |
| --- | --- | --- |
| Edge OS | RHEL image mode (bootc) | Red Hat |
| Edge runtime | Podman + Quadlets (default) or MicroShift (optional) | Red Hat |
| Fleet and updates | Red Hat Edge Manager | Red Hat |
| Datacenter platform | OpenShift Container Platform | Red Hat |
| Messaging | AMQ Streams (Red Hat Streams for Apache Kafka) | Red Hat |
| MLOps | Red Hat OpenShift AI (workbench, pipelines, model serving, registry) | Red Hat |
| Registry | Red Hat Quay | Red Hat |
| GitOps | OpenShift GitOps | Red Hat |
| Evidence storage | S4 | Red Hat AI Services BU project, demo grade, not a supported product |
| GPU stack | NVIDIA driver, toolkit, device plugin, TensorRT, L4T (Jetson) | NVIDIA |
| VMS (optional, for RTSP) | Nx Witness | Network Optix |
| Object detector | YOLO (onnx/tensorrt) | Ultralytics / open source |
| Action classifier | MoViNet A0 | Google, open source |
| camera-capture, inference-onnx, inference-tensorrt(-jetson), stream-viewer | Real-time video and detection pipeline, ported from the object-detection-custom project | **Custom, from your own repo** |
| clip-recorder | Ring buffer and evidence clip cutting | **Custom, new** |
| aggression-detector | Tier 1 gate, classifier wrapper, decision, ZeroMQ consumer | **Custom** |
| passenger-analytics | Centroid tracker, line counter, ZeroMQ consumer | **Custom** |
| event-publisher | Outbox, claim check, health | **Custom** |
| alert-service | Routing and notify | **Custom** |
| ops-dashboard | Read-only view | **Custom** |
| MoViNet fine-tuning pipeline | Pipeline and data | **Custom** |

The custom code is the demo's glue and its two real-time pipelines (frames over shared
memory, detections over ZeroMQ). The Red Hat story is that the platform, the messaging, the
MLOps, and the edge lifecycle (including Jetson) are products, and only the video and event
logic on top of them is yours.
