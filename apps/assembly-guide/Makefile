include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff smoke restore-check

check:
	cd $(ROOT)/apps/assembly-guide/app && npm ci && npm run build && npm test
	cd $(ROOT) && kubectl kustomize apps/assembly-guide/manifests >/dev/null
	cd $(ROOT) && kubectl kustomize apps/assembly-guide/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app assembly-guide --package apps/assembly-guide/manifests

smoke:
	@printf 'unknown: check the private ingress, page, assets, and 3D controls from a tailnet device.\n'; exit 2

restore-check:
	@printf 'not-required: assembly-guide has no persistent state.\n'
