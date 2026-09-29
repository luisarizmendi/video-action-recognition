# S4 (evidence storage)

S4 is a small S3 compatible store (Ceph RGW + web UI) from Red Hat AI Services BU:
https://github.com/rh-aiservices-bu/s4

It is a good fit for a demo. Upstream describes it as made for POCs and demos, so plan a swap
(for example OpenShift Data Foundation object storage) if this ever goes past a demo.

## Install
```bash
git clone https://github.com/rh-aiservices-bu/s4.git /tmp/s4
helm install s4 /tmp/s4/charts/s4 --namespace bus-s4 --create-namespace
oc get route s4 -n bus-s4 -o jsonpath='{.spec.host}'
```
Read the upstream deployment guide for auth, storage size and the S3 route. Change the default
credentials (`s4admin` / `s4secret`) before you expose anything.

## Bucket
```bash
export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...
export AWS_ENDPOINT_URL=https://<s3 route of s4>
aws s3 mb s3://bus-evidence
```
Set `S3_ENDPOINT` in `edge/manifests/base/configmap.yaml` to the S3 route (port 7480 service).

## Optional
S4 supports webhook bucket notifications. You can point them at a small service that
republishes "evidence stored" to AMQ Streams. Not needed for the base demo.
