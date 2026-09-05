SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy

check:
	$(PYTHON) -m pytest -q apps/headlamp/tests tests/test_argocd_root.py tests/test_sso_headlamp.py
	kubectl kustomize apps/headlamp/argocd >/dev/null

diff:
	$(PYTHON) -m scripts.app_diff --app headlamp --pushed

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= headlamp HEADLAMP_REVISION=$(REVISION)

.DEFAULT:
	@printf 'unknown: headlamp has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
