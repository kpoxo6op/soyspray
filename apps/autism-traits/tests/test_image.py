import copy
import os
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]

promote = runpy.run_path(ROOT / "apps/autism-traits/promote-image.py")["promote"]
IMAGE = "ghcr.io/kpoxo6op/autism-traits@sha256:" + "a" * 64


def read(path):
    return yaml.safe_load(path.read_text())


def test_promotion_changes_only_the_image_and_is_retryable(tmp_path):
    for name in ("deployment.yaml", "kustomization.yaml"):
        shutil.copy(ROOT / "apps/autism-traits/manifests" / name, tmp_path / name)
    before = read(tmp_path / "deployment.yaml")
    prior_kustomization = (tmp_path / "kustomization.yaml").read_bytes()
    expected = copy.deepcopy(before)
    pod = expected["spec"]["template"]["spec"]
    web = pod["containers"][0]
    web["image"] = IMAGE
    promote(IMAGE, tmp_path)
    assert read(tmp_path / "deployment.yaml") == expected
    assert (tmp_path / "kustomization.yaml").read_bytes() == prior_kustomization
    first = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    promote(IMAGE, tmp_path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == first
    next_image = IMAGE[:-1] + "b"
    promote(next_image, tmp_path)
    expected["spec"]["template"]["spec"]["containers"][0]["image"] = next_image
    assert read(tmp_path / "deployment.yaml") == expected


@pytest.mark.parametrize("image", ["latest", "ghcr.io/other/app@sha256:" + "a" * 64])
def test_invalid_image_cannot_write_a_promotion(tmp_path, image):
    with pytest.raises(ValueError, match="digest"):
        promote(image, tmp_path)
    assert not list(tmp_path.iterdir())


def test_image_publication_selector_ignores_tests_but_detects_runtime_changes(tmp_path):
    workflow = yaml.safe_load((ROOT / ".github/workflows/autism-image.yml").read_text())
    detect = next(
        step for step in workflow["jobs"]["image"]["steps"] if step.get("id") == "runtime"
    )
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")

    def commit(path, content):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        git("add", path)
        git("commit", "-m", "fixture")
        return git("rev-parse", "HEAD")

    base = commit("apps/autism-traits/app/src/App.tsx", "original\n")
    test = commit("apps/autism-traits/app/src/data/content.test.ts", "test\n")
    e2e = commit("apps/autism-traits/app/e2e/assessment.spec.ts", "browser test\n")
    runtime = commit("apps/autism-traits/app/src/App.tsx", "updated\n")
    config = commit("apps/autism-traits/config/nginx.conf", "updated\n")

    def detected(before, head):
        output = tmp_path / "output"
        output.write_text("")
        env = {
            **os.environ,
            "BEFORE": before,
            "GITHUB_SHA": head,
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(output),
            "RUNNER_TEMP": str(tmp_path),
        }
        subprocess.run(["bash", "-e", "-c", detect["run"]], cwd=repo, env=env, check=True)
        return output.read_text().strip()

    assert detected(base, test) == "changed=false"
    assert detected(test, e2e) == "changed=false"
    assert detected(e2e, runtime) == "changed=true"
    assert detected(runtime, config) == "changed=true"
