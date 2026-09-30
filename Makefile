ENGINE ?= podman
SERVICES = camera-capture inference-onnx inference-tensorrt inference-tensorrt-jetson \
           stream-viewer clip-recorder aggression-detector passenger-analytics \
           event-publisher alert-service ops-dashboard
TESTED_SERVICES = services/camera-capture services/clip-recorder services/aggression-detector \
                   services/passenger-analytics services/event-publisher \
                   services/alert-service services/ops-dashboard

.PHONY: test dev-up dev-up-cam dev-down dev-logs sim-pax bucket edge-os edge-os-jetson

test:
	@for d in $(TESTED_SERVICES); do echo "== $$d"; (cd $$d && python -m pytest -q tests) || exit 1; done

dev-up:
	$(ENGINE) compose up -d --build
	@echo ""
	@echo "No camera device is passed through, so camera-capture loops videos/*.mp4."
	@echo "First run only, create the S4 bucket:  make bucket"
	@echo "Dashboard:       http://localhost:8080"
	@echo "Stream viewer:   http://localhost:8084"
	@echo "Real USB webcam? make dev-down && make dev-up-cam"

dev-up-cam:
	$(ENGINE) compose -f compose.yaml -f compose.cam.yaml up -d --build
	@echo ""
	@echo "--------------------------------------"
	@echo "DONE!"
	@echo "--------------------------------------"
	@echo "Dashboard:       http://localhost:8080"
	@echo "Stream viewer:   http://localhost:8084"

dev-down:
	$(ENGINE) compose down

dev-clean:
	$(ENGINE) compose down --remove-orphans && \
	$(ENGINE) image ls --format '{{.Repository}}:{{.Tag}}' | grep '^docker.io/library/video-action-recognition-' | xargs -r podman image rm

dev-logs:
	$(ENGINE) compose logs -f aggression-detector passenger-analytics event-publisher

bucket:
	AWS_ACCESS_KEY_ID=s4admin AWS_SECRET_ACCESS_KEY=s4secret \
	  aws --endpoint-url http://localhost:7480 s3 mb s3://bus-evidence || true

sim-pax:
	python tools/simulate.py --passengers 5 --publisher http://localhost:8085

edge-os:
	$(ENGINE) build -f infra/devices/device-images/video-detector/Containerfile \
	  -t quay.io/CHANGEME/action-video-detection-os:latest .

edge-os-jetson:
	$(ENGINE) build --platform linux/arm64 \
	  -f infra/devices/device-images/video-detector-jetson/Containerfile \
	  -t quay.io/CHANGEME/action-video-detection-os-jetson:latest .