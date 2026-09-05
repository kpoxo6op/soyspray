SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy

check:
	$(PYTHON) -m pytest -q apps/obsidian-livesync/tests
	$(PYTHON) -m ansiblelint apps/obsidian-livesync/*.yml
	kubectl kustomize apps/obsidian-livesync/argocd >/dev/null

diff:
	$(PYTHON) -m scripts.app_diff --app obsidian-livesync --package playbooks/argocd/applications/database/obsidian-livesync

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= obsidian-livesync OBSIDIAN_ENABLED=true OBSIDIAN_REVISION=$(REVISION)

.DEFAULT:
	@printf 'unknown: obsidian-livesync has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
