# Demo script (about 12 minutes)

1. Show the architecture diagram. Point at the edge device box: everything in it runs on one
   small box (x86_64 or Jetson), with only the event-publisher talking to the datacenter.
2. Open the stream viewer (`http://localhost:8084` or the device's port 8080). Show live
   bounding boxes from the real YOLO detector, not a mock.
3. Open the ops dashboard. Point out it is read-only and empty so far.
4. Walk two people quickly through frame (or play a test clip). Narrate the path out loud as
   it happens: Tier 1 gate opens on persons + motion, clip-recorder cuts the clip, the
   classifier scores it, a High or Suspicious event lands on the dashboard with a working
   evidence link.
5. Walk through slowly, or with one person. Show nothing fires: gate stays closed, no GPU
   classifier run, no event.
6. Cut the datacenter link (block egress or scale the AMQ Streams route to 0). Trigger another
   event. Show the outbox filling (`GET /v1/stats` on event-publisher). Restore the link and
   watch it flow, evidence first, then the event.
7. Show Edge Manager rolling a new model or OS image to a device; mention rollback is one
   click, and that the same rollout targets both the x86_64 and the Jetson fleet.
8. Show the MLOps loop: hard clips in S4 feed the OpenShift AI pipeline, which packages a new
   modelcar to Quay for the next rollout.
