.DEFAULT_GOAL := help

APP_ID := caption_obvious
APP_VERSION := $(shell sed -n 's:.*<image-tag>\(.*\)</image-tag>.*:\1:p' appinfo/info.xml)
IMAGE := ghcr.io/meatybot/$(APP_ID):$(APP_VERSION)
# nextcloud-docker-dev: the container running Nextcloud, and the daemon to deploy with.
NC_CONTAINER ?= master-nextcloud-1
DAEMON ?= harp_docker
OCC := docker exec -u www-data $(NC_CONTAINER) php occ

.PHONY: help
help:
	@echo "Caption Obvious $(APP_VERSION)"
	@echo ""
	@echo "  make build      build the frontend into ex_app/js (npm ci + webpack)"
	@echo "  make lint       eslint, isort, black, ruff and pylint"
	@echo "  make image      build $(IMAGE) locally"
	@echo "  make push       build for amd64 and arm64 and push $(IMAGE) (CI does this on release)"
	@echo ""
	@echo "  For nextcloud-docker-dev, run on the host. NC_CONTAINER=$(NC_CONTAINER) DAEMON=$(DAEMON)"
	@echo "  make deploy     install the local image: re-registers $(APP_ID) from appinfo/info.xml"
	@echo "  make undeploy   remove $(APP_ID)"

.PHONY: build
build:
	npm ci --no-audit --no-fund
	npm run build

.PHONY: lint
lint:
	npm run lint
	isort --check-only ex_app/lib
	black --check ex_app/lib
	ruff check ex_app/lib
	pylint --recursive=y ex_app/lib

.PHONY: image
image:
	docker build -t $(IMAGE) .

.PHONY: push
push:
	docker buildx build --push --platform linux/amd64,linux/arm64 --tag $(IMAGE) .

# The daemon pulls the image unless its registry mapping is "local" (app_api:daemon:registry:add
# --registry-from ghcr.io --registry-to local); with that mapping it uses the image built by `make image`.
.PHONY: deploy
deploy: image
	docker cp appinfo/info.xml $(NC_CONTAINER):/tmp/$(APP_ID)-info.xml
	$(OCC) app_api:app:unregister $(APP_ID) --silent || true
	$(OCC) app_api:app:register $(APP_ID) $(DAEMON) --info-xml /tmp/$(APP_ID)-info.xml --wait-finish

.PHONY: undeploy
undeploy:
	$(OCC) app_api:app:unregister $(APP_ID)
