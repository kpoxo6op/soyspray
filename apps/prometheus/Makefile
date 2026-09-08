include $(dir $(lastword $(MAKEFILE_LIST)))../common.mk
PROMETHEUS_STACK_UID ?= a58c2137-4482-4926-b659-ad08ab017aed
PROMETHEUS_CRDS_UID ?= 72c2f99a-2820-4751-ac38-42c2097b5504
.PHONY: check diff deploy bootstrap restore-check smoke

check:
	cd $(ROOT) && $(PYTHON) -m pytest -q apps/prometheus/tests tests/test_argocd_root.py \
		tests/test_authentik_dashboard.py tests/test_longhorn_metric_filter.py tests/test_sso.py \
		tests/test_sso_legacy_proxy.py
	cd $(ROOT) && $(PYTHON) scripts/check_prometheus.py
	cd $(ROOT) && $(PYTHON) -m ansiblelint apps/prometheus/*.yml
	cd $(ROOT) && kubectl kustomize apps/prometheus/argocd >/dev/null

diff:
	cd $(ROOT) && $(PYTHON) -m scripts.app_diff --app kube-prometheus-stack --package apps/prometheus

deploy:
	cd $(ROOT) && $(ANSIBLE) apps/prometheus/bootstrap.yml
	cd $(ROOT) && $(ANSIBLE) apps/prometheus/adopt.yml \
		-e prometheus_revision=$(REVISION) \
		-e prometheus_stack_uid=$(PROMETHEUS_STACK_UID) \
		-e prometheus_crds_uid=$(PROMETHEUS_CRDS_UID)
	cd $(ROOT) && $(ANSIBLE) playbooks/bootstrap-apps.yml -e argocd_revision=$(REVISION) \
		-e argocd_preview_application=$(if $(filter HEAD,$(REVISION)),,kube-prometheus-stack)

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
