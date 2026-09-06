import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import app_diff, argocd_cli
from scripts.app_command import command

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "app,bootstrap",
    [
        (name, name not in {"headlamp", "media-helper"})
        for name in (
            "autism-traits",
            "boys",
            "cert-manager-config",
            "domain-health",
            "external-dns",
            "headlamp",
            "media-helper",
            "obsidian-livesync",
            "vaultwarden",
        )
    ],
)
def test_native_app_deployment_passes_exact_bootstrap_and_preview_arguments(
    tmp_path, app, bootstrap
):
    log = tmp_path / "calls.jsonl"
    runner = tmp_path / "ansible.py"
    runner.write_text(
        "import json, os, pathlib, sys\n"
        "with pathlib.Path(os.environ['ANSIBLE_CALL_LOG']).open('a') as f:\n"
        "    f.write(json.dumps({'cwd': os.getcwd(), 'args': sys.argv[1:]}) + '\\n')\n"
    )
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-C",
            str(ROOT / "apps" / app),
            "deploy",
            "REVISION=codex/preview",
            f"ANSIBLE={sys.executable} {runner}",
        ],
        env={**os.environ, "ANSIBLE_CALL_LOG": str(log)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    expected = [[f"apps/{app}/bootstrap.yml"]] if bootstrap else []
    expected.append(
        [
            "playbooks/bootstrap-apps.yml",
            "-e",
            "argocd_revision=codex/preview",
            "-e",
            f"argocd_preview_application={app}",
        ]
    )
    assert calls == [{"cwd": str(ROOT), "args": args} for args in expected]


@pytest.mark.parametrize("app", ["", "..", "../boys", "boys/other", "-f", "boys;true"])
def test_app_names_cannot_select_other_makefiles(tmp_path, app):
    with pytest.raises(ValueError, match="Application name"):
        command(app, "check", "python3", "HEAD", tmp_path)


def test_missing_operation_has_an_explicit_cause(tmp_path):
    with pytest.raises(ValueError, match="no maintained operation file"):
        command("boys", "check", "python3", "HEAD", tmp_path)


def test_app_make_receives_the_requested_native_action_and_revision(tmp_path):
    folder = tmp_path / "apps/boys"
    folder.mkdir(parents=True)
    (folder / "Makefile").write_text('check:\n\t@printf "%s\\n" "$(REVISION)"\n')
    result = subprocess.run(
        command("boys", "check", "python3", "topic/preview", tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "topic/preview\n"


def test_go_keeps_the_full_gate_when_app_is_set():
    result = subprocess.run(
        ["make", "-n", "go", "APP=boys"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert "make --no-print-directory full-check" in result.stdout
    assert "-m scripts.app_command" not in result.stdout
    assert "ansible-playbook" in result.stdout


def test_deploy_runs_shared_check_app_check_preflight_and_native_deploy_in_order(tmp_path):
    log = tmp_path / "calls.log"
    runner = tmp_path / "make-runner"
    runner.write_text(
        "#! /usr/bin/env python3\n"
        "import os, pathlib, sys\n"
        "pathlib.Path(os.environ['MAKE_CALL_LOG']).open('a').write(' '.join(sys.argv[1:]) + '\\n')\n"
    )
    runner.chmod(0o700)
    result = subprocess.run(
        ["make", "--no-print-directory", "deploy", "APP=boys", f"MAKE={runner}"],
        cwd=ROOT,
        env={**os.environ, "MAKE_CALL_LOG": str(log)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    assert calls == [
        "--no-print-directory shared-check",
        "--no-print-directory check APP=boys",
        "--no-print-directory deploy-preflight",
        "--no-print-directory app-command COMMAND=deploy",
    ]


@pytest.mark.parametrize("failure", ["shared-check", "check", "deploy-preflight", "app-command"])
def test_deploy_stops_when_a_stage_fails(tmp_path, failure):
    log = tmp_path / "calls.log"
    runner = tmp_path / "make-runner"
    runner.write_text(
        "#! /usr/bin/env python3\n"
        "import os, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "pathlib.Path(os.environ['MAKE_CALL_LOG']).open('a').write(' '.join(args) + '\\n')\n"
        "if os.environ['MAKE_FAIL_STAGE'] in args: raise SystemExit(23)\n"
    )
    runner.chmod(0o700)
    result = subprocess.run(
        ["make", "--no-print-directory", "deploy", "APP=boys", f"MAKE={runner}"],
        cwd=ROOT,
        env={
            **os.environ,
            "MAKE_CALL_LOG": str(log),
            "MAKE_FAIL_STAGE": failure,
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    calls = log.read_text().splitlines()
    stages = ["shared-check", "check", "deploy-preflight", "app-command"]
    assert len(calls) == stages.index(failure) + 1
    assert all(
        stage in call
        for stage, call in zip(stages[: stages.index(failure) + 1], calls, strict=True)
    )


def test_operation_file_cannot_link_outside_checkout(tmp_path):
    external = tmp_path / "outside"
    external.write_text("check:\n\tfalse\n")
    root = tmp_path / "checkout"
    folder = root / "apps/boys"
    folder.mkdir(parents=True)
    (folder / "Makefile").symlink_to(external)
    with pytest.raises(ValueError, match="no maintained operation file"):
        command("boys", "check", "python3", "HEAD", root)


def test_staging_preserves_local_changes_without_copying_ignored_credentials(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    monkeypatch.setattr(app_diff, "ROOT", tmp_path)
    package = tmp_path / "apps/example/manifests"
    package.mkdir(parents=True)
    manifest = package / "deployment.yaml"
    manifest.write_text("old")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    manifest.write_text("local draft")
    (package / ".gitignore").write_text("private.yaml\n")
    (package / "private.yaml").write_text("secret")
    (package / "new.yml").write_text("new local manifest")
    staged = tmp_path / "staged"
    app_diff.stage_package(package, "old/app/path", staged)
    assert (staged / "old/app/path/deployment.yaml").read_text() == "local draft"
    assert (staged / "old/app/path/new.yml").read_text() == "new local manifest"
    assert not (staged / "old/app/path/private.yaml").exists()
    with pytest.raises(ValueError, match="inside the temporary"):
        app_diff.stage_package(package, "../../escape", staged)
    (package / "escape.yaml").symlink_to(tmp_path / "outside.yaml")
    (tmp_path / "outside.yaml").write_text("outside")
    with pytest.raises(ValueError, match="links outside"):
        app_diff.stage_package(package, "old/app/path", staged)


@pytest.mark.parametrize("exit_code", [0, 10, 1, 20])
def test_native_diff_distinguishes_changes_from_failed_comparisons(
    tmp_path, monkeypatch, exit_code
):
    import json
    import stat

    application = {"spec": {"source": {"path": "apps/example/manifests"}}}
    kubeconfig = {"contexts": [{"context": {"namespace": "original"}}]}
    monkeypatch.setattr(
        app_diff.subprocess,
        "check_output",
        lambda args, **kwargs: json.dumps(kubeconfig if "config" in args else application).encode(),
    )
    monkeypatch.setattr(app_diff, "stage_package", lambda *args: None)
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        config = Path(kwargs["env"]["KUBECONFIG"])
        assert stat.S_IMODE(config.stat().st_mode) == 0o600
        assert json.loads(config.read_text())["contexts"][0]["context"]["namespace"] == "argocd"
        return subprocess.CompletedProcess(args, exit_code if "diff" in args else 0)

    monkeypatch.setattr(app_diff.subprocess, "run", run)
    if exit_code in (0, 10):
        app_diff.compare("example", tmp_path, "argocd")
    else:
        with pytest.raises(RuntimeError, match="comparison failed"):
            app_diff.compare("example", tmp_path, "argocd")
    assert kubeconfig["contexts"][0]["context"]["namespace"] == "original"
    assert calls[-1][-2:] == ["--diff-exit-code", "10"]


def test_cached_cli_with_wrong_checksum_is_rejected(tmp_path):
    binary = tmp_path / "argocd"
    binary.write_bytes(b"wrong artifact")
    with pytest.raises(ValueError, match="checksum"):
        argocd_cli.verify(binary)


@pytest.mark.parametrize("action", ["restore-check", "smoke"])
def test_unimplemented_app_operation_reports_unknown_without_running_another_action(action):
    result = subprocess.run(
        command("autism-traits", action, "python3", "HEAD"),
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stdout.startswith("unknown:")
    assert action in result.stdout


def operation_spy(tmp_path, monkeypatch):
    log = tmp_path / "calls.jsonl"
    spy = tmp_path / "spy.py"
    spy.write_text(
        "import json, os, pathlib, sys\n"
        "with pathlib.Path(os.environ['OPERATION_LOG']).open('a') as f:\n"
        "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
    )
    monkeypatch.setenv("OPERATION_LOG", str(log))
    return log, f"{sys.executable} {spy}"


@pytest.mark.parametrize(
    "app,enabled", [("live-tv", "true"), ("live-tv", "false"), ("voice-assistant", "true")]
)
def test_legacy_alias_preserves_ansible_arguments(tmp_path, monkeypatch, app, enabled):
    log, spy = operation_spy(tmp_path, monkeypatch)
    prefix = "LIVE_TV" if app == "live-tv" else "VOICE_ASSISTANT"
    subprocess.run(
        [
            "make",
            "-o",
            "go",
            app,
            f"ANSIBLE={spy}",
            f"{prefix}_ENABLED={enabled}",
            f"{prefix}_REVISION=codex/test",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    tags = (
        "authentik,live-tv"
        if app == "live-tv" and enabled == "true"
        else ("live-tv" if app == "live-tv" else "voice_assistant")
    )
    args = ["playbooks/deploy-argocd-apps.yml", "--tags", tags]
    if app == "live-tv":
        if enabled == "true":
            args += ["-e", "authentik_target_revision=codex/test"]
        args += ["-e", f"live_tv_enabled={enabled}", "-e", "live_tv_target_revision=codex/test"]
    else:
        args += [
            "-e",
            "voice_assistant_target_revision=codex/test",
            "-e",
            f"voice_assistant_enabled={enabled}",
        ]
    assert [json.loads(line) for line in log.read_text().splitlines()] == [args]


def test_firmware_upload_keeps_render_validate_compile_upload_order(tmp_path, monkeypatch):
    log, spy = operation_spy(tmp_path, monkeypatch)
    subprocess.run(
        [
            "make",
            "-o",
            "go",
            "voice-pe-upload",
            f"PYTHON={spy}",
            f"ESPHOME={spy}",
            "VOICE_PE_HOST=test-device",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    config = ".build/voice-pe/gi-voice-pe.yaml"
    assert [json.loads(line) for line in log.read_text().splitlines()] == [
        ["scripts/render_gi_voice_pe.py", "--output", config],
        ["config", config],
        ["compile", config],
        ["upload", config, "--device", "test-device"],
    ]


@pytest.mark.parametrize(
    "target,expected",
    [("status-page", [[]]), ("status-page-fallback", [["--check"], ["--fallback"]])],
)
def test_status_alias_preserves_script_arguments(tmp_path, monkeypatch, target, expected):
    log, spy = operation_spy(tmp_path, monkeypatch)
    subprocess.run(
        ["make", "-o", "go", target, f"PYTHON={spy}"], cwd=ROOT, check=True, capture_output=True
    )
    assert [json.loads(line) for line in log.read_text().splitlines()] == [
        ["scripts/configure_status_page.py", *args] for args in expected
    ]


@pytest.mark.parametrize("target", ["live-tv", "voice-assistant", "voice-pe-upload", "status-page"])
def test_legacy_mutation_alias_keeps_full_check_and_preflight(target):
    result = subprocess.run(
        ["make", "-n", target], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert "make --no-print-directory full-check" in result.stdout
    assert "playbooks/deploy-argocd-apps.yml --syntax-check" in result.stdout
