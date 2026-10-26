include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap smoke restore-check

check:
	cd $(ROOT)/apps/sewing-guide/app && npm ci && npm run build && npm test
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/sewing-guide/tests
	cd $(ROOT) && kubectl kustomize apps/sewing-guide/manifests >/dev/null
	cd $(ROOT) && kubectl kustomize apps/sewing-guide/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app sewing-guide --package apps/sewing-guide/manifests

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/sewing-guide/bootstrap.yml

smoke:
	kubectl -n sewing-guide rollout status deployment/sewing-guide --timeout=120s
	$(PYTHON) apps/sewing-guide/test-image.py --url https://sewing.soyspray.vip

restore-check:
	@printf 'not-required: sewing-guide has no persistent state.\n'
