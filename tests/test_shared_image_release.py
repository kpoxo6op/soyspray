from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / ".github/actions/publish-image-promotion/action.yml"
CALLERS = (
    ROOT / ".github/workflows/domain-health-image.yml",
    ROOT / ".github/workflows/media-helper-image.yml",
)


def load(path: Path):
    return yaml.load(path.read_text(), Loader=yaml.BaseLoader)


def test_callers_keep_checks_before_the_shared_release_boundary() -> None:
    for path in CALLERS:
        workflow = load(path)
        steps = workflow["jobs"]["image"]["steps"]
        release = next(
            index
            for index, step in enumerate(steps)
            if step.get("uses") == "./.github/actions/publish-image-promotion"
        )
        names = [step.get("name", "") for step in steps[:release]]
        assert "Build the immutable runtime" in names
        assert "Check the packaged runtime without external network access" in names
        assert "Check the real entrypoint with disposable inputs" in names
        text = path.read_text()
        assert "docker push" not in text
        assert "gh pr create" not in text


def test_shared_release_preserves_the_publication_boundaries() -> None:
    action = load(ACTION)
    text = ACTION.read_text()
    assert action["runs"]["using"] == "composite"
    assert "github.ref == 'refs/heads/main'" in text
    assert 'GITHUB_EVENT_NAME" = workflow_dispatch' in text
    assert 'GITHUB_EVENT_NAME" = push' in text
    assert "docker push" in text
    assert "if git diff --quiet; then exit 0; fi" in text
    assert "gh pr create --draft --base main" in text
    assert "Argo CD follows" in text
    assert "standard Ansible path" not in text
