# MLOps in the datacenter (OpenShift AI)

Training and packaging live here, not on the bus.

1. Fine-tune MoViNet A0 in an OpenShift AI workbench with your labeled clips.
2. Run `pipeline.py` as a Data Science Pipeline: train, evaluate, package.
3. Package the model as a modelcar (OCI image with the model files) and push to Quay.
4. Roll the new model tag to the buses with Red Hat Edge Manager (change the manifest image or the model image).
5. Hard cases: buses only send High and Suspicious clips. Those clips in S4 are your review queue and your next training set.
