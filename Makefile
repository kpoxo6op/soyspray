SHELL := /bin/bash
.DEFAULT_GOAL := help
.SILENT:

VENV := soyspray-venv
PYTHON := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
PYTEST := $(PYTHON) -m pytest
INVENTORY := kubespray/inventory/soycluster/hosts.yml
ANSIBLE := source $(VENV)/bin/activate && ansible-playbook -i $(INVENTORY) --become --become-user=root --user ubuntu
AUTISM_TRAITS_APP := apps/autism-traits/app
AUTISM_TRAITS_ENABLED ?= true
AUTISM_TRAITS_REVISION ?= HEAD
BOYS_ENABLED ?= true
BOYS_REVISION ?= HEAD
EXTERNAL_DNS_REVISION ?= HEAD
DOMAIN_HEALTH_REVISION ?= HEAD
VOICE_ASSISTANT_REVISION ?= HEAD
VOICE_ASSISTANT_ENABLED ?= true
VAULTWARDEN_PACKAGE := apps/vaultwarden/manifests
OBSIDIAN_PACKAGE := apps/obsidian-livesync/manifests
VAULTWARDEN_ENABLED ?= true
VAULTWARDEN_REVISION ?= HEAD
HEADLAMP_REVISION ?= HEAD
MEDIA_HELPER_REVISION ?= HEAD
CERT_MANAGER_CONFIG_REVISION ?= HEAD
OBSIDIAN_REVISION ?= HEAD
OBSIDIAN_ENABLED ?= true
FORMAT ?= text
REVISION ?= HEAD
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
	argocd \
	apps/autism-traits/manifests \
	apps/boys/manifests \
	apps/domain-health \
	$(VAULTWARDEN_PACKAGE) \
	$(OBSIDIAN_PACKAGE) \
	playbooks/argocd/applications/home-automation/voice-assistant \
	apps/media-helper \
	playbooks/argocd/applications/media/dispatcharr \
	playbooks/argocd/applications/media/jellyfin

.PHONY: help setup act check full-check app-command diff deploy smoke restore-check boys-check autism-traits-check lint validate validate-skills status-page-check prometheus-check \
	test render go autism-traits boys vaultwarden obsidian-livesync headlamp live-tv voice-assistant voice-pe-render \
	voice-pe-check voice-pe-compile voice-pe-upload media-helper cert-manager-config status-page status-page-fallback argo-login \
	apps status backup-status external-dns domain-health list-apps node0 node1 node2 master worker1 worker2 worker3 clean

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

full-check: lint validate test autism-traits-check boys-check ## Run the full repository gate explicitly
	printf '\nLocal gate passed.\n'

app-command:
	$(PYTHON) -m scripts.app_command "$(COMMAND)" --app "$(APP)" --python "$(PYTHON)" --revision "$(REVISION)"

diff: ## Compare APP's local deployment with the live resources
	$(MAKE) --no-print-directory app-command COMMAND=diff

deploy: ## Run APP's standard Ansible path (REVISION=HEAD by default)
	$(MAKE) --no-print-directory app-command COMMAND=deploy

smoke: ## Check APP's deployed user journey and report evidence gaps
	$(MAKE) --no-print-directory app-command COMMAND=smoke

restore-check: ## Restore APP in isolation and check its data through the standard Ansible path
	$(MAKE) --no-print-directory app-command COMMAND=restore-check

boys-check: ## Check Boys dates, trip behavior, and phone and desktop browsers
	cd apps/boys && npm test

autism-traits-check: ## Check and build the autism traits web application
	cd $(AUTISM_TRAITS_APP) && npm run check

lint: ## Check Python style and common defects
	$(PYTHON) -m ruff check apps/boys/app apps/boys/tests apps/autism-traits/*.py apps/autism-traits/tests apps/boys/*.py apps/external-dns/tests apps/domain-health/tests apps/vaultwarden/tests apps/obsidian-livesync/tests apps/obsidian-livesync/*.py apps/headlamp/tests apps/media-helper/tests apps/cert-manager-config/tests apps/media-helper/app apps/media-helper/*.py apps/vaultwarden/*.py apps/domain-health/app apps/domain-health/*.py apps/immich scripts tests
	$(PYTHON) -m ruff format --check apps/boys/app apps/boys/tests apps/autism-traits/*.py apps/autism-traits/tests apps/boys/*.py apps/external-dns/tests apps/domain-health/tests apps/vaultwarden/tests apps/obsidian-livesync/tests apps/obsidian-livesync/*.py apps/headlamp/tests apps/media-helper/tests apps/cert-manager-config/tests apps/media-helper/app apps/media-helper/*.py apps/vaultwarden/*.py apps/domain-health/app apps/domain-health/*.py apps/immich scripts tests
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint \
		apps/autism-traits/bootstrap.yml apps/boys/bootstrap*.yml apps/external-dns/*.yml apps/domain-health/*.yml apps/vaultwarden/*.yml apps/obsidian-livesync/*.yml apps/cert-manager-config/*.yml argocd/bootstrap/repositories.yml roles/apps/cert-manager/tasks/main.yml roles/apps/authentik/tasks/certificate.yml \
		roles/apps/voice-assistant/tasks/*.yml roles/apps/voice-assistant/defaults/*.yml
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint \
		roles/apps/live_tv/tasks/*.yml roles/apps/live_tv/defaults/*.yml \
		playbooks/operations/boys/*.yml
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint playbooks/bootstrap-apps.yml \
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
	$(PYTHON) scripts/configure_status_page.py --check

test: ## Run the focused test suite
	$(PYTEST) -q tests apps/autism-traits/tests apps/boys/tests apps/external-dns/tests apps/domain-health/tests apps/vaultwarden/tests apps/obsidian-livesync/tests apps/headlamp/tests apps/media-helper/tests apps/cert-manager-config/tests

render: ## Render all managed Kustomize packages
	for path in $(KUSTOMIZATIONS); do \
		printf '\n--- %s ---\n' "$$path"; \
		kubectl kustomize "$$path"; \
	done

go: override APP :=
go: check ## Run the full gate and deployment preflight even when APP is set
	branch="$$(git branch --show-current)"; \
	test -n "$$branch" && test "$$branch" != main || { echo 'Deploy from a topic branch, not main.' >&2; exit 1; }
	test -z "$$(git status --porcelain)" || { echo 'Commit the working tree before deployment.' >&2; exit 1; }
	git merge-base --is-ancestor HEAD '@{upstream}' || { echo 'Push the current commit before deployment.' >&2; exit 1; }
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --syntax-check --tags authentik,live-tv,autism_traits,boys,vaultwarden,voice_assistant
	printf '\nDeployment preflight passed.\n'

autism-traits: go ## Reconcile the autism traits site through the native Argo root
	test "$(AUTISM_TRAITS_ENABLED)" = true || { echo 'Retire an adopted app through an explicit operation; this command only deploys.' >&2; exit 1; }
	$(ANSIBLE) apps/autism-traits/bootstrap.yml
	$(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(AUTISM_TRAITS_REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(AUTISM_TRAITS_REVISION)),,autism-traits)

boys: go ## Reconcile Boys through the native Argo root
	test "$(BOYS_ENABLED)" = true || { echo 'Retire an adopted app through an explicit operation; this command only deploys.' >&2; exit 1; }
	$(ANSIBLE) apps/boys/bootstrap.yml
	$(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(BOYS_REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(BOYS_REVISION)),,boys)

external-dns: go ## Reconcile ExternalDNS through the native Argo root
	$(ANSIBLE) apps/external-dns/bootstrap.yml
	$(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(EXTERNAL_DNS_REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(EXTERNAL_DNS_REVISION)),,external-dns)

domain-health: go ## Reconcile domain checks through the native Argo root
	$(ANSIBLE) apps/domain-health/bootstrap.yml
	$(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(DOMAIN_HEALTH_REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(DOMAIN_HEALTH_REVISION)),,domain-health)

media-helper: go ## Reconcile the media helper through the native Argo root
	$(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(MEDIA_HELPER_REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(MEDIA_HELPER_REVISION)),,media-helper)

cert-manager-config: go ## Reconcile the certificate configuration through the native Argo root
	$(ANSIBLE) apps/cert-manager-config/bootstrap.yml
	$(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(CERT_MANAGER_CONFIG_REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(CERT_MANAGER_CONFIG_REVISION)),,cert-manager-config)

headlamp: go ## Reconcile Headlamp through the native Argo root
	$(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(HEADLAMP_REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(HEADLAMP_REVISION)),,headlamp)

obsidian-livesync: go ## Reconcile Obsidian through the native Argo root
	test "$(OBSIDIAN_ENABLED)" = true || { echo 'Retire an adopted app through an explicit operation; this command only deploys.' >&2; exit 1; }
	$(ANSIBLE) apps/obsidian-livesync/bootstrap.yml
	$(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(OBSIDIAN_REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(OBSIDIAN_REVISION)),,obsidian-livesync)

vaultwarden: go ## Reconcile Vaultwarden through the native Argo root
	test "$(VAULTWARDEN_ENABLED)" = true || { echo 'Retire an adopted app through an explicit operation; this command only deploys.' >&2; exit 1; }
	$(ANSIBLE) apps/vaultwarden/bootstrap.yml
	$(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(VAULTWARDEN_REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(VAULTWARDEN_REVISION)),,vaultwarden)

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
