include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/otv-horoscope/tests
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/otv-horoscope/*.yml
	cd $(ROOT) && kubectl kustomize apps/otv-horoscope >/dev/null
	cd $(ROOT) && kubectl kustomize apps/otv-horoscope/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app otv-horoscope --package apps/otv-horoscope

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/otv-horoscope/bootstrap.yml

.DEFAULT:
	@printf 'unknown: otv-horoscope has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
