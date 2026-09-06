# Shared settings for application Makefiles. No deployment actions run here.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
PYTHON ?= soyspray-venv/bin/python
ANSIBLE ?= source soyspray-venv/bin/activate && ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu
REVISION ?= HEAD
