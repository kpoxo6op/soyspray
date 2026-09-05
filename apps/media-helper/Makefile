SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy

check:
	$(PYTHON) -m pytest -q apps/media-helper/tests tests/test_argocd_root.py tests/test_live_tv.py
	$(PYTHON) -m ansiblelint apps/media-helper/adopt.yml
	kubectl kustomize apps/media-helper/argocd >/dev/null

diff:
	$(PYTHON) -m scripts.app_diff --app media-helper --pushed

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= media-helper MEDIA_HELPER_REVISION=$(REVISION)

.DEFAULT:
	@printf 'unknown: media-helper has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
