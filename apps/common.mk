# Shared settings for application Makefiles. No deployment actions run here.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
PYTHON ?= soyspray-venv/bin/python
# $(PYTHON) for recipes that change directory away from $(ROOT).
PYTHON_ABS = $(if $(filter /%,$(PYTHON)),$(PYTHON),$(if $(findstring /,$(PYTHON)),$(ROOT)/$(PYTHON),$(PYTHON)))
ANSIBLE ?= source soyspray-venv/bin/activate && ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu
