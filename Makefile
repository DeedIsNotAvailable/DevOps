SHELL := /bin/sh
.DEFAULT_GOAL := build
.PHONY: build run verify test clean ci cache-check dev-setup dev
.NOTPARALLEL: ci cache-check

IMAGE ?= quotes-scrapper:lab1
BUILD_CONTEXT ?= .
BUILD_LOG ?= .checks/build.log
RUN_USER := $(shell id -u):$(shell id -g)

build:
	@mkdir -p .checks
	@docker build --progress=plain --target production -t "$(IMAGE)" "$(BUILD_CONTEXT)" > "$(BUILD_LOG)" 2>&1 || { cat "$(BUILD_LOG)"; exit 1; }
	@cat "$(BUILD_LOG)"

run:
	@mkdir -p out
	docker run --rm --init --shm-size=1g --user "$(RUN_USER)" --mount "type=bind,source=$(CURDIR)/out,target=/app/out" "$(IMAGE)"

verify:
	docker run --rm --user "$(RUN_USER)" --mount "type=bind,source=$(CURDIR)/out,target=/app/out,readonly" "$(IMAGE)" node src/verify-result.mjs

test:
	docker run --rm --init --shm-size=1g --user "$(RUN_USER)" --mount "type=bind,source=$(CURDIR)/test,target=/app/test,readonly" "$(IMAGE)" npm test

clean:
	@if docker image inspect "$(IMAGE)" >/dev/null 2>&1; then docker image rm "$(IMAGE)"; fi
	rm -rf out

# Check both rebuild scenarios without changing tracked source files.
cache-check:
	$(MAKE) clean
	$(MAKE) build BUILD_LOG=.checks/rebuild.log
	awk -f scripts/check-cache.awk .checks/rebuild.log
	@mkdir -p .checks/context/src
	cp Dockerfile package.json package-lock.json .checks/context/
	cp src/*.mjs .checks/context/src/
	@printf '\n// Temporary code change for cache verification.\n' >> .checks/context/src/index.mjs
	$(MAKE) build BUILD_CONTEXT=.checks/context BUILD_LOG=.checks/code-change.log
	awk -f scripts/check-cache.awk .checks/code-change.log

ci:
	$(MAKE) build
	$(MAKE) test
	$(MAKE) run
	$(MAKE) verify
	$(MAKE) cache-check
	$(MAKE) clean
	@test -z "$$(git status --porcelain)" || { git status --short; exit 1; }

dev-setup:
	npm ci
	npx playwright install --with-deps chromium

dev:
	npm start
