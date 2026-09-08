import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import app_diff, argocd_cli
from scripts.app_command import command

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("app", ["headlamp", "media-helper"])
def test_git_only_apps_have_no_bootstrap_or_deploy_action(app):
    for action in ("bootstrap", "deploy"):
        result = subprocess.run(
            ["make", "--no-print-directory", "-C", str(ROOT / "apps" / app), action],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert "no maintained" in result.stderr


@pytest.mark.parametrize("app", ["", "..", "../boys", "boys/other", "-f", "boys;true"])
def test_app_names_cannot_select_other_makefiles(tmp_path, app):
    with pytest.raises(ValueError, match="Application name"):
        command(app, "check", "python3", tmp_path)


def test_missing_operation_has_an_explicit_cause(tmp_path):
    with pytest.raises(ValueError, match="no maintained operation file"):
        command("boys", "check", "python3", tmp_path)


def test_app_make_receives_the_requested_native_action(tmp_path):
    folder = tmp_path / "apps/boys"
    folder.mkdir(parents=True)
    (folder / "Makefile").write_text('check:\n\t@printf "checked\\n"\n')
    result = subprocess.run(
        command("boys", "check", "python3", tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "checked\n"


def test_go_keeps_the_full_gate_when_app_is_set():
    result = subprocess.run(
        ["make", "-n", "go", "APP=boys"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert "Local gate passed." in result.stdout
    assert "-m scripts.app_command" not in result.stdout
    assert "ansible-playbook" not in result.stdout


def test_root_has_no_deploy_target():
    result = subprocess.run(
        ["make", "--no-print-directory", "deploy", "APP=boys"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "No rule to make target 'deploy'" in result.stderr


def test_operation_file_cannot_link_outside_checkout(tmp_path):
    external = tmp_path / "outside"
    external.write_text("check:\n\tfalse\n")
    root = tmp_path / "checkout"
    folder = root / "apps/boys"
    folder.mkdir(parents=True)
    (folder / "Makefile").symlink_to(external)
    with pytest.raises(ValueError, match="no maintained operation file"):
        command("boys", "check", "python3", root)


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
    (package / "dashboard.json").write_text('{"title":"local dashboard"}')
    staged = tmp_path / "staged"
    app_diff.stage_package(package, "old/app/path", staged)
    assert (staged / "old/app/path/deployment.yaml").read_text() == "local draft"
    assert (staged / "old/app/path/new.yml").read_text() == "new local manifest"
    assert (staged / "old/app/path/dashboard.json").read_text() == ('{"title":"local dashboard"}')
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
        command("autism-traits", action, "python3"),
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
    "app,tags",
    [("live-tv", "authentik,live-tv"), ("voice-assistant", "voice_assistant")],
)
def test_private_input_bootstrap_uses_the_input_playbook(tmp_path, monkeypatch, app, tags):
    log, spy = operation_spy(tmp_path, monkeypatch)
    subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-C",
            str(ROOT / "apps" / app),
            "bootstrap",
            f"ANSIBLE={spy}",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    args = ["playbooks/bootstrap-app-inputs.yml", "--tags", tags]
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


@pytest.mark.parametrize("target", ["voice-pe-upload", "status-page"])
def test_external_mutation_alias_keeps_full_check(target):
    result = subprocess.run(
        ["make", "-n", target], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert "Local gate passed." in result.stdout
