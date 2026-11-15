include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff smoke restore-check

check:
	cd $(ROOT)/apps/pearl-guide/app && npm ci
	cd $(ROOT)/apps/assembly-guide/app && npm ci
	cd $(ROOT)/apps/explain/app && npm ci && npm run build && npm test
	cd $(ROOT) && kubectl kustomize apps/explain/manifests >/dev/null
	cd $(ROOT) && kubectl kustomize apps/explain/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app explain --package apps/explain/manifests

smoke:
	@printf 'unknown: open https://explain.soyspray.vip from a tailnet device, then one chapter link per guide.\n'; exit 2

restore-check:
	@printf 'not-required: explain has no persistent state.\n'
