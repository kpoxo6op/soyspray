import os
import re
import subprocess
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


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_callers_run_packaged_checks_before_shared_publication() -> None:
    for path in CALLERS:
        steps = load(path)["jobs"]["image"]["steps"]
        release = next(
            index
            for index, step in enumerate(steps)
            if step.get("uses") == "./.github/actions/publish-image-promotion"
        )
        commands = [step.get("run", "") for step in steps]
        assert any("docker build" in command for command in commands[:release])
        checks = [command for command in commands[:release] if "docker run" in command]
        assert len(checks) >= 2
        assert all("--network none" in command and "--read-only" in command for command in checks)
        assert any("test_runtime.py" in command for command in checks)
        assert any("docker exec" in command for command in commands[:release])
        assert not any(
            "docker push" in command or "gh pr create" in command for command in commands
        )
        assert release == len(steps) - 1


def test_runtime_detection_rejects_unrelated_pushes_and_unrequested_publication(tmp_path) -> None:
    action = load(ACTION)
    detect = next(step for step in action["runs"]["steps"] if step.get("id") == "runtime")
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")

    def commit(path: str, content: str) -> str:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        git(repo, "add", path)
        git(repo, "commit", "-m", "fixture")
        return git(repo, "rev-parse", "HEAD")

    base = commit("apps/example/app/runtime.py", "original\n")
    docs = commit("docs/readme.md", "unrelated\n")
    changed = commit("apps/example/app/runtime.py", "updated\n")

    def detected(before: str, head: str, event: str, requested: str) -> str:
        output = tmp_path / "output"
        output.write_text("")
        env = {
            **os.environ,
            "BEFORE": before,
            "GITHUB_SHA": head,
            "GITHUB_EVENT_NAME": event,
            "GITHUB_OUTPUT": str(output),
            "RUNNER_TEMP": str(tmp_path),
            "REQUEST_PUBLISH": requested,
            "RUNTIME_PATHS": "apps/example/app",
        }
        subprocess.run(["bash", "-e", "-c", detect["run"]], cwd=repo, env=env, check=True)
        return output.read_text().strip()

    assert detected(base, docs, "push", "true") == "changed=false"
    assert detected(docs, changed, "push", "false") == "changed=false"
    assert detected(docs, changed, "push", "true") == "changed=true"
    assert detected(docs, changed, "workflow_dispatch", "true") == "changed=true"


def test_publication_and_promotion_require_the_main_runtime_gate() -> None:
    steps = load(ACTION)["runs"]["steps"]
    publish = next(step for step in steps if step.get("id") == "publish")
    promotion = next(step for step in steps if "gh pr create" in step.get("run", ""))
    gate = "github.ref == 'refs/heads/main' && steps.runtime.outputs.changed == 'true'"
    for step in (publish, promotion):
        assert re.sub(r"\s+", " ", step["if"].strip()) == gate
    assert "docker push" in publish["run"]
    assert "docker image inspect" in publish["run"]
    assert "git diff --quiet" in promotion["run"]
    assert 'git add "$MANIFEST"' in promotion["run"]
    assert "gh pr create --draft --base main" in promotion["run"]
