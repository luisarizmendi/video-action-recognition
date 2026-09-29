ENGINE ?= podman
SERVICES = camera-capture inference-onnx inference-tensorrt inference-tensorrt-jetson \
           stream-viewer clip-recorder aggression-detector passenger-analytics \
           event-publisher alert-service ops-dashboard
TESTED_SERVICES = services/camera-capture services/clip-recorder services/aggression-detector \
                   services/passenger-analytics services/event-publisher \
                   services/alert-service services/ops-dashboard

.PHONY: test dev-up dev-up-nocam dev-down dev-logs sim-pax bucket edge-os edge-os-jetson

test:
	@for d in $(TESTED_SERVICES); do echo "== $$d"; (cd $$d && python -m pytest -q tests) || exit 1; done

dev-up:
	$(ENGINE) compose up -d --build
	@echo ""
	@echo "First run only, create the S4 bucket:  make bucket"
	@echo "Dashboard:       http://localhost:8080"
	@echo "Stream viewer:   http://localhost:8084"
	@echo "No webcam?       make dev-down && make dev-up-nocam"

dev-up-nocam:
	$(ENGINE) compose -f compose.yaml -f compose.nocam.yaml up -d --build
	@echo "camera-capture will loop videos/*.mp4 instead of a USB camera."

dev-down:
	$(ENGINE) compose down

dev-logs:
	$(ENGINE) compose logs -f aggression-detector passenger-analytics event-publisher

bucket:
	AWS_ACCESS_KEY_ID=s4admin AWS_SECRET_ACCESS_KEY=s4secret \
	  aws --endpoint-url http://localhost:7480 s3 mb s3://bus-evidence || true

sim-pax:
	python tools/simulate.py --passengers 5 --publisher http://localhost:8085

edge-os:
	$(ENGINE) build -f infra/devices/device-images/video-detector/Containerfile \
	  -t quay.io/CHANGEME/video-action-recognition-os:latest .

edge-os-jetson:
	$(ENGINE) build --platform linux/arm64 \
	  -f infra/devices/device-images/video-detector-jetson/Containerfile \
	  -t quay.io/CHANGEME/video-action-recognition-os-jetson:latest .
