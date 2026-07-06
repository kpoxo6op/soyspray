SHELL := /bin/bash
.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
PYTHON ?= $(if $(wildcard soyspray-venv/bin/python),soyspray-venv/bin/python,python3)
PYTEST ?= $(PYTHON) -m pytest

K8S_USER        := ubuntu
NODE0           := 192.168.20.10
NODE1           := 192.168.20.11
NODE2           := 192.168.20.12
WORKER_NODE1    := $(NODE0)
WORKER_NODE2    := $(NODE1)
WORKER_NODE3    := $(NODE2)
MASTER_NODE     := $(NODE0)

# Adjust ArgoCD version if needed
ARGOCD_VERSION  := v2.12.4
GATEWAY_API_CRDS := platform/kong/gateway-api/crds/standard-install.yaml
GATEWAY_API_REQUIRED_CRDS := gatewayclasses.gateway.networking.k8s.io gateways.gateway.networking.k8s.io httproutes.gateway.networking.k8s.io

master:
	ssh $(K8S_USER)@$(MASTER_NODE)

worker1:
	ssh $(K8S_USER)@$(WORKER_NODE1)

worker2:
	ssh $(K8S_USER)@$(WORKER_NODE2)

worker3:
	ssh $(K8S_USER)@$(WORKER_NODE3)

argo:
	argocd login argocd.soyspray.vip --username admin --password password --grpc-web

VENV_NAME       := soyspray-venv

venv:
	@test -d $(VENV_NAME) || python3 -m venv $(VENV_NAME)
	@$(VENV_NAME)/bin/python -m pip install --upgrade pip wheel

act:
	@bash -lc 'source $(VENV_NAME)/bin/activate && exec bash -i'

ans:
	@echo "ansible-playbook -i kubespray/inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu playbooks/deploy-argocd-apps.yml --tags TAG"


install:
	@if [ ! -w /usr/local/bin ]; then \
		echo "Error: This target requires sudo privileges. Please run 'sudo make install'"; \
		exit 1; \
	fi

	@if ! dpkg -l | grep -q "^ii  python3-pip " || ! dpkg -l | grep -q "^ii  python3-venv "; then \
		echo "Installing Python packages..."; \
		sudo apt-get update && sudo apt-get install python3-pip python3-venv -y; \
	else \
		echo "Python packages already installed: python $$(python3 --version), pip $$(pip3 --version | cut -d' ' -f2)"; \
	fi

	@if command -v kubectl >/dev/null 2>&1; then \
		echo "kubectl already installed. Version info:"; \
		kubectl version --client 2>&1 || true; \
	else \
		echo "Installing kubectl..."; \
		curl -LO "https://dl.k8s.io/release/$$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"; \
		sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl; \
		rm -f kubectl; \
	fi

	@if command -v argocd >/dev/null 2>&1 && argocd version --client >/dev/null 2>&1; then \
		echo "ArgoCD CLI already installed and working:"; \
		argocd version --client | head -1; \
	else \
		echo "Installing ArgoCD CLI $(ARGOCD_VERSION)..."; \
		sudo curl -L -o /usr/local/bin/argocd \
			https://github.com/argoproj/argo-cd/releases/download/$(ARGOCD_VERSION)/argocd-linux-amd64; \
		sudo chmod +x /usr/local/bin/argocd; \
	fi

go: argo act ans

alist:
	@./scripts/argocd-list.sh "$(COLS)"

validate:
	@$(PYTHON) scripts/validate_repo.py

validate-yaml:
	@$(PYTHON) scripts/validate_yaml.py

validate-kustomize:
	@$(PYTHON) scripts/render_prereqs.py >/dev/null

validate-prereqs:
	@$(PYTHON) scripts/validate_prereqs.py

validate-kong-baseline:
	@$(PYTHON) scripts/validate_kong_baseline.py

render-prereqs:
	@$(PYTHON) scripts/render_prereqs.py

render-kong-baseline:
	@$(PYTHON) scripts/render_kong_baseline.py >/dev/null

validate-synthetic-apis:
	@$(PYTHON) scripts/validate_synthetic_bank_apis.py

validate-synthetic-api-runtime-gate:
	@$(PYTHON) scripts/validate_synthetic_api_runtime_gate.py

openapi-lint:
	@$(PYTHON) scripts/validate_openapi_specs.py

render-synthetic-apis:
	@$(PYTHON) scripts/render_synthetic_apis.py >/dev/null

synthetic-api-static-test:
	@$(PYTEST) tests/unit/test_goal_003_synthetic_api_structure.py tests/unit/test_goal_003_route_matrix.py tests/unit/test_goal_003_runtime_boundary.py tests/policy/test_goal_003_exposure_policy.py tests/policy/test_goal_003_no_forbidden_kong_resources.py

synthetic-api-contract-test:
	@$(PYTEST) tests/unit/test_goal_003_openapi_specs.py tests/unit/test_goal_003_api_ownership_metadata.py tests/unit/test_goal_003_synthetic_clients.py tests/policy/test_goal_003_no_auth_until_goal004.py tests/policy/test_goal_003_no_secrets.py tests/policy/test_goal_003_network_policy.py

synthetic-api-smoke-plan:
	@$(PYTHON) scripts/generate_synthetic_api_smoke_plan.py

kong-static-test:
	@$(PYTEST) tests/unit/test_goal_002_kong_structure.py tests/unit/test_goal_002_kong_versions.py tests/unit/test_goal_002_no_enterprise_features.py tests/unit/test_goal_002_admin_api_private.py

kong-admin-exposure-test:
	@$(PYTHON) scripts/validate_kong_baseline.py --admin-only

runtime-preflight-local:
	@$(PYTHON) scripts/validate_runtime_preflight.py

kong-apply-plan:
	@platform/kong/scripts/generate-kong-apply-plan.sh

cluster-readonly-preflight:
	@platform/kong/scripts/cluster-readonly-preflight.sh

kong-readonly-preflight:
	@platform/kong/scripts/kong-readonly-preflight.sh

mutation-guard-test:
	@set -euo pipefail; \
	if platform/kong/scripts/require-cluster-mutation-permission.sh >/tmp/banklab-mutation-guard-test.out 2>&1; then \
		echo "Mutation guard unexpectedly passed without permission."; \
		cat /tmp/banklab-mutation-guard-test.out; \
		exit 1; \
	fi; \
	if BANKLAB_ALLOW_CLUSTER_MUTATION=true platform/kong/scripts/require-cluster-mutation-permission.sh >/tmp/banklab-mutation-guard-test.out 2>&1; then \
		echo "Mutation guard unexpectedly passed without target context."; \
		cat /tmp/banklab-mutation-guard-test.out; \
		exit 1; \
	fi; \
	echo "Mutation guard fails closed without explicit permission."

validate-cluster-apply-gate:
	@$(PYTHON) scripts/validate_cluster_apply_gate.py

goal002-runtime-ready:
	@platform/kong/scripts/verify-goal002-runtime-ready.sh

test:
	@$(PYTEST) tests/unit

policy-test:
	@$(PYTEST) tests/policy

docs:
	@$(PYTHON) -m mkdocs build --strict --site-dir .build/mkdocs

evidence:
	@$(PYTHON) scripts/generate_evidence_report.py

evidence-goal-001:
	@$(PYTHON) scripts/generate_evidence_report.py --goal goal-001-platform-prereqs

evidence-goal-002:
	@$(PYTHON) scripts/generate_evidence_report.py --goal goal-002-kong-oss-baseline

evidence-goal-003:
	@$(PYTHON) scripts/generate_evidence_report.py --goal goal-003-synthetic-bank-apis

evidence-gate-003-synthetic-api-runtime:
	@$(PYTHON) scripts/generate_evidence_report.py --goal gate-003-synthetic-api-runtime-apply-and-smoke

evidence-gate-002-runtime-preflight:
	@$(PYTHON) scripts/generate_evidence_report.py --goal gate-002-runtime-preflight

evidence-gate-002-cluster-apply-and-smoke:
	@$(PYTHON) scripts/generate_evidence_report.py --goal gate-002-cluster-apply-and-smoke

cluster-smoke:
	@$(PYTHON) scripts/cluster_smoke.py

cluster-prereq-smoke:
	@platform/bootstrap/check-cluster-prereqs.sh

kong-cluster-smoke:
	@$(PYTHON) scripts/check_kong_cluster.py

kong-route-smoke:
	@platform/kong/scripts/route-smoke.sh

synthetic-api-install-dry-run:
	@$(PYTHON) scripts/render_synthetic_apis.py | kubectl apply --dry-run=server -f -

synthetic-api-apply:
	@platform/kong/scripts/require-cluster-mutation-permission.sh
	@platform/kong/synthetic-apis/scripts/synthetic-api-apply.sh

synthetic-api-smoke:
	@platform/kong/synthetic-apis/scripts/synthetic-api-smoke.sh

synthetic-api-negative-test:
	@platform/kong/synthetic-apis/scripts/synthetic-api-negative-test.sh

synthetic-api-rollback:
	@platform/kong/scripts/require-cluster-mutation-permission.sh
	@platform/kong/synthetic-apis/scripts/synthetic-api-rollback.sh

synthetic-api-runtime-ready:
	@platform/kong/synthetic-apis/scripts/verify-synthetic-api-runtime-ready.sh

goal003-runtime-ready:
	@platform/kong/synthetic-apis/scripts/verify-goal003-runtime-ready.sh

kong-install-dry-run:
	@kubectl apply --dry-run=server -f $(GATEWAY_API_CRDS)
	@kubectl apply --dry-run=server -f platform/kong/namespace.yaml
	@kubectl apply --dry-run=server -f platform/kong/smoke/namespace.yaml
	@if kubectl get crd $(GATEWAY_API_REQUIRED_CRDS) >/dev/null 2>&1 && \
		kubectl get namespace platform-kong platform-kong-smoke >/dev/null 2>&1; then \
		$(PYTHON) scripts/render_kong_baseline.py | kubectl apply --dry-run=server -f -; \
	else \
		$(PYTHON) scripts/render_kong_baseline.py | kubectl apply --dry-run=client -f - >/dev/null; \
		echo "Full server dry-run requires Gateway API CRDs and target namespaces to already exist; client dry-run passed for rendered baseline."; \
	fi

kong-apply:
	@platform/kong/scripts/require-cluster-mutation-permission.sh
	@kubectl apply -f $(GATEWAY_API_CRDS)
	@kubectl wait --for=condition=Established --timeout=90s crd/$(word 1,$(GATEWAY_API_REQUIRED_CRDS)) crd/$(word 2,$(GATEWAY_API_REQUIRED_CRDS)) crd/$(word 3,$(GATEWAY_API_REQUIRED_CRDS))
	@kubectl apply -f platform/kong/namespace.yaml
	@kubectl apply -f platform/kong/smoke/namespace.yaml
	@$(PYTHON) scripts/render_kong_baseline.py | kubectl apply -f -

kong-rollback:
	@platform/kong/scripts/require-cluster-mutation-permission.sh
	@$(PYTHON) scripts/render_kong_baseline.py | kubectl delete --ignore-not-found=true -f -

clean:
	@rm -rf .build .pytest_cache
	@find . -path './.git' -prune -o -path './soyspray-venv' -prune -o -type d -name __pycache__ -prune -exec rm -rf {} +

help:
	@echo "Available commands:"
	@echo "  make validate    - Run local repository foundation checks"
	@echo "  make validate-yaml - Parse local YAML files"
	@echo "  make validate-kustomize - Render prerequisite kustomizations locally"
	@echo "  make validate-prereqs - Run local goal-001 prerequisite checks"
	@echo "  make validate-kong-baseline - Run local goal-002 Kong checks"
	@echo "  make validate-synthetic-apis - Run local goal-003 synthetic API checks"
	@echo "  make validate-synthetic-api-runtime-gate - Run local gate-003 runtime checks"
	@echo "  make runtime-preflight-local - Run local gate-002 runtime preflight checks"
	@echo "  make render-prereqs - Print rendered prerequisite manifests"
	@echo "  make render-kong-baseline - Render Kong baseline manifests locally"
	@echo "  make render-synthetic-apis - Render goal-003 synthetic API manifests locally"
	@echo "  make openapi-lint - Validate goal-003 OpenAPI specs locally"
	@echo "  make kong-static-test - Run goal-002 unit tests"
	@echo "  make kong-admin-exposure-test - Check Admin API exposure statically"
	@echo "  make synthetic-api-static-test - Run goal-003 static structure tests"
	@echo "  make synthetic-api-contract-test - Run goal-003 OpenAPI and metadata tests"
	@echo "  make synthetic-api-smoke-plan - Generate goal-003 runtime smoke plan"
	@echo "  make kong-apply-plan - Generate Kong runtime apply plan locally"
	@echo "  make mutation-guard-test - Prove cluster mutation guardrails fail closed"
	@echo "  make validate-cluster-apply-gate - Validate cluster-apply gate package locally"
	@echo "  make goal002-runtime-ready - Verify runtime evidence is approved"
	@echo "  make test        - Run local unit tests"
	@echo "  make policy-test - Run local placeholder policy tests"
	@echo "  make docs        - Build MkDocs documentation locally"
	@echo "  make evidence    - Refresh goal-000 evidence report"
	@echo "  make evidence-goal-001 - Refresh goal-001 evidence report"
	@echo "  make evidence-goal-002 - Refresh goal-002 evidence report"
	@echo "  make evidence-goal-003 - Refresh goal-003 evidence report"
	@echo "  make evidence-gate-003-synthetic-api-runtime - Refresh gate-003 runtime evidence"
	@echo "  make evidence-gate-002-runtime-preflight - Refresh runtime preflight evidence"
	@echo "  make evidence-gate-002-cluster-apply-and-smoke - Refresh cluster apply gate evidence"
	@echo "  make cluster-smoke - Run explicit cluster connectivity checks"
	@echo "  make cluster-prereq-smoke - Check applied prerequisite resources"
	@echo "  make cluster-readonly-preflight - Run optional read-only cluster preflight"
	@echo "  make kong-readonly-preflight - Run optional read-only Kong preflight"
	@echo "  make kong-cluster-smoke - Run read-only Kong cluster checks"
	@echo "  make kong-route-smoke - Run Kong smoke route checks"
	@echo "  make kong-install-dry-run - Dry-run Kong baseline apply"
	@echo "  make kong-apply  - Apply Kong baseline with BANKLAB mutation guard variables"
	@echo "  make kong-rollback - Roll back Kong baseline with BANKLAB mutation guard variables"
	@echo "  make synthetic-api-install-dry-run - Server dry-run goal-003 synthetic APIs"
	@echo "  make synthetic-api-apply - Apply goal-003 synthetic APIs with mutation guard variables"
	@echo "  make synthetic-api-smoke - Run read-only goal-003 route smoke checks"
	@echo "  make synthetic-api-negative-test - Run read-only goal-003 negative route checks"
	@echo "  make synthetic-api-rollback - Roll back goal-003 synthetic APIs with mutation guard variables"
	@echo "  make synthetic-api-runtime-ready - Verify runtime evidence is approved"
	@echo "  make goal003-runtime-ready - Verify goal-003 runtime evidence is approved"
	@echo "  make clean       - Remove generated local artifacts"
	@echo "  make master      - SSH into master node ($(MASTER_NODE))"
	@echo "  make worker1     - SSH into worker node 1 ($(WORKER_NODE1))"
	@echo "  make worker2     - SSH into worker node 2 ($(WORKER_NODE2))"
	@echo "  make worker3     - SSH into worker node 3 ($(WORKER_NODE3))"
	@echo "  make venv        - Create Python virtual environment"
	@echo "  make install     - Install tools (requires sudo: run 'sudo make install')"
	@echo "  make argo        - Login to ArgoCD (argocd.soyspray.vip)"
	@echo "  make act         - Start interactive shell with venv activated"
	@echo "  make ans         - Show Ansible command starter"
	@echo "  make go          - Run argo, act, and ans commands in sequence"
	@echo "  make alist       - List ArgoCD apps with scripts/argocd-list.sh"
.PHONY: master worker1 worker2 worker3 help venv act argo install go alist validate validate-yaml validate-kustomize validate-prereqs validate-kong-baseline validate-synthetic-apis validate-synthetic-api-runtime-gate openapi-lint runtime-preflight-local render-prereqs render-kong-baseline render-synthetic-apis kong-static-test kong-admin-exposure-test synthetic-api-static-test synthetic-api-contract-test synthetic-api-smoke-plan kong-apply-plan cluster-readonly-preflight kong-readonly-preflight mutation-guard-test validate-cluster-apply-gate goal002-runtime-ready synthetic-api-runtime-ready goal003-runtime-ready test policy-test docs evidence evidence-goal-001 evidence-goal-002 evidence-goal-003 evidence-gate-002-runtime-preflight evidence-gate-002-cluster-apply-and-smoke evidence-gate-003-synthetic-api-runtime cluster-smoke cluster-prereq-smoke kong-cluster-smoke kong-route-smoke synthetic-api-install-dry-run synthetic-api-apply synthetic-api-smoke synthetic-api-negative-test synthetic-api-rollback kong-install-dry-run kong-apply kong-rollback clean
