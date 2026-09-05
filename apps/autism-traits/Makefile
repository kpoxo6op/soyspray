SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
PYTHON ?= soyspray-venv/bin/python
REVISION ?= HEAD
.PHONY: check diff deploy

check:
	$(PYTHON) -m pytest -q apps/autism-traits/tests
	cd apps/autism-traits/app && npm run check && npm run test:e2e

diff:
	$(PYTHON) -m scripts.app_diff --app autism-traits --package apps/autism-traits/manifests

deploy:
	$(MAKE) --no-print-directory -f Makefile APP= autism-traits AUTISM_TRAITS_ENABLED=true AUTISM_TRAITS_REVISION=$(REVISION)
