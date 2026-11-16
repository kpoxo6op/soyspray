SHELL := /bin/bash
.DEFAULT_GOAL := help
.SILENT:

VENV := soyspray-venv
PYTHON := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
PYTEST := $(PYTHON) -m pytest
INVENTORY := inventory/soycluster/hosts.yml
AUTISM_TRAITS_APP := apps/autism-traits/app

NODE0 := 192.168.20.10
NODE1 := 192.168.20.11
NODE2 := 192.168.20.12

# Every tracked kustomization renders in the gate. The ones that inflate a
# Helm chart need Helm and network access, so Argo CD renders those.
KUSTOMIZATIONS := $(shell git ls-files '*kustomization.yaml' | xargs grep -L '^helmCharts:' | xargs -n1 dirname | sort)

# Suites that need their own image dependencies run in their image workflows.
TEST_SKIP := apps/memes/tests/ apps/voice-assistant/intent-agent/tests/
TEST_PATHS := tests $(filter-out $(TEST_SKIP),$(sort $(dir $(shell git ls-files 'apps/*test_*.py'))))

# Every tracked .yml under these folders is Ansible (manifests use .yaml).
# The skip list holds files with known findings: rarely-run or destructive
# operations that cannot be re-tested casually. Fix one, then remove it here.
# apps/node-backup/bootstrap.yml loads a private vault file, so its syntax
# check fails on any machine that has the file but no vault password.
# recovery/provision-s3.yml needs the extra collections in
# playbooks/operations/recovery/requirements.yml.
ANSIBLE_LINT_SKIP := \
	apps/immich/recovery/restore.yml \
	apps/node-backup/bootstrap.yml \
	apps/node-backup/run.yml \
	playbooks/argocd/config/argocd-configure-ingress.yml \
	playbooks/argocd/config/argocd-enable-kustomize.yml \
	playbooks/argocd/config/argocd-publish-service.yml \
	playbooks/operations/networking/install-tailscale.yml \
	playbooks/operations/networking/remove-tailscale.yml \
	playbooks/operations/nodes/configure-openwrt-syslog.yml \
	playbooks/operations/nodes/configure-zigbee-udev-alias.yml \
	playbooks/operations/nodes/restart-node.yml \
	playbooks/operations/recovery/provision-s3.yml \
	playbooks/operations/recovery/select-authentik-database.yml \
	playbooks/operations/security/sync-certificates.yml \
	playbooks/operations/storage/initialize-longhorn-storage.yml \
	playbooks/operations/storage/prepare-longhorn-worker-ssd.yml \
	playbooks/operations/storage/prepare-media-usb-disk.yml \
	roles/app-secret/tasks/main.yml
ANSIBLE_FILES := $(filter-out $(ANSIBLE_LINT_SKIP),$(shell git ls-files 'apps/*.yml' 'argocd/*.yml' 'playbooks/*.yml' 'roles/*.yml'))

.PHONY: help setup act check shared-test shared-check full-check app-command diff smoke restore-check boys-check autism-traits-check docs-check docs-serve lint validate status-page-check prometheus-check \
	test render go voice-pe-render voice-pe-check voice-pe-compile voice-pe-upload status-page status-page-fallback argo-login \
	list-apps node0 node1 node2 clean

help: ## Show the operator commands
	printf 'Soyspray operator commands\n\n'
	awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install the pinned Kubespray and repository toolchain
	test -d $(VENV) || python3 -m venv $(VENV)
	git submodule update --init --recursive
	$(VENV)/bin/python -m pip install -r kubespray/requirements.txt -r requirements-dev.txt
	$(VENV)/bin/ansible-galaxy collection install -r requirements-ansible.yml
	cd $(AUTISM_TRAITS_APP) && npm ci
	cd apps/boys && npm ci && npx playwright install chromium

act: ## Open a shell in the project venv
	bash -lc 'source $(VENV)/bin/activate && exec bash -i'

check: ## Run app checks with APP, or the complete local gate without APP
	$(if $(strip $(APP)),$(MAKE) --no-print-directory app-command COMMAND=check,$(MAKE) --no-print-directory full-check)

shared-test:
	$(PYTEST) -q tests

shared-check: lint validate shared-test ## Run checks shared by every application deployment

full-check: lint validate test autism-traits-check boys-check docs-check ## Run the full repository gate explicitly
	printf '\nLocal gate passed.\n'

app-command:
	$(PYTHON) -m scripts.app_command "$(COMMAND)" --app "$(APP)" --python "$(PYTHON)"

diff: ## Compare APP's local deployment with the live resources
	$(MAKE) --no-print-directory app-command COMMAND=diff

smoke: ## Check APP's deployed user journey and report evidence gaps
	$(MAKE) --no-print-directory app-command COMMAND=smoke

restore-check: ## Restore APP in isolation and check its data through the standard Ansible path
	$(MAKE) --no-print-directory app-command COMMAND=restore-check

boys-check: ## Check Boys dates, trip behavior, and phone and desktop browsers
	cd apps/boys && npm test

autism-traits-check: ## Check and build the autism traits web application
	cd $(AUTISM_TRAITS_APP) && npm run check

docs-check: ## Build the human documentation with strict validation
	$(PYTHON) -m mkdocs build --strict

docs-serve: ## Preview the human documentation locally
	$(PYTHON) -m mkdocs serve

lint: ## Check Python style, common defects and Ansible files
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint $(ANSIBLE_FILES)

validate: status-page-check prometheus-check ## Validate YAML and rendered manifests
	$(PYTHON) scripts/validate_yaml.py
	for path in $(KUSTOMIZATIONS); do \
		printf 'Rendered %s\n' "$$path"; \
		kubectl kustomize "$$path" >/dev/null; \
	done

prometheus-check: ## Check monitoring rules and backup alert behavior with pinned promtool
	$(PYTHON) scripts/check_prometheus.py

status-page-check:
	$(MAKE) --no-print-directory -f apps/status-page/Makefile check

test: ## Run the focused test suite
	$(PYTEST) -q $(TEST_PATHS) --ignore=apps/immich-offsite-backup/tests/test_backup.py

render: ## Render all managed Kustomize packages
	for path in $(KUSTOMIZATIONS); do \
		printf '\n--- %s ---\n' "$$path"; \
		kubectl kustomize "$$path"; \
	done

go: override APP :=
go: full-check ## Compatibility alias for the complete local check

voice-pe-render:
	$(MAKE) --no-print-directory -f apps/voice-assistant/Makefile voice-pe-render

voice-pe-check:
	$(MAKE) --no-print-directory -f apps/voice-assistant/Makefile voice-pe-check

voice-pe-compile:
	$(MAKE) --no-print-directory -f apps/voice-assistant/Makefile voice-pe-compile

voice-pe-upload: go
	$(MAKE) --no-print-directory -f apps/voice-assistant/Makefile voice-pe-upload

status-page: go
	$(MAKE) --no-print-directory -f apps/status-page/Makefile deploy

status-page-fallback:
	$(MAKE) --no-print-directory -f apps/status-page/Makefile fallback

argo-login: ## Log in using the private Argo recovery Vault
	$(PYTHON) -m scripts.argocd_login

list-apps: ## List Argo CD applications
	kubectl --request-timeout=10s -n argocd get applications

node0: ## SSH to node-0
	ssh ubuntu@$(NODE0)

node1: ## SSH to node-1
	ssh ubuntu@$(NODE1)

node2: ## SSH to node-2
	ssh ubuntu@$(NODE2)

clean: ## Remove generated local output
	rm -rf .build .pytest_cache
	find apps playbooks scripts tests -name node_modules -prune -o -type d -name __pycache__ -prune -exec rm -rf {} +
