SHELL := /bin/sh
.PHONY: build run verify clean ci
.NOTPARALLEL: ci
IMAGE := quotes-scrapper:lab1

build:
	docker build --progress=plain -t $(IMAGE) .

run:
	mkdir -p out
	docker run --rm --init --shm-size=1g --user "$$(id -u):$$(id -g)" --mount "type=bind,source=$(CURDIR)/out,target=/app/out" $(IMAGE)

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
