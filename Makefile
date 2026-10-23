SHELL := /bin/sh
.DEFAULT_GOAL := build
.NOTPARALLEL:
.PHONY: prepare doctor build tools-build up wait init fmt plan provision deploy run verify status logs clean destroy test ci ci-check

PROJECT ?= quotes-lab2
FLOCI_PORT ?= 4566
INFRA_DIR ?= $(CURDIR)/infra
DC = INFRA_DIR="$(INFRA_DIR)" FLOCI_PORT="$(FLOCI_PORT)" docker compose --project-name "$(PROJECT)"
TF = $(DC) run --rm -T --no-deps terraform
TOOLS = $(DC) run --rm -T --no-deps tools

prepare:
	@mkdir -p .runtime out
	@touch .runtime/app.env

doctor:
	docker version
	docker compose version

tools-build: prepare
	$(DC) build tools

build: prepare
	$(DC) build worker tools

up: prepare
	$(DC) up -d floci

wait: prepare
	$(TOOLS) wait

init: prepare
	$(TF) init -input=false

fmt: prepare
	$(TF) fmt

plan: up tools-build wait init
	$(TF) plan -input=false

provision: up tools-build wait init
	$(TF) apply -auto-approve -input=false
	$(TF) output -json > .runtime/terraform-output.json
	$(TOOLS) configure

deploy: build up wait
	$(TF) output -json > .runtime/terraform-output.json
	$(TOOLS) configure
	$(DC) up -d --no-deps --wait --wait-timeout 90 worker

run: prepare
	$(TOOLS) submit

verify: prepare
	$(TOOLS) verify

status: prepare
	$(DC) ps -a
	$(TOOLS) status

logs: prepare
	$(DC) logs --tail=100 worker floci

clean: prepare
	$(DC) rm -sf worker
	@if docker image inspect quotes-scrapper:lab2 >/dev/null 2>&1; then docker image rm quotes-scrapper:lab2; fi
	rm -rf out

destroy: prepare
	$(DC) stop worker
	@if ! docker image inspect quotes-tools:lab2 >/dev/null 2>&1; then $(MAKE) tools-build; fi
	@if [ -f "$(INFRA_DIR)/terraform.tfstate" ]; then \
		$(MAKE) up wait init && $(TF) destroy -auto-approve -input=false; \
	fi
	$(DC) down --volumes --remove-orphans
	rm -f .runtime/app.env .runtime/terraform-output.json

test: tools-build
	$(DC) run --rm -T --no-deps --entrypoint python tools -m unittest discover -s tests -v

# A separate Compose project and state directory keep local resources untouched.
ci: prepare
	mkdir -p .runtime/ci-infra
	cp infra/*.tf infra/.terraform.lock.hcl .runtime/ci-infra/
	$(MAKE) ci-check PROJECT="$(PROJECT)-ci" INFRA_DIR="$(CURDIR)/.runtime/ci-infra" FLOCI_PORT=0

ci-check: prepare
	@set -eu; \
	trap '$(DC) down --volumes --remove-orphans' EXIT; \
	$(DC) build tools; \
	$(DC) up -d floci; \
	$(TOOLS) wait; \
	$(TF) init -input=false -lockfile=readonly; \
	$(TF) fmt -check; \
	$(TF) validate; \
	$(TF) plan -input=false -out=ci.tfplan
