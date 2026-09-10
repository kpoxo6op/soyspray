SHELL := /bin/bash
.DEFAULT_GOAL := help
.SILENT:

VENV := soyspray-venv
PYTHON := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
PYTEST := $(PYTHON) -m pytest
INVENTORY := kubespray/inventory/soycluster/hosts.yml
ANSIBLE := source $(VENV)/bin/activate && ansible-playbook -i $(INVENTORY) --become --become-user=root --user ubuntu
AUTISM_TRAITS_APP := apps/autism-traits/app
VAULTWARDEN_PACKAGE := apps/vaultwarden/manifests
OBSIDIAN_PACKAGE := apps/obsidian-livesync/manifests
FORMAT ?= text

NODE0 := 192.168.20.10
NODE1 := 192.168.20.11
NODE2 := 192.168.20.12

KUSTOMIZATIONS := \
	argocd \
	apps/autism-traits/manifests \
	apps/boys/manifests \
	apps/domain-health \
	apps/immich/database/production \
	apps/immich/database/alias \
	$(VAULTWARDEN_PACKAGE) \
	$(OBSIDIAN_PACKAGE) \
	apps/voice-assistant/manifests \
	apps/media-helper \
	apps/dispatcharr/manifests \
	apps/jellyfin/manifests

.PHONY: help setup act check shared-test shared-check full-check app-command diff smoke restore-check boys-check autism-traits-check docs-check docs-serve lint validate validate-skills status-page-check prometheus-check \
	test render go voice-pe-render voice-pe-check voice-pe-compile voice-pe-upload status-page status-page-fallback argo-login \
	apps status backup-status list-apps node0 node1 node2 master worker1 worker2 worker3 clean

help: ## Show the operator commands
	printf 'Soyspray operator commands\n\n'
	awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

apps: ## List Applications and their declared owners (FORMAT=json is supported)
	$(PYTHON) -m scripts.app_status apps --format "$(FORMAT)"

status: ## Read desired/running revisions and evidence gaps for APP (FORMAT=json is supported)
	$(PYTHON) -m scripts.app_status status --app "$(APP)" --format "$(FORMAT)"

backup-status: ## Read backup coverage, age, failures, and missing recovery evidence
	$(PYTHON) -m scripts.backup_status --format "$(FORMAT)"

setup: ## Create the venv and install local tooling
	test -d $(VENV) || python3 -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r requirements-dev.txt
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
	$(VENV)/bin/mkdocs build --strict

docs-serve: ## Preview the human documentation locally
	$(VENV)/bin/mkdocs serve

lint: ## Check Python style and common defects
	$(PYTHON) -m ruff check apps/cluster-diagnosis apps/boys/app apps/boys/tests apps/autism-traits/*.py apps/autism-traits/tests apps/boys/*.py apps/external-dns/tests apps/domain-health/tests apps/vaultwarden/tests apps/obsidian-livesync/tests apps/obsidian-livesync/*.py apps/headlamp/tests apps/media-helper/tests apps/cert-manager-config/tests apps/cert-manager-config/*.py apps/media-helper/app apps/media-helper/*.py apps/vaultwarden/*.py apps/domain-health/app apps/domain-health/*.py apps/immich apps/prometheus/tests scripts tests playbooks/operations/nodes/cleanup-kubernetes-network.py playbooks/operations/nodes/run-node2-rebuild.py
	$(PYTHON) -m ruff format --check apps/cluster-diagnosis apps/boys/app apps/boys/tests apps/autism-traits/*.py apps/autism-traits/tests apps/boys/*.py apps/external-dns/tests apps/domain-health/tests apps/vaultwarden/tests apps/obsidian-livesync/tests apps/obsidian-livesync/*.py apps/headlamp/tests apps/media-helper/tests apps/cert-manager-config/tests apps/cert-manager-config/*.py apps/media-helper/app apps/media-helper/*.py apps/vaultwarden/*.py apps/domain-health/app apps/domain-health/*.py apps/immich apps/prometheus/tests scripts tests playbooks/operations/nodes/cleanup-kubernetes-network.py playbooks/operations/nodes/run-node2-rebuild.py
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint \
		apps/autism-traits/bootstrap.yml apps/boys/bootstrap*.yml apps/external-dns/*.yml apps/domain-health/*.yml apps/vaultwarden/*.yml apps/obsidian-livesync/*.yml apps/cert-manager-config/*.yml apps/prometheus/*.yml argocd/bootstrap/repositories.yml apps/authentik/bootstrap/tasks/certificate.yml \
		apps/voice-assistant/bootstrap/tasks/*.yml apps/voice-assistant/bootstrap/defaults/*.yml
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint \
		apps/live-tv/bootstrap/tasks/*.yml apps/live-tv/bootstrap/defaults/*.yml \
		playbooks/operations/boys/*.yml
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint playbooks/bootstrap-apps.yml \
		playbooks/bootstrap-app-inputs.yml \
		playbooks/operations/runtime/install.yml \
		playbooks/operations/nodes/snapshot-etcd.yml \
		playbooks/operations/nodes/preflight-node2-removal.yml \
		playbooks/operations/nodes/clean-node2-baseline.yml \
		playbooks/operations/storage/prepare-existing-longhorn-storage.yml \
		playbooks/operations/storage/protect-loki-before-node2.yml \
		playbooks/operations/storage/evacuate-node2.yml \
		playbooks/operations/storage/restore-node2-replicas.yml \
		playbooks/operations/recovery/restore-volume.yml playbooks/operations/recovery/cleanup-restore.yml playbooks/operations/recovery/start-restored-app.yml \
		playbooks/operations/recovery/configure-longhorn.yml playbooks/operations/recovery/backup-daily-now.yml

validate: validate-skills status-page-check prometheus-check ## Validate YAML and rendered manifests
	$(PYTHON) scripts/validate_yaml.py
	for path in $(KUSTOMIZATIONS); do \
		printf 'Rendered %s\n' "$$path"; \
		kubectl kustomize "$$path" >/dev/null; \
	done

validate-skills: ## Validate reusable project-local Agent Skills
	$(PYTHON) scripts/validate_skills.py

prometheus-check: ## Check monitoring rules and backup alert behavior with pinned promtool
	$(PYTHON) scripts/check_prometheus.py

status-page-check:
	$(MAKE) --no-print-directory -f apps/status-page/Makefile check

test: ## Run the focused test suite
	$(PYTEST) -q tests apps/cluster-diagnosis/tests apps/immich/tests apps/immich-offsite-backup/tests --ignore=apps/immich-offsite-backup/tests/test_backup.py apps/autism-traits/tests apps/boys/tests apps/external-dns/tests apps/domain-health/tests apps/vaultwarden/tests apps/obsidian-livesync/tests apps/headlamp/tests apps/media-helper/tests apps/cert-manager-config/tests apps/prometheus/tests

render: ## Render all managed Kustomize packages
	for path in $(KUSTOMIZATIONS); do \
		printf '\n--- %s ---\n' "$$path"; \
		kubectl kustomize "$$path"; \
	done

go: override APP :=
go: full-check ## Run every local check before a pull request or merge

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

argo-login: ## Log in to the home Argo CD instance
	argocd login argocd.soyspray.vip --username admin --grpc-web

list-apps: ## List Argo CD applications
	kubectl --request-timeout=10s -n argocd get applications

node0: ## SSH to node-0
	ssh ubuntu@$(NODE0)

node1: ## SSH to node-1
	ssh ubuntu@$(NODE1)

node2: ## SSH to node-2
	ssh ubuntu@$(NODE2)

# Compatibility aliases for the older cluster workflow.
master worker1: node0
worker2: node1
worker3: node2

clean: ## Remove generated local output
	rm -rf .build .pytest_cache
	find kubernetes scripts tests -type d -name __pycache__ -prune -exec rm -rf {} +
