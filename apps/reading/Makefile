include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff smoke restore-check

check:
	cd $(ROOT)/apps/reading/app && node build.mjs && node --test test/*.test.mjs
	cd $(ROOT) && kubectl kustomize apps/reading/manifests >/dev/null
	cd $(ROOT) && kubectl kustomize apps/reading/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app reading --package apps/reading/manifests

smoke:
	@printf 'unknown: open https://reading.soyspray.vip from a tailnet device, then a book and chapter.\n'; exit 2

restore-check:
	@printf 'not-required: reading has no persistent state.\n'
