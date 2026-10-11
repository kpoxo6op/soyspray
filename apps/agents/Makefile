include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff smoke restore-check

check:
	cd $(ROOT)/apps/agents/app && npm ci && npm run build && npm test
	cd $(ROOT)/apps/agents && $(PYTHON) -m unittest discover -s tests -v
	cd $(ROOT) && $(PYTHON) -m ruff check apps/agents
	cd $(ROOT) && $(PYTHON) -m ruff format --check apps/agents
	cd $(ROOT) && kubectl kustomize apps/agents/storage >/dev/null
	cd $(ROOT) && kubectl kustomize apps/agents/provision >/dev/null
	cd $(ROOT) && kubectl kustomize apps/agents/argocd-provision >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app agents --package apps/agents/provision

smoke:
	@printf 'unknown: inspect replay, captions, range seeking and controls from a tailnet device.\n'; exit 2

restore-check:
	@printf 'unknown: encrypted backup, independent download, full hash restore and restore-test intake need live evidence.\n'; exit 2
