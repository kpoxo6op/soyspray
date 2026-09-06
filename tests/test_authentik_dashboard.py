from __future__ import annotations

import json

from conftest import ROOT, load_yaml

DASHBOARD_PATH = ROOT / (
    "playbooks/argocd/applications/observability/prometheus/dashboards/authentik.json"
)
ALERTS_PATH = "playbooks/argocd/applications/observability/prometheus/alerts/authentik.yaml"
KUSTOMIZATION_PATH = "playbooks/argocd/applications/observability/prometheus/kustomization.yaml"
PROMETHEUS = {"type": "prometheus", "uid": "${datasource}"}


def load_dashboard() -> dict:
    return json.loads(DASHBOARD_PATH.read_text())


def dashboard_expressions(dashboard: dict) -> list[str]:
    return [target["expr"] for panel in dashboard["panels"] for target in panel.get("targets", [])]


def test_authentik_dashboard_is_native_focused_and_well_laid_out() -> None:
    dashboard = load_dashboard()
    panels = dashboard["panels"]

    assert dashboard["title"] == "Authentik"
    assert dashboard["uid"] == "authentik"
    assert dashboard["schemaVersion"] >= 39
    assert {"authentik", "identity", "soyspray"} <= set(dashboard["tags"])
    assert DASHBOARD_PATH.stat().st_size < 150_000

    variables = {item["name"]: item for item in dashboard["templating"]["list"]}
    assert variables["datasource"]["type"] == "datasource"
    assert variables["datasource"]["query"] == "prometheus"

    assert {panel["type"] for panel in panels} <= {
        "bargauge",
        "row",
        "stat",
        "text",
        "timeseries",
    }
    text_panels = [panel for panel in panels if panel["type"] == "text"]
    assert len(text_panels) == 1
    intro = text_panels[0]["options"]["content"]
    intro_lines = intro.splitlines()
    assert len(intro_lines[0]) <= 24
    assert len(" ".join(intro_lines[1:])) <= 90
    assert "2026.5.6" in intro
    assert "PostgreSQL" in intro
    assert len(intro) < 650
    assert "<img" not in intro
    assert "![" not in intro

    ids = [panel["id"] for panel in panels]
    assert len(ids) == len(set(ids))
    occupied: set[tuple[int, int]] = set()
    for panel in panels:
        position = panel["gridPos"]
        assert position["x"] >= 0
        assert position["y"] >= 0
        assert position["w"] > 0
        assert position["h"] > 0
        assert position["x"] + position["w"] <= 24
        cells = {
            (x, y)
            for x in range(position["x"], position["x"] + position["w"])
            for y in range(position["y"], position["y"] + position["h"])
        }
        assert occupied.isdisjoint(cells), panel["title"]
        occupied.update(cells)

        if panel["type"] in {"row", "text"}:
            continue
        assert panel["datasource"] == PROMETHEUS
        assert panel["targets"]
        for target in panel["targets"]:
            assert target["datasource"] == PROMETHEUS
            assert target["expr"]


def test_authentik_dashboard_covers_live_authentik_and_cnpg_metrics() -> None:
    dashboard = load_dashboard()
    expressions = dashboard_expressions(dashboard)
    query_text = "\n".join(expressions)
    row_titles = {panel["title"] for panel in dashboard["panels"] if panel["type"] == "row"}

    assert {
        "Status",
        "Traffic, latency, and errors",
        "Embedded outpost and proxy traffic",
        "Worker and task health",
        "Pod resources",
        "Authentik PostgreSQL",
    } <= row_titles

    required_metrics = {
        "django_http_requests_total_by_method_total",
        "django_http_responses_total_by_status_total",
        "authentik_main_request_duration_seconds_bucket",
        "authentik_outpost_connection",
        "authentik_outpost_proxy_request_duration_seconds_count",
        "authentik_outpost_proxy_request_duration_seconds_bucket",
        "authentik_tasks_workers",
        "authentik_tasks_queued",
        "authentik_tasks_in_progress",
        "authentik_tasks_duration_milliseconds_bucket",
        "container_cpu_usage_seconds_total",
        "container_memory_working_set_bytes",
        "kube_pod_container_status_restarts_total",
        "cnpg_collector_up",
        "cnpg_pg_replication_lag",
        "barman_cloud_cloudnative_pg_io_last_available_backup_timestamp",
        "cnpg_pg_database_size_bytes",
        "cnpg_pg_stat_archiver_seconds_since_last_archival",
        "cnpg_pg_stat_archiver_failed_count",
        "cnpg_backends_total",
    }
    assert all(metric in query_text for metric in required_metrics)
    assert any(
        "authentik_outpost_proxy_request_duration_seconds_count" in expression
        and "by (host, method)" in expression
        for expression in expressions
    )
    assert any(
        "authentik_outpost_proxy_request_duration_seconds_bucket" in expression
        and "by (le, host)" in expression
        for expression in expressions
    )

    cnpg_expressions = [
        expression
        for expression in expressions
        if "cnpg_" in expression or "barman_cloud_" in expression
    ]
    assert cnpg_expressions
    assert all('namespace="authentik"' in expression for expression in cnpg_expressions)
    assert all(
        'job="authentik/authentik-postgresql"' in expression for expression in cnpg_expressions
    )
    assert all("or vector(0)" not in expression for expression in cnpg_expressions)


def test_authentik_dashboard_keeps_idle_series_useful_and_covers_all_pods() -> None:
    expressions = dashboard_expressions(load_dashboard())

    resource_expressions = [
        expression
        for expression in expressions
        if any(
            metric in expression
            for metric in (
                "container_cpu_usage_seconds_total",
                "container_memory_working_set_bytes",
                "kube_pod_container_status_restarts_total",
            )
        )
    ]
    assert len(resource_expressions) == 3
    assert all(
        'container=~"server|worker|postgres"' in expression for expression in resource_expressions
    )

    archive_gap = next(
        expression
        for expression in expressions
        if "cnpg_pg_stat_archiver_seconds_since_last_archival" in expression
    )
    assert "cnpg_collector_pg_wal_archive_status" in archive_gap
    assert 'value="ready"' in archive_gap

    proxy_p95 = next(
        expression
        for expression in expressions
        if "authentik_outpost_proxy_request_duration_seconds_bucket" in expression
    )
    assert "authentik_outpost_proxy_request_duration_seconds_count" in proxy_p95
    assert "> 0" in proxy_p95

    task_p95_expressions = [
        expression
        for expression in expressions
        if "authentik_tasks_duration_milliseconds_bucket" in expression
    ]
    assert task_p95_expressions
    assert all(
        "authentik_tasks_duration_milliseconds_count" in expression and "> 0" in expression
        for expression in task_p95_expressions
    )

    task_throughput = next(
        expression for expression in expressions if "authentik_tasks_total" in expression
    )
    assert "> 0" in task_throughput

    database_growth = next(
        expression for expression in expressions if "sum by (pod, datname)" in expression
    )
    assert 'datname="authentik"' in database_growth


def test_authentik_alerts_are_product_specific_and_actionable() -> None:
    manifest = load_yaml(ALERTS_PATH)
    assert manifest["kind"] == "PrometheusRule"
    assert manifest["metadata"]["name"] == "authentik"
    assert manifest["metadata"]["namespace"] == "monitoring"
    assert manifest["metadata"]["labels"]["release"] == "kube-prometheus-stack"

    rules = manifest["spec"]["groups"][0]["rules"]
    alerts = {rule["alert"]: rule for rule in rules}
    assert set(alerts) == {
        "AuthentikHighHTTP5xxRate",
        "AuthentikTaskQueueBacklog",
        "AuthentikWorkerVersionMismatch",
        "AuthentikEmbeddedOutpostDisconnected",
        "AuthentikPostgreSQLBackupStale",
        "AuthentikPostgreSQLReplicationLag",
        "AuthentikPostgreSQLWALArchivingStalled",
        "AuthentikPostgreSQLArchiverFailures",
    }
    for rule in rules:
        assert rule["for"]
        assert rule["labels"]["severity"] in {"warning", "critical"}
        assert rule["annotations"]["summary"]
        assert rule["annotations"]["description"].startswith("Check ")

    alert_queries = "\n".join(str(rule["expr"]) for rule in rules)
    assert "django_http_responses_total_by_status_total" in alert_queries
    assert "authentik_tasks_queued" in alert_queries
    assert 'version_matched="False"' in alert_queries
    assert "authentik_outpost_connection" in alert_queries
    assert "barman_cloud_cloudnative_pg_io_last_available_backup_timestamp" in alert_queries
    assert "cnpg_pg_replication_lag" in alert_queries
    assert "cnpg_pg_stat_archiver_seconds_since_last_archival" in alert_queries
    assert "cnpg_pg_stat_archiver_failed_count" in alert_queries
    assert "KubePod" not in alert_queries
    assert "TargetDown" not in alert_queries


def test_authentik_dashboard_and_alerts_are_provisioned() -> None:
    kustomization = load_yaml(KUSTOMIZATION_PATH)
    generators = {item["name"]: item for item in kustomization["configMapGenerator"]}
    dashboard = generators["grafana-dashboard-authentik"]

    assert dashboard["files"] == ["dashboards/authentik.json"]
    assert dashboard["options"]["labels"]["grafana_dashboard"] == "1"
    assert (
        dashboard["options"]["annotations"]["kustomize.toolkit.fluxcd.io/substitute"] == "disabled"
    )
    assert "alerts/authentik.yaml" in kustomization["resources"]
