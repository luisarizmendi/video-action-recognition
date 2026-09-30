"""Skeleton Kubeflow pipeline for OpenShift AI. Fill in the three steps.
Compile:  python pipeline.py   then upload aggression-pipeline.yaml in OpenShift AI.
"""
from kfp import compiler, dsl


@dsl.component(base_image="registry.access.redhat.com/ubi9/python-311:latest")
def train(dataset_bucket: str, model_out: dsl.Output[dsl.Model]):
    # TODO: pull labeled clips from S4, fine-tune MoViNet A0, save to model_out.path
    open(model_out.path, "w").write("placeholder")


@dsl.component(base_image="registry.access.redhat.com/ubi9/python-311:latest")
def evaluate(model: dsl.Input[dsl.Model]) -> float:
    # TODO: run the eval set, return the metric you gate on (recall at a fixed false alarm rate)
    return 0.0


@dsl.component(base_image="registry.access.redhat.com/ubi9/python-311:latest")
def package_modelcar(model: dsl.Input[dsl.Model], image: str):
    # TODO: build an OCI image with the model files (buildah) and push to Quay
    print("push", image)


@dsl.pipeline(name="aggression-model")
def aggression_pipeline(dataset_bucket: str = "bus-training", image: str = "quay.io/luisarizmendi/movinet-a0:latest"):
    t = train(dataset_bucket=dataset_bucket)
    e = evaluate(model=t.outputs["model_out"])
    package_modelcar(model=t.outputs["model_out"], image=image).after(e)


if __name__ == "__main__":
    compiler.Compiler().compile(aggression_pipeline, "aggression-pipeline.yaml")
