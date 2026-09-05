from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar
from conftest import ROOT, load_yaml


def test_longhorn_preview_changes_only_the_git_revision():
    task = load_yaml("roles/apps/longhorn/tasks/main.yml")[0]
    baseline = load_yaml(
        "playbooks/argocd/applications/infrastructure/longhorn/longhorn-application.yaml"
    )
    for revision in (None, "codex/storage-check", "true", "2026"):
        variables = {"playbook_dir": str(ROOT / "playbooks")}
        if revision is not None:
            variables["longhorn_target_revision"] = revision
        result = Templar(loader=DataLoader(), variables=variables).template(
            task["kubernetes.core.k8s"]["definition"]
        )
        assert result["spec"]["source"]["targetRevision"] == (revision or "HEAD")
        result["spec"]["source"]["targetRevision"] = "HEAD"
        assert result == baseline
