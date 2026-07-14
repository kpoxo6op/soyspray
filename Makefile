SHELL := /bin/bash
.DEFAULT_GOAL := help
.SILENT:

VENV := soyspray-venv
PYTHON := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
PYTEST := $(PYTHON) -m pytest
MKDOCS := NO_MKDOCS_2_WARNING=true $(PYTHON) -m mkdocs
INVENTORY := kubespray/inventory/soycluster/hosts.yml
ANSIBLE := source $(VENV)/bin/activate && ansible-playbook -i $(INVENTORY) --become --become-user=root --user ubuntu
DOCS_ADDR ?= 127.0.0.1:8000
KONG_REVISION ?= HEAD

NODE0 := 192.168.20.10
NODE1 := 192.168.20.11
NODE2 := 192.168.20.12

KUSTOMIZATIONS := \
	platform/kong/gateway-api \
	platform/kong/network-policies \
	platform/kong/smoke \
	apis/synthetic-bank \
	kubernetes/banklab/security \
	kubernetes/banklab/tenancy \
	kubernetes/banklab/governance \
	kubernetes/banklab/customer-web \
	kubernetes/banklab/docs-site \
	playbooks/argocd/applications/kong-bank-lab/operator-dashboard

.PHONY: help setup act check lint validate validate-skills test docs docs-serve render status smoke go deploy kong-on kong-off \
	argo-login list-apps node0 node1 node2 master worker1 worker2 worker3 clean

help: ## Show the operator commands
	printf 'Soyspray operator commands\n\n'
	awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Create the venv and install local tooling
	test -d $(VENV) || python3 -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r requirements-dev.txt

act: ## Open a shell in the project venv
	bash -lc 'source $(VENV)/bin/activate && exec bash -i'

check: lint validate test docs ## Run the complete local gate
	printf '\nLocal gate passed.\n'

lint: ## Check Python style and common defects
	$(PYTHON) -m ruff check kubernetes/banklab/customer-web/app scripts tests
	$(PYTHON) -m ruff format --check kubernetes/banklab/customer-web/app scripts tests
	PATH=$(CURDIR)/$(VENV)/bin:$$PATH $(PYTHON) -m ansiblelint \
		roles/apps/kong-bank-lab/tasks/*.yml roles/apps/kong-bank-lab/defaults/*.yml

validate: validate-skills ## Validate YAML, OpenAPI, and rendered manifests
	$(PYTHON) scripts/validate_yaml.py
	$(PYTHON) scripts/validate_openapi_specs.py
	for path in $(KUSTOMIZATIONS); do \
		printf 'Rendered %s\n' "$$path"; \
		kubectl kustomize "$$path" >/dev/null; \
	done

validate-skills: ## Validate reusable project-local Agent Skills
	$(PYTHON) scripts/validate_skills.py

test: ## Run the focused test suite
	$(PYTEST) -q tests

docs: ## Build the operator guide in strict mode
	$(MKDOCS) build --strict --site-dir .build/mkdocs

docs-serve: ## Preview docs with live reload
	$(MKDOCS) serve --dev-addr $(DOCS_ADDR)

render: ## Render all bank-lab Kustomize packages
	for path in $(KUSTOMIZATIONS); do \
		printf '\n--- %s ---\n' "$$path"; \
		kubectl kustomize "$$path"; \
	done

status: ## Show cluster and bank-lab Argo health
	$(PYTHON) scripts/banklab_status.py

smoke: ## Run read-only Kong and customer checks
	$(PYTHON) scripts/banklab_smoke.py

go: check ## Run the deployment preflight
	branch="$$(git branch --show-current)"; \
	test -n "$$branch" && test "$$branch" != main || { echo 'Deploy from a topic branch, not main.' >&2; exit 1; }
	test -z "$$(git status --porcelain)" || { echo 'Commit the working tree before deployment.' >&2; exit 1; }
	git merge-base --is-ancestor HEAD '@{upstream}' || { echo 'Push the current commit before deployment.' >&2; exit 1; }
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --syntax-check --tags kong_bank_lab
	$(PYTHON) scripts/banklab_status.py || printf '\nBank-lab applications need reconciliation.\n'
	printf '\nDeployment preflight passed.\n'

deploy: go ## Apply bank-lab Argo definitions through Ansible
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags kong_bank_lab

kong-on: go ## Start the Kong bank lab
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags kong_bank_lab \
		-e kong_bank_lab_enabled=true -e kong_bank_lab_target_revision=$(KONG_REVISION)

kong-off: go ## Stop the Kong bank lab
	$(ANSIBLE) playbooks/deploy-argocd-apps.yml --tags kong_bank_lab -e kong_bank_lab_enabled=false

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
	find apis kubernetes scripts tests -type d -name __pycache__ -prune -exec rm -rf {} +
