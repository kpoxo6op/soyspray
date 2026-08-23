from __future__ import annotations

import importlib.util
import re
import subprocess
from hashlib import sha256

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
OPENWAKEWORD_IMAGE = (
    "rhasspy/wyoming-openwakeword:2.1.0@"
    "sha256:52cb1168731a1849fc28cf339c935fde58746bbabc94226668a40ef6ddf5d42b"
)
STOP_MODEL_SHA256 = "b5a18c4ad681a89950dfade31011e1631bdcb333e93c84519a1a63ff4f071146"
BOOTSTRAP_IMAGE = (
    "curlimages/curl:8.14.1@sha256:9a1ed35addb45476afa911696297f8e115993df459278ed036182dd2cd22b67b"
)
SPEECH_MODEL_REVISION = "a17c6ed2bbbb09176164e81cd3161b264d0fb2ba"
SPEECH_MODEL_SHA256 = "3dbf8c16b2d08767eba4866a444f075d0a5b1304c73ca366d2c60346b28759e7"
PIPER_MODEL_REVISION = "ea046e8458f6acd997706d6e6066a022b42f6fb1"
PIPER_MODEL_SHA256 = "5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f"
PIPER_CONFIG_SHA256 = "efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0"
DEPLOYED_GI_MODEL_CONFIGMAP = "openwakeword-gi-model-v7b"
DEPLOYED_GI_MODEL_SHA256 = "e61dd9f2880f226b05b8f9885c053fa7ec7805170c3f3b4d56427c6294cb4be0"


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


def test_voice_services_have_their_own_kustomize_package() -> None:
    resources = render_voice_stack()
    names_by_kind = {
        kind: {item["metadata"]["name"] for item in resources if item["kind"] == kind}
        for kind in ("Deployment", "Job", "Service", "PersistentVolumeClaim")
    }

    assert names_by_kind["Deployment"] == {
        "speech-to-phrase",
        "piper-en",
        "openwakeword-gi",
    }
    assert names_by_kind["Job"] == {"voice-model-bootstrap-v1"}
    assert names_by_kind["Service"] == {
        "speech-to-phrase",
        "piper-en",
        "openwakeword-gi",
    }
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


def test_voice_services_use_local_storage_and_limited_network_access() -> None:
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
    assert set(policies) == {
        "speech-to-phrase",
        "piper-en",
        "openwakeword-gi",
        "voice-model-bootstrap",
    }
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


def test_gi_model_runs_locally_without_wan_access() -> None:
    resources = render_voice_stack()
    deployment = resource(resources, "Deployment", "openwakeword-gi")
    service = resource(resources, "Service", "openwakeword-gi")
    policy = resource(resources, "NetworkPolicy", "openwakeword-gi")
    pod = deployment["spec"]["template"]["spec"]
    container = pod["containers"][0]

    assert pod["automountServiceAccountToken"] is False
    assert pod["securityContext"] == {
        "runAsNonRoot": True,
        "runAsUser": 1000,
        "runAsGroup": 1000,
        "fsGroup": 1000,
        "seccompProfile": {"type": "RuntimeDefault"},
    }
    assert container["image"] == OPENWAKEWORD_IMAGE
    assert container["command"] == [
        "/usr/src/.venv/bin/python3",
        "-P",
        "-m",
        "wyoming_openwakeword",
    ]
    assert container["args"] == [
        "--uri",
        "tcp://0.0.0.0:10400",
        "--custom-model-dir",
        "/models",
        "--threshold",
        "0.65",
        "--trigger-level",
        "2",
    ]
    assert container["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "capabilities": {"drop": ["ALL"]},
    }
    assert container["startupProbe"].get("exec")
    startup_probe_command = container["startupProbe"]["exec"]["command"][2]
    assert "hashlib.sha256" in startup_probe_command
    assert "handler.__file__" in startup_probe_command
    assert "startswith('/patched/')" in startup_probe_command
    assert "'OKAY_NABU' not in handler_source" in startup_probe_command
    assert "MODEL_SHA256_PENDING" not in startup_probe_command
    assert DEPLOYED_GI_MODEL_SHA256 in startup_probe_command
    assert "OpenWakeWord.from_model('/models/gi.tflite')" in startup_probe_command
    assert "model.input_windows == 16" in startup_probe_command
    assert "model.process_streaming" in startup_probe_command
    assert "np.zeros" in startup_probe_command
    assert container["startupProbe"]["timeoutSeconds"] == 20
    assert container["readinessProbe"]["tcpSocket"]["port"] == 10400
    assert {item["name"]: item["value"] for item in container["env"]} == {"PYTHONPATH": "/patched"}
    assert container["livenessProbe"] == {
        "tcpSocket": {"port": 10400},
        "periodSeconds": 30,
        "failureThreshold": 3,
    }
    assert service["spec"] == {
        "type": "ClusterIP",
        "selector": {"app": "openwakeword-gi"},
        "ports": [{"name": "wyoming", "port": 10400, "protocol": "TCP", "targetPort": 10400}],
    }
    assert policy["spec"]["ingress"] == [
        {
            "from": [{"podSelector": {"matchLabels": {"app": "home-assistant"}}}],
            "ports": [{"port": 10400, "protocol": "TCP"}],
        }
    ]
    assert policy["spec"]["egress"] == []

    kustomization = load_yaml(f"{PACKAGE}/kustomization.yaml")
    assert kustomization["configMapGenerator"] == [
        {
            "name": "openwakeword-gi-patch",
            "files": ["patch.py=gi_only_openwakeword.py"],
        }
    ]
    model_volume = next(volume for volume in pod["volumes"] if volume["name"] == "models")
    assert model_volume["configMap"]["name"] == DEPLOYED_GI_MODEL_CONFIGMAP
    tmp_volume = next(volume for volume in pod["volumes"] if volume["name"] == "tmp")
    assert tmp_volume == {"name": "tmp", "emptyDir": {"sizeLimit": "256Mi"}}
    init = pod["initContainers"][0]
    assert init["name"] == "patch-gi-only"
    assert init["image"] == OPENWAKEWORD_IMAGE
    assert init["command"] == [
        "/usr/src/.venv/bin/python3",
        "/patch-source/patch.py",
    ]
    patch_maps = [
        item
        for item in resources
        if item["kind"] == "ConfigMap"
        and item["metadata"]["name"].startswith("openwakeword-gi-patch-")
    ]
    assert len(patch_maps) == 1
    assert set(patch_maps[0]["data"]) == {"patch.py"}


def test_openwakeword_accepts_only_the_gi_model() -> None:
    patch_path = ROOT / PACKAGE / "gi_only_openwakeword.py"
    spec = importlib.util.spec_from_file_location("gi_only_openwakeword", patch_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = """import logging
import time
from dataclasses import dataclass

from pyopen_wakeword import Model, OpenWakeWord, OpenWakeWordFeatures

_LOGGER = logging.getLogger(__name__)

DEFAULT_MODEL = Model.OKAY_NABU

            if detect.names:
                for ww_name in detect.names:
                    if ww_name in self.state.custom_models:
                        ww_names.add(ww_name)
                    else:
                        try:
                            model = Model(ww_name)
                            ww_names.add(ww_name)
                        except ValueError:
                            continue

            if not ww_names:
                ww_names.add(DEFAULT_MODEL.value)

                model_path = self.state.custom_models.get(ww_name)
                if model_path is not None:
                    oww_model = OpenWakeWord.from_model(model_path)
                else:
                    try:
                        model = Model(ww_name)
                        oww_model = OpenWakeWord.from_builtin(model)
                    except ValueError:
                        pass

        models: List[WakeModel] = []
        for model in Model:
            phrase = _get_phrase(model.value)
            models.append(
                WakeModel(
                    name=model.value,
                    description=phrase,
                    phrase=phrase,
                    attribution=Attribution(
                        name="dscripka",
                        url="https://github.com/dscripka/openWakeWord",
                    ),
                    installed=True,
                    languages=["en"],
                    version="v0.1",
                )
            )

        for custom_model in self.state.custom_models:

        self.audio_timestamp = 0

        _LOGGER.debug("Client connected: %s", self.client_id)

            self.audio_timestamp = 0
            self.oww_features.reset()

        elif AudioChunk.is_type(event.type):
            chunk = self.converter.convert(AudioChunk.from_event(event))
            for features in self.oww_features.process_streaming(chunk.audio):

                        if prob <= self.threshold:
                            continue

                        detector.triggers_left -= 1
                        if detector.triggers_left > 0:
                            continue

                        detector.is_detected = True
                        detector.last_triggered = time.monotonic()
                        await self.write_event(
                            Detection(
                                name=detector.id, timestamp=self.audio_timestamp
                            ).event()
                        )

                        _LOGGER.debug(
                            "Detected %s at %s", detector.id, self.audio_timestamp
                        )
"""
    patched = module.patch_handler(source, sha256(source.encode()).hexdigest())

    assert "OKAY_NABU" not in patched
    assert "Model(ww_name)" not in patched
    assert "for model in Model:" not in patched
    assert "if ww_name in self.state.custom_models" in patched
    assert "for custom_model in self.state.custom_models" in patched
    assert "if chunk_peak >= 12:" in patched
    assert "if audio_is_recent:" in patched
    assert "detector.triggers_left = self.trigger_level" in patched
    assert "GI_CANDIDATE" in patched
    assert "GI_DETECTION" in patched

    candidate_log = patched.index('"GI_CANDIDATE')
    detection_log = patched.index('"GI_DETECTION')
    candidate_block = patched[
        candidate_log : patched.index("if not audio_is_recent:", candidate_log)
    ]
    detection_block = patched[detection_log : patched.index("_LOGGER.debug(", detection_log)]
    for log_block in (candidate_block, detection_block):
        for field in (
            "client_id=%s",
            "model=%s",
            "audio_timestamp=%s",
            "score=%.6f",
            "chunk_peak=%s",
            "last_audio_peak=%s",
            "recent_audio_time_left_ms=%s",
            "audio_is_recent=%s",
            "triggers_left=%s",
        ):
            assert field in log_block
        assert "chunk.audio" not in log_block

    assert patched.rfind("_LOGGER.info(", 0, candidate_log) > -1
    assert patched.rfind("_LOGGER.info(", 0, detection_log) > -1
    assert candidate_log < patched.index("if not audio_is_recent:", candidate_log)
    assert patched.index("await self.write_event(") < detection_log


def test_gi_voice_pe_firmware_renderer_disables_nabu() -> None:
    from scripts.render_gi_voice_pe import (
        MICRO_WAKE_WORD_MODELS_COMMIT,
        VOICE_PE_COMMIT,
        patch_voice_pe_config,
    )

    upstream = """
file: https://github.com/esphome/home-assistant-voice-pe/raw/dev/sounds/wake.flac
external_components:
  - source:
      ref: dev
button_logic:
                      - if:
                          condition:
                            voice_assistant.is_running:
                          then:
                            - voice_assistant.stop:
                          else:
                                        - if:
                                            condition:
                                              and:
                                                - switch.is_off: master_mute_switch
                                                - not:
                                                    voice_assistant.is_running
                                            then:
                                              - script.execute:
                                                  id: play_sound
                                                  priority: true
                                                  sound_file: !lambda return id(center_button_press_sound);
                                              - delay: 300ms
                                              - voice_assistant.start:
script:
                then:
                  - micro_wake_word.disable_model: stop

i2s_audio:
micro_wake_word:
  models:
    - model: https://github.com/kahrendt/microWakeWord/releases/download/okay_nabu_20241226.3/okay_nabu.json
      id: okay_nabu
    - model: hey_jarvis
      id: hey_jarvis
    - model: hey_mycroft
      id: hey_mycroft
    - model: https://github.com/kahrendt/microWakeWord/releases/download/stop/stop.json
      id: stop
  vad:
  on_wake_word_detected:
                - if:
                    condition:
                      voice_assistant.is_running:
                    then:
                      voice_assistant.stop:
                    # Stop any other media player announcement
                    else:
select:
  - platform: template
    name: "Wake word sensitivity"
    lambda: |-
      id(okay_nabu).set_probability_cutoff(217);
voice_assistant:
  micro_wake_word: mww
  use_wake_word: false
  on_client_connected:
    - micro_wake_word.start:
  on_error:
    - if:
        condition:
          - lambda: return code == "cloud-auth-failed";
        then:
          - script.execute:
              id: play_sound
              priority: true
              sound_file: !lambda return id(error_cloud_expired);
  # When the voice assistant starts: Play a wake up sound, duck audio.
  on_start:
    - mixer_speaker.apply_ducking:
        id: media_mixing_input
        decibel_reduction: 20
        duration: 0.0s
  on_end:
    - wait_until:
        not:
          voice_assistant.is_running:
"""
    rendered = patch_voice_pe_config(upstream)

    assert f"/raw/{VOICE_PE_COMMIT}/sounds/wake.flac" in rendered
    assert f"ref: {VOICE_PE_COMMIT}" in rendered
    assert rendered.count(MICRO_WAKE_WORD_MODELS_COMMIT) == 1
    assert "okay_nabu" not in rendered
    assert "hey_jarvis" not in rendered
    assert "hey_mycroft" not in rendered
    assert "Wake word sensitivity" not in rendered
    assert f"model: {(ROOT / '.build/voice-pe/models/stop.json').resolve()}" in rendered
    assert "use_wake_word: true" in rendered
    assert "micro_wake_word: mww" not in rendered
    assert "micro_wake_word.start:" in rendered
    assert "voice_assistant.start_continuous:" in rendered
    assert "restart_streaming_wake_word" in rendered
    assert "delay: 500ms" in rendered
    assert "# Reduce media volume only after Home Assistant detects GI." in rendered
    assert "then:\n                      script.execute: restart_streaming_wake_word" in rendered
    assert (
        "on_end:\n    - wait_until:\n        condition:\n          lambda: return !id(va).is_running();"
        in rendered
    )
    assert 'code == "wake-provider-missing"' in rendered
    assert 'code == "wake-engine-missing"' in rendered
    assert rendered.endswith("improv_serial:\n")

    stop_model = ROOT / PACKAGE / "firmware/stop.tflite"
    assert sha256(stop_model.read_bytes()).hexdigest() == STOP_MODEL_SHA256


def test_model_downloads_use_checksums() -> None:
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


def test_ansible_creates_the_voice_secret_and_argocd_app() -> None:
    defaults = load_yaml("roles/apps/voice-assistant/defaults/main.yml")
    tasks = (ROOT / "roles/apps/voice-assistant/tasks/main.yml").read_text()
    enabled_tasks = (ROOT / "roles/apps/voice-assistant/tasks/enabled.yml").read_text()
    disabled_tasks = (ROOT / "roles/apps/voice-assistant/tasks/disabled.yml").read_text()
    playbook = load_yaml("playbooks/deploy-argocd-apps.yml")

    assert defaults["voice_assistant_target_revision"] == "HEAD"
    assert defaults["voice_assistant_enabled"] is True
    assert "VOICE_ASSISTANT_HA_TOKEN" in defaults["voice_assistant_ha_token"]
    assert "VOICE_ASSISTANT_GI_MODEL_PATH" in defaults["voice_assistant_gi_model_path"]
    assert defaults["voice_assistant_gi_model_configmap_name"] == DEPLOYED_GI_MODEL_CONFIGMAP
    assert defaults["voice_assistant_gi_model_sha256"] == DEPLOYED_GI_MODEL_SHA256
    assert re.fullmatch(r"[0-9a-f]{64}", defaults["voice_assistant_gi_model_sha256"])
    assert defaults["voice_assistant_gi_model_retired_configmaps"] == []
    assert "enabled.yml" in tasks
    assert "disabled.yml" in tasks
    assert "kubernetes.core.k8s_info" in enabled_tasks
    assert "voice-assistant-ha-token" in enabled_tasks
    assert "voice_assistant_gi_model_path" in enabled_tasks
    assert "ansible.builtin.slurp" in enabled_tasks
    assert "binaryData" in enabled_tasks
    assert "immutable: true" in enabled_tasks
    assert "voice.soyspray.vip/model-sha256" in enabled_tasks
    assert "base64.b64decode" in enabled_tasks
    assert "voice_assistant_gi_model_live_checksum.stdout" in enabled_tasks
    assert "voice_assistant_gi_model_retired_configmaps" in enabled_tasks
    assert enabled_tasks.index("Do not delete the selected GI model") < enabled_tasks.index(
        "Apply the Home Assistant voice app"
    )
    assert "no_log: true" in enabled_tasks
    assert "voice_assistant_target_revision" in enabled_tasks
    assert "voice-assistant-application.yaml" in enabled_tasks
    assert "Stop automated sync before removal" in disabled_tasks
    assert "state: absent" in disabled_tasks
    assert "voice-assistant" in disabled_tasks
    assert "voice_assistant_gi_model_configmap_name" in disabled_tasks
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
    for target in (
        "voice-pe-render:",
        "voice-pe-check:",
        "voice-pe-compile:",
        "voice-pe-upload:",
    ):
        assert target in makefile
    assert "esphome==2025.5.1" in makefile
    assert "scripts/render_gi_voice_pe.py" in makefile
    assert "voice-pe-upload: voice-pe-compile" in makefile
    assert "\t$(MAKE) go\n" in makefile


def test_home_assistant_has_local_voice_settings() -> None:
    home_assistant = "playbooks/argocd/applications/home-automation/home-assistant"
    bootstrap = load_yaml(f"{home_assistant}/configmap-bootstrap.yaml")["data"][
        "configuration.yaml"
    ]
    service = load_yaml(f"{home_assistant}/service.yaml")["spec"]

    assert (
        f"internal_url: http://{service['loadBalancerIP']}:{service['ports'][0]['port']}"
        in bootstrap
    )
    deployment = load_yaml(
        "playbooks/argocd/applications/home-automation/home-assistant/deployment.yaml"
    )
    assert deployment["spec"]["template"]["metadata"]["annotations"] == {
        "soyspray.vip/bootstrap-config-revision": "2026-08-15-voice-only-lights"
    }
    configmap = load_yaml(
        "playbooks/argocd/applications/home-automation/home-assistant/configmap-bootstrap.yaml"
    )
    automations = yaml.safe_load(configmap["data"]["automations.yaml"])
    by_id = {automation["id"]: automation for automation in automations}

    for automation_id in (
        "tapo_motion_relax_lights_after_sunset",
        "tapo_motion_relax_lights_off_after_midnight",
        "tapo_motion_relax_lights_off_after_clear",
    ):
        assert by_id[automation_id]["initial_state"] is False

    for automation_id in (
        "door_open_10min",
        "tapo_l530_relax_on",
        "tapo_bedtime_motion_guard_on",
        "tapo_bedtime_motion_guard_clear",
    ):
        assert by_id[automation_id].get("initial_state", True) is True
