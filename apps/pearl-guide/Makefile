include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff smoke restore-check

check:
	cd $(ROOT)/apps/pearl-guide/app && npm ci && npm run build && npm test
	cd $(ROOT) && kubectl kustomize apps/pearl-guide/manifests >/dev/null
	cd $(ROOT) && kubectl kustomize apps/pearl-guide/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app pearl-guide --package apps/pearl-guide/manifests

smoke:
	@printf 'unknown: open https://pearl.soyspray.vip from a tailnet device and play one chapter.\n'; exit 2

restore-check:
	@printf 'not-required: pearl-guide has no persistent state.\n'
