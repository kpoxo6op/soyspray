SHELL := /bin/bash
.DEFAULT_GOAL := help
.SILENT:

VENV := soyspray-venv
PYTHON := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
PYTEST := $(PYTHON) -m pytest
INVENTORY := kubespray/inventory/soycluster/hosts.yml
ANSIBLE := source $(VENV)/bin/activate && ansible-playbook -i $(INVENTORY) --become --become-user=root --user ubuntu
AUTISM_TRAITS_APP := kubernetes/autism-traits/app
AUTISM_TRAITS_ENABLED ?= true
AUTISM_TRAITS_REVISION ?= HEAD
BOYS_ENABLED ?= true
BOYS_REVISION ?= HEAD
VOICE_ASSISTANT_REVISION ?= HEAD
VOICE_ASSISTANT_ENABLED ?= true
VAULTWARDEN_PACKAGE := kubernetes/vaultwarden
VAULTWARDEN_ENABLED ?= true
VAULTWARDEN_REVISION ?= HEAD
LIVE_TV_ENABLED ?= false
LIVE_TV_REVISION ?= HEAD
ifeq ($(LIVE_TV_ENABLED),true)
LIVE_TV_TAGS := authentik,live-tv
LIVE_TV_AUTHENTIK_ARGS := -e authentik_target_revision=$(LIVE_TV_REVISION)
else
LIVE_TV_TAGS := live-tv
LIVE_TV_AUTHENTIK_ARGS :=
endif
VOICE_PE_HOST ?= home-assistant-voice-0a9b95.local
VOICE_PE_CONFIG := .build/voice-pe/gi-voice-pe.yaml
ESPHOME := uvx --from esphome==2025.5.1 esphome

NODE0 := 192.168.20.10
NODE1 := 192.168.20.11
NODE2 := 192.168.20.12

KUSTOMIZATIONS := \
	kubernetes/autism-traits \
	kubernetes/boys \
	$(VAULTWARDEN_PACKAGE) \
	playbooks/argocd/applications/home-automation/voice-assistant \
	playbooks/argocd/applications/media/media-helper \
	playbooks/argocd/applications/media/dispatcharr \
	playbooks/argocd/applications/media/jellyfin

.PHONY: help setup act check boys-check autism-traits-check lint validate validate-skills status-page-check \
	test render go autism-traits boys vaultwarden live-tv voice-assistant voice-pe-render \
	voice-pe-check voice-pe-compile voice-pe-upload status-page status-page-fallback argo-login \
	list-apps node0 node1 node2 master worker1 worker2 worker3 clean

help: ## Show the operator commands
	printf 'Soyspray operator commands\n\n'
	awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create the venv and install local tooling
	test -d $(VENV) || python3 -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r requirements-dev.txt
	cd $(AUTISM_TRAITS_APP) && npm ci
	cd kubernetes/boys && npm ci && npx playwright install chromium

act: ## Open a shell in the project venv
	bash -lc 'source $(VENV)/bin/activate && exec bash -i'

check: lint validate test autism-traits-check boys-check ## Run the complete local gate
	printf '\nLocal gate passed.\n'

boys-check: ## Check Boys save recovery in phone and desktop browsers
	cd kubernetes/boys && npm test

autism-traits-check: ## Check and build the autism traits web application
	cd $(AUTISM_TRAITS_APP) && npm run check

lint: ## Check Python style and common defects
	$(PYTHON) -m ruff check kubernetes/boys/app kubernetes/boys/tests scripts tests
	$(PYTHON) -m ruff format --check kubernetes/boys/app kubernetes/boys/tests scripts tests
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint \
		roles/apps/autism-traits/tasks/*.yml roles/apps/autism-traits/defaults/*.yml \
		roles/apps/boys/tasks/*.yml roles/apps/boys/defaults/*.yml \
		roles/apps/vaultwarden/tasks/*.yml roles/apps/vaultwarden/defaults/*.yml \
		roles/apps/voice-assistant/tasks/*.yml roles/apps/voice-assistant/defaults/*.yml
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint \
		roles/apps/live_tv/tasks/*.yml roles/apps/live_tv/defaults/*.yml

validate: validate-skills status-page-check ## Validate YAML and rendered manifests
	$(PYTHON) scripts/validate_yaml.py
	for path in $(KUSTOMIZATIONS); do \
		printf 'Rendered %s\n' "$$path"; \
		kubectl kustomize "$$path" >/dev/null; \
	done

validate-skills: ## Validate reusable project-local Agent Skills
	$(PYTHON) scripts/validate_skills.py

status-page-check:
	$(PYTHON) scripts/configure_status_page.py --check

test: ## Run the focused test suite
	$(PYTEST) -q tests

render: ## Render all managed Kustomize packages
	for path in $(KUSTOMIZATIONS); do \
		printf '\n--- %s ---\n' "$$path"; \
		kubectl kustomize "$$path"; \
	done

go: check ## Run the deployment preflight
	branch="$$(git branch --show-current)"; \
	test -n "$$branch" && test "$$branch" != main || { echo 'Deploy from a topic branch, not main.' >&2; exit 1; }
	test -z "$$(git status --porcelain)" || { echo 'Commit the working tree before deployment.' >&2; exit 1; }
	git merge-base --is-ancestor HEAD '@{upstream}' || { echo 'Push the current commit before deployment.' >&2; exit 1; }
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --syntax-check --tags authentik,live-tv,autism_traits,boys,vaultwarden,voice_assistant
	printf '\nDeployment preflight passed.\n'

autism-traits: go ## Reconcile or remove the autism traits site
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags autism_traits \
		-e autism_traits_enabled=$(AUTISM_TRAITS_ENABLED) \
		-e autism_traits_target_revision=$(AUTISM_TRAITS_REVISION)

boys: go
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags boys \
		-e boys_enabled=$(BOYS_ENABLED) \
		-e boys_target_revision=$(BOYS_REVISION)

vaultwarden: go
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags vaultwarden \
		-e vaultwarden_enabled=$(VAULTWARDEN_ENABLED) \
		-e vaultwarden_target_revision=$(VAULTWARDEN_REVISION)

live-tv: go
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags $(LIVE_TV_TAGS) $(LIVE_TV_AUTHENTIK_ARGS) \
		-e live_tv_enabled=$(LIVE_TV_ENABLED) \
		-e live_tv_target_revision=$(LIVE_TV_REVISION)

voice-assistant: go
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags voice_assistant \
		-e voice_assistant_target_revision=$(VOICE_ASSISTANT_REVISION) \
		-e voice_assistant_enabled=$(VOICE_ASSISTANT_ENABLED)

voice-pe-render:
	$(PYTHON) scripts/render_gi_voice_pe.py --output $(VOICE_PE_CONFIG)

voice-pe-check: voice-pe-render
	$(ESPHOME) config $(VOICE_PE_CONFIG) >/dev/null

voice-pe-compile: voice-pe-check
	$(ESPHOME) compile $(VOICE_PE_CONFIG)

voice-pe-upload: voice-pe-compile
	$(MAKE) go
	$(ESPHOME) upload $(VOICE_PE_CONFIG) --device $(VOICE_PE_HOST)

status-page: go
	$(PYTHON) scripts/configure_status_page.py

status-page-fallback: status-page-check
	$(PYTHON) scripts/configure_status_page.py --fallback

argo-login: ## Log in to the home Argo CD instance
	argocd login argocd.soyspray.vip --username admin --grpc-web

list-apps: ## List Argo CD applications
	./scripts/argocd-list.sh "$(COLS)"

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
