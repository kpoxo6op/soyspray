include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
.PHONY: check diff bootstrap restore-check smoke

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/prometheus/tests tests/test_argocd_root.py \
		tests/test_authentik_dashboard.py tests/test_longhorn_metric_filter.py tests/test_sso.py \
		tests/test_sso_legacy_proxy.py
	cd $(ROOT) && $(PYTHON) scripts/check_prometheus.py
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/prometheus/*.yml
	cd $(ROOT) && kubectl kustomize apps/prometheus/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app kube-prometheus-stack --package apps/prometheus

bootstrap:
	cd $(ROOT) && $(ANSIBLE) apps/prometheus/bootstrap.yml

restore-check:
	@printf '%s\n' 'unknown: Prometheus has no maintained isolated TSDB restore check yet.' >&2
	@exit 2

smoke:
	@printf '%s\n' 'unknown: Prometheus has no maintained deployed access check yet.' >&2
	@exit 2

.DEFAULT:
	@printf 'unknown: prometheus has no maintained %s operation yet.\n' "$@" >&2
	@exit 2
