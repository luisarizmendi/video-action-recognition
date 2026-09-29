Place model files here for local testing with compose.yaml:
- `model.onnx` — YOLO object detector (person, etc.) for inference-onnx.
  A ready one exists at `models/yolo26n.onnx` in the object-detection-custom
  repo this was built from; copy it here and rename, or set INFERENCE_MODEL.
- `movinet-a0/` — the action classifier aggression-detector's classifier.py
  will load once you replace the stub (not needed to run the demo).
