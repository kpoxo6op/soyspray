from __future__ import annotations

import subprocess

import yaml
from conftest import ROOT, load_yaml

PACKAGE = "playbooks/argocd/applications/home-automation/voice-assistant"

SPEECH_IMAGE = (
    "rhasspy/wyoming-speech-to-phrase:1.4.3@"
    "sha256:e532f0dbc6b21285c4c784212003865b9167041927328a767cb0beb1a0beaa20"
)
PIPER_IMAGE = (
    "rhasspy/wyoming-piper:2.3.1@"
    "sha256:69b7f797ae3a8c3c0202cbf97152fb795d78c2355de2a31655c20671247360d8"
)
BOOTSTRAP_IMAGE = (
    "curlimages/curl:8.14.1@sha256:9a1ed35addb45476afa911696297f8e115993df459278ed036182dd2cd22b67b"
)
SPEECH_MODEL_REVISION = "a17c6ed2bbbb09176164e81cd3161b264d0fb2ba"
SPEECH_MODEL_SHA256 = "3dbf8c16b2d08767eba4866a444f075d0a5b1304c73ca366d2c60346b28759e7"
PIPER_MODEL_REVISION = "ea046e8458f6acd997706d6e6066a022b42f6fb1"
PIPER_MODEL_SHA256 = "5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f"
PIPER_CONFIG_SHA256 = "efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0"


def render_voice_stack() -> list[dict]:
    result = subprocess.run(
        ["kubectl", "kustomize", PACKAGE],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def resource(resources: list[dict], kind: str, name: str) -> dict:
    return next(
        item for item in resources if item["kind"] == kind and item["metadata"]["name"] == name
    )


def test_voice_stack_is_an_independent_gitops_package() -> None:
    resources = render_voice_stack()
    names_by_kind = {
        kind: {item["metadata"]["name"] for item in resources if item["kind"] == kind}
        for kind in ("Deployment", "Job", "Service", "PersistentVolumeClaim")
    }

    assert names_by_kind["Deployment"] == {"speech-to-phrase", "piper-en"}
    assert names_by_kind["Job"] == {"voice-model-bootstrap-v1"}
    assert names_by_kind["Service"] == {"speech-to-phrase", "piper-en"}
    assert names_by_kind["PersistentVolumeClaim"] == {
        "speech-to-phrase-data-v1",
        "piper-en-data-v1",
    }

    application = load_yaml(f"{PACKAGE}/voice-assistant-application.yaml")
    assert application["spec"]["source"] == {
        "repoURL": "https://github.com/kpoxo6op/soyspray.git",
        "targetRevision": "HEAD",
        "path": PACKAGE,
    }
    assert application["spec"]["syncPolicy"]["automated"] == {
        "prune": True,
        "selfHeal": True,
    }
    assert "PruneLast=true" in application["spec"]["syncPolicy"]["syncOptions"]


def test_voice_workloads_are_local_persistent_and_restricted() -> None:
    resources = render_voice_stack()
    speech = resource(resources, "Deployment", "speech-to-phrase")
    piper = resource(resources, "Deployment", "piper-en")

    expected = {
        "speech-to-phrase": {
            "deployment": speech,
            "image": SPEECH_IMAGE,
            "port": 10300,
            "data_claim": "speech-to-phrase-data-v1",
        },
        "piper-en": {
            "deployment": piper,
            "image": PIPER_IMAGE,
            "port": 10200,
            "data_claim": "piper-en-data-v1",
        },
    }

    for contract in expected.values():
        pod = contract["deployment"]["spec"]["template"]["spec"]
        container = pod["containers"][0]
        assert pod["automountServiceAccountToken"] is False
        assert pod["securityContext"] == {
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 1000,
            "fsGroup": 1000,
            "seccompProfile": {"type": "RuntimeDefault"},
        }
        assert container["image"] == contract["image"]
        assert container["resources"]["requests"]
        assert container["resources"]["limits"]
        assert container["securityContext"] == {
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": True,
            "capabilities": {"drop": ["ALL"]},
        }
        assert container["startupProbe"].get("exec")
        assert container["livenessProbe"]["tcpSocket"]["port"] == contract["port"]
        assert any(
            volume.get("persistentVolumeClaim", {}).get("claimName") == contract["data_claim"]
            for volume in pod["volumes"]
        )

    speech_container = speech["spec"]["template"]["spec"]["containers"][0]
    assert speech["spec"]["template"]["metadata"]["annotations"] == {
        "voice.soyspray.vip/token-revision": "1"
    }
    assert speech["spec"]["template"]["spec"]["enableServiceLinks"] is True
    speech_text = yaml.safe_dump(speech_container)
    assert "/run/secrets/home-assistant/token" in speech_text
    assert "secretKeyRef" not in speech_text
    assert "--retrain-seconds" in speech_text
    assert "300" in speech_text
    assert "HOME_ASSISTANT_SERVICE_HOST" in speech_text
    assert "home-assistant.home-automation.svc.cluster.local" not in speech_text
    assert "training_info.json" in speech_text
    assert ".artifact-sha256" in speech_text
    assert speech_container["readinessProbe"].get("exec")

    piper_container = piper["spec"]["template"]["spec"]["containers"][0]
    assert piper_container["readinessProbe"].get("exec")
    assert ".artifact-sha256" in yaml.safe_dump(piper_container["readinessProbe"])

    piper_args = piper["spec"]["template"]["spec"]["containers"][0]["args"]
    assert "--voice" in piper_args
    assert "en_US-lessac-medium" in piper_args
    assert "--download-dir" in piper_args
    assert "/data" in piper_args

    for name, port in (("speech-to-phrase", 10300), ("piper-en", 10200)):
        service = resource(resources, "Service", name)
        assert service["spec"]["type"] == "ClusterIP"
        assert service["spec"]["ports"] == [
            {"name": "wyoming", "port": port, "protocol": "TCP", "targetPort": port}
        ]

    policies = {
        item["metadata"]["name"]: item for item in resources if item["kind"] == "NetworkPolicy"
    }
    assert set(policies) == {"speech-to-phrase", "piper-en", "voice-model-bootstrap"}
    for policy in (policies["speech-to-phrase"], policies["piper-en"]):
        assert policy["spec"]["policyTypes"] == ["Ingress", "Egress"]
        assert policy["spec"]["ingress"][0]["from"] == [
            {"podSelector": {"matchLabels": {"app": "home-assistant"}}}
        ]
        assert 443 not in {
            port["port"]
            for rule in policy["spec"].get("egress", [])
            for port in rule.get("ports", [])
        }

    assert len(policies["speech-to-phrase"]["spec"]["egress"]) == 1
    bootstrap = policies["voice-model-bootstrap"]
    assert bootstrap["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-2"
    assert bootstrap["spec"]["egress"][0]["to"] == [{"ipBlock": {"cidr": "169.254.25.10/32"}}]
    assert any(
        port == {"port": 443, "protocol": "TCP"}
        for rule in bootstrap["spec"]["egress"]
        for port in rule.get("ports", [])
    )


def test_model_bootstrap_is_immutable_and_verified() -> None:
    resources = render_voice_stack()
    job = resource(resources, "Job", "voice-model-bootstrap-v1")
    pod = job["spec"]["template"]["spec"]
    container = pod["containers"][0]
    command = yaml.safe_dump(container)

    assert job["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "-1"
    assert job["spec"]["backoffLimit"] == 4
    assert pod["restartPolicy"] == "Never"
    assert pod["automountServiceAccountToken"] is False
    assert container["image"] == BOOTSTRAP_IMAGE
    for immutable_value in (
        SPEECH_MODEL_REVISION,
        SPEECH_MODEL_SHA256,
        PIPER_MODEL_REVISION,
        PIPER_MODEL_SHA256,
        PIPER_CONFIG_SHA256,
    ):
        assert immutable_value in command
    assert "resolve/main" not in command
    assert ".part" in command
    assert {mount["name"] for mount in container["volumeMounts"]} == {
        "speech-data",
        "piper-data",
    }


def test_ansible_bootstraps_the_runtime_secret_and_argocd_application() -> None:
    defaults = load_yaml("roles/apps/voice-assistant/defaults/main.yml")
    tasks = (ROOT / "roles/apps/voice-assistant/tasks/main.yml").read_text()
    enabled_tasks = (ROOT / "roles/apps/voice-assistant/tasks/enabled.yml").read_text()
    disabled_tasks = (ROOT / "roles/apps/voice-assistant/tasks/disabled.yml").read_text()
    playbook = load_yaml("playbooks/deploy-argocd-apps.yml")

    assert defaults["voice_assistant_target_revision"] == "HEAD"
    assert defaults["voice_assistant_enabled"] is True
    assert "VOICE_ASSISTANT_HA_TOKEN" in defaults["voice_assistant_ha_token"]
    assert "enabled.yml" in tasks
    assert "disabled.yml" in tasks
    assert "kubernetes.core.k8s_info" in enabled_tasks
    assert "voice-assistant-ha-token" in enabled_tasks
    assert "no_log: true" in enabled_tasks
    assert "voice_assistant_target_revision" in enabled_tasks
    assert "voice-assistant-application.yaml" in enabled_tasks
    assert "Remove automated sync" in disabled_tasks
    assert "state: absent" in disabled_tasks
    assert "voice-assistant" in disabled_tasks
    assert any(
        item["role"] == "apps/voice-assistant" for item in playbook[0]["vars"]["argocd_app_roles"]
    )

    makefile = (ROOT / "Makefile").read_text()
    assert "VOICE_ASSISTANT_REVISION ?= HEAD" in makefile
    assert "VOICE_ASSISTANT_ENABLED ?= true" in makefile
    assert PACKAGE in makefile
    assert "roles/apps/voice-assistant/tasks/*.yml" in makefile
    assert "roles/apps/voice-assistant/defaults/*.yml" in makefile
    assert "voice-assistant: go" in makefile
    assert "--tags voice_assistant" in makefile
    assert "voice_assistant_target_revision=$(VOICE_ASSISTANT_REVISION)" in makefile
    assert "voice_assistant_enabled=$(VOICE_ASSISTANT_ENABLED)" in makefile


def test_runbook_records_every_non_git_home_assistant_step() -> None:
    runbook = (ROOT / PACKAGE / "README.md").read_text()

    for required in (
        "VOICE_ASSISTANT_HA_TOKEN",
        "speech-to-phrase.home-automation.svc.cluster.local",
        "piper-en.home-automation.svc.cluster.local",
        "GI",
        "Okay Nabu",
        "light.top",
        "light.middle",
        "light.bottom",
        "Assist exposure",
        "Area",
        "Rollback",
        "dedicated Home Assistant user",
        "requires Administrator",
        "VOICE_ASSISTANT_ENABLED=false",
        SPEECH_MODEL_REVISION,
        SPEECH_MODEL_SHA256,
        PIPER_MODEL_REVISION,
        PIPER_MODEL_SHA256,
        "WAN",
        "training_info.json",
        "Wyoming transcription",
        "scripts/ha_voice_smoke.py",
        "kubectl exec -i",
        "voice.soyspray.vip/token-revision",
        "Revoke the old token only after",
        "Push this unchanged rotation branch",
        "before the annotation change",
        "internal_url",
        "192.168.20.33:8123",
        "home-assistant-voice-0a9b95",
        "port `6053`",
    ):
        assert required in runbook

    assert "Gee Ai" in runbook
    assert ".storage" in runbook


def test_wyoming_smoke_checks_tts_audio_and_speech_transcript() -> None:
    smoke_path = ROOT / "scripts/ha_voice_smoke.py"
    smoke = smoke_path.read_text()
    compile(smoke, smoke_path, "exec")

    for required in (
        "AsyncTcpClient",
        "Synthesize",
        "AudioChunk",
        "Transcribe",
        "Transcript",
        "piper-en.home-automation.svc.cluster.local",
        "speech-to-phrase.home-automation.svc.cluster.local",
        "turn on the top",
    ):
        assert required in smoke


def test_home_assistant_voice_uses_the_lan_service_url() -> None:
    home_assistant = "playbooks/argocd/applications/home-automation/home-assistant"
    bootstrap = load_yaml(f"{home_assistant}/configmap-bootstrap.yaml")["data"][
        "configuration.yaml"
    ]
    service = load_yaml(f"{home_assistant}/service.yaml")["spec"]

    assert (
        f"internal_url: http://{service['loadBalancerIP']}:{service['ports'][0]['port']}"
        in bootstrap
    )


def test_home_assistant_rolls_out_the_voice_lan_url() -> None:
    deployment = load_yaml(
        "playbooks/argocd/applications/home-automation/home-assistant/deployment.yaml"
    )

    assert deployment["spec"]["template"]["metadata"]["annotations"] == {
        "soyspray.vip/bootstrap-config-revision": "2026-08-14-voice-lan-url"
    }
