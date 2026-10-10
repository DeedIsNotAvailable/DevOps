SHELL := /bin/sh
.PHONY: build run verify clean ci
.NOTPARALLEL: ci
IMAGE := quotes-scrapper:lab1
RUN_USER ?= $(shell id -u):$(shell id -g)

build:
	docker build --progress=plain -t $(IMAGE) .

run:
	mkdir -p out
	docker run --rm --init --shm-size=1g --user "$(RUN_USER)" --env HOME=/tmp --mount "type=bind,source=$(CURDIR)/out,target=/app/out" $(IMAGE)

verify:
	docker run --rm --mount "type=bind,source=$(CURDIR)/out,target=/app/out,readonly" $(IMAGE) python src/verify.py

clean:
	@if docker image inspect $(IMAGE) >/dev/null 2>&1; then docker image rm $(IMAGE); fi
	rm -rf out

ci:
	$(MAKE) build
	$(MAKE) run
	$(MAKE) verify
	$(MAKE) clean
