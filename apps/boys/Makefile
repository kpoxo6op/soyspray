SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy smoke restore-check

check:
	$(PYTHON) -m pytest -q apps/boys/tests
	cd apps/boys && npm test

diff:
	$(PYTHON) -m scripts.app_diff --app boys --package apps/boys/manifests

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= boys BOYS_ENABLED=true BOYS_REVISION=$(REVISION)

smoke:
	@node apps/boys/smoke.js

restore-check:
	$(PYTHON) -m apps.boys.restore_check
