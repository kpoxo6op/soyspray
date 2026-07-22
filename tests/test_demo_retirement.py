from __future__ import annotations

import yaml
from conftest import ROOT


def test_demo_cleanup_quiesces_apps_before_deleting_namespaces() -> None:
    tasks = yaml.safe_load((ROOT / "roles/apps/demo-cleanup/tasks/main.yml").read_text())
    names = [task["name"] for task in tasks]
    assert names.index("Quiesce retired demo applications") < names.index(
        "Remove retired demo applications"
    )
    assert names.index("Remove retired demo applications") < names.index(
        "Remove retired demo namespaces and data"
    )


def test_demo_cleanup_scope_is_only_battlemap_and_jira() -> None:
    defaults = yaml.safe_load((ROOT / "roles/apps/demo-cleanup/defaults/main.yml").read_text())
    assert defaults["retired_demo_applications"] == ["battlemap", "jira"]
    assert defaults["retired_demo_namespaces"] == ["battlemap", "jira"]
