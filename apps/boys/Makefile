SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy

check:
	$(PYTHON) -m pytest -q apps/boys/tests kubernetes/boys/tests
	cd kubernetes/boys && npm test

diff:
	$(PYTHON) -m scripts.app_diff --app boys --package kubernetes/boys

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= boys BOYS_ENABLED=true BOYS_REVISION=$(REVISION)
