SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy

check:
	$(PYTHON) -m pytest -q apps/vaultwarden/tests
	$(PYTHON) -m ansiblelint apps/vaultwarden/*.yml
	kubectl kustomize apps/vaultwarden/argocd >/dev/null

diff:
	$(PYTHON) -m scripts.app_diff --app vaultwarden --package apps/vaultwarden/manifests

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= vaultwarden VAULTWARDEN_ENABLED=true VAULTWARDEN_REVISION=$(REVISION)

.DEFAULT:
	@printf 'unknown: vaultwarden has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
