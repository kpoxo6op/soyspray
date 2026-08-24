#!/usr/bin/env python3
"""Build a Voice PE config that sends wake detection to Home Assistant."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import shutil
import urllib.request

VOICE_PE_VERSION = "25.5.2"
VOICE_PE_COMMIT = "8178e25aceb4f08b0f2e932dc902974dc7f1632a"
VOICE_PE_URL = (
    "https://raw.githubusercontent.com/esphome/home-assistant-voice-pe/"
    f"{VOICE_PE_COMMIT}/home-assistant-voice.yaml"
)
VOICE_PE_SHA256 = "ccd3188da67597ddf461b3c076b049c2c89e3c64e7219a82048de4c08e00ec31"
MICRO_WAKE_WORD_MODELS_COMMIT = "05b65922cc433c9df13e98e32a7fe520758c837e"
ROOT = pathlib.Path(__file__).resolve().parents[1]
FIRMWARE_ASSET_DIR = ROOT / "playbooks/argocd/applications/home-automation/voice-assistant/firmware"
FIRMWARE_ASSETS = {
    "stop.json": "bd13aeb1b83852649dc4fb6135cb160ff68716d14612b06f6a405342c57447aa",
    "stop.tflite": "b5a18c4ad681a89950dfade31011e1631bdcb333e93c84519a1a63ff4f071146",
}


def replace_once(source: str, old: str, new: str) -> str:
    """Replace one source block. Stop if it is missing or repeated."""
    count = source.count(old)
    if count != 1:
        raise ValueError(f"Source block appears {count} times; expected once: {old!r}")
    return source.replace(old, new)


def patch_voice_pe_config(source: str, stop_manifest_path: pathlib.Path | None = None) -> str:
    """Use fixed source versions and let Home Assistant detect GI."""
    if stop_manifest_path is None:
        stop_manifest_path = ROOT / ".build/voice-pe/models/stop.json"
    stop_manifest = stop_manifest_path.resolve().as_posix()
    source = source.replace(
        "https://github.com/esphome/home-assistant-voice-pe/raw/dev/",
        f"https://github.com/esphome/home-assistant-voice-pe/raw/{VOICE_PE_COMMIT}/",
    )
    source = replace_once(source, "      ref: dev", f"      ref: {VOICE_PE_COMMIT}")
    models_base = (
        "https://raw.githubusercontent.com/esphome/micro-wake-word-models/"
        f"{MICRO_WAKE_WORD_MODELS_COMMIT}/models/v2"
    )
    source = replace_once(
        source,
        "    - model: https://github.com/kahrendt/microWakeWord/releases/download/okay_nabu_20241226.3/okay_nabu.json\n"
        "      id: okay_nabu\n"
        "    - model: hey_jarvis\n"
        "      id: hey_jarvis\n"
        "    - model: hey_mycroft\n"
        "      id: hey_mycroft\n",
        "",
    )
    source = replace_once(
        source,
        "    - model: https://github.com/kahrendt/microWakeWord/releases/download/stop/stop.json",
        f"    - model: {stop_manifest}",
    )
    source = replace_once(source, "  vad:\n", f"  vad:\n    model: {models_base}/vad.json\n")
    source = replace_once(
        source,
        "                - if:\n"
        "                    condition:\n"
        "                      voice_assistant.is_running:\n"
        "                    then:\n"
        "                      voice_assistant.stop:\n"
        "                    # Stop any other media player announcement\n"
        "                    else:\n",
        "                - if:\n"
        "                    condition:\n"
        "                      voice_assistant.is_running:\n"
        "                    then:\n"
        "                      script.execute: restart_streaming_wake_word\n"
        "                    # Stop any other media player announcement\n"
        "                    else:\n",
    )
    source, sensitivity_count = re.subn(
        r'\nselect:\n  - platform: template\n    name: "Wake word sensitivity"\n.*?(?=\nvoice_assistant:\n)',
        "\n",
        source,
        flags=re.DOTALL,
    )
    if sensitivity_count != 1:
        raise ValueError(
            f"Voice PE config has {sensitivity_count} wake-word sensitivity selectors; expected one"
        )
    source = replace_once(source, "  micro_wake_word: mww\n", "")
    source = replace_once(source, "  use_wake_word: false", "  use_wake_word: true")
    source = replace_once(
        source,
        "    - micro_wake_word.start:",
        "    - micro_wake_word.start:\n    - voice_assistant.start_continuous:",
    )
    source = replace_once(
        source,
        "                      - if:\n"
        "                          condition:\n"
        "                            voice_assistant.is_running:\n"
        "                          then:\n"
        "                            - voice_assistant.stop:\n"
        "                          else:\n",
        "                      - if:\n"
        "                          condition:\n"
        "                            lambda: return id(voice_assistant_phase) > ${voice_assist_idle_phase_id};\n"
        "                          then:\n"
        "                            - script.execute: restart_streaming_wake_word\n"
        "                          else:\n",
    )
    source = replace_once(
        source,
        "                                        - if:\n"
        "                                            condition:\n"
        "                                              and:\n"
        "                                                - switch.is_off: master_mute_switch\n"
        "                                                - not:\n"
        "                                                    voice_assistant.is_running\n"
        "                                            then:\n"
        "                                              - script.execute:\n"
        "                                                  id: play_sound\n"
        "                                                  priority: true\n"
        "                                                  sound_file: !lambda return id(center_button_press_sound);\n"
        "                                              - delay: 300ms\n"
        "                                              - voice_assistant.start:\n",
        "                                        - if:\n"
        "                                            condition:\n"
        "                                              switch.is_off: master_mute_switch\n"
        "                                            then:\n"
        "                                              - script.execute: restart_streaming_wake_word\n",
    )
    source = replace_once(
        source,
        "                then:\n"
        "                  - micro_wake_word.disable_model: stop\n"
        "\n"
        "i2s_audio:\n",
        "                then:\n"
        "                  - micro_wake_word.disable_model: stop\n"
        "\n"
        "  - id: restart_streaming_wake_word\n"
        "    mode: restart\n"
        "    then:\n"
        "      - voice_assistant.stop:\n"
        "      - wait_until:\n"
        "          condition:\n"
        "            lambda: return !id(va).is_running();\n"
        "      - delay: 500ms\n"
        "      - lambda: id(va).set_use_wake_word(true);\n"
        "      - voice_assistant.start_continuous:\n"
        "      - lambda: id(voice_assistant_phase) = ${voice_assist_idle_phase_id};\n"
        "      - script.execute: control_leds\n"
        "\n"
        "i2s_audio:\n",
    )
    source = replace_once(
        source,
        "  on_end:\n    - wait_until:\n        not:\n          voice_assistant.is_running:\n",
        "  on_end:\n"
        "    - wait_until:\n"
        "        condition:\n"
        "          lambda: return !id(va).is_running();\n",
    )
    source = replace_once(
        source,
        "              sound_file: !lambda return id(error_cloud_expired);\n"
        "  # When the voice assistant starts: Play a wake up sound, duck audio.\n",
        "              sound_file: !lambda return id(error_cloud_expired);\n"
        "    - if:\n"
        "        condition:\n"
        "          or:\n"
        '            - lambda: return code == "wake-provider-missing";\n'
        '            - lambda: return code == "wake-engine-missing";\n'
        "        then:\n"
        "          - delay: 5s\n"
        "          - script.execute: restart_streaming_wake_word\n"
        "  # When the voice assistant starts: Play a wake up sound, duck audio.\n",
    )
    source = replace_once(
        source,
        "  # When the voice assistant starts: Play a wake up sound, duck audio.\n  on_start:\n",
        "  # Reduce media volume only after Home Assistant detects GI.\n  on_wake_word_detected:\n",
    )
    return (
        source.rstrip()
        + "\n\n# Allow Wi-Fi setup without storing credentials in this file.\nimprov_serial:\n"
    )


def stage_firmware_assets(output: pathlib.Path) -> None:
    """Copy the checked firmware files next to the generated config."""
    target_dir = output.parent / "models"
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, expected_sha256 in FIRMWARE_ASSETS.items():
        source = FIRMWARE_ASSET_DIR / name
        actual_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"Firmware file {name} has SHA-256 {actual_sha256}; expected {expected_sha256}"
            )
        shutil.copyfile(source, target_dir / name)


def download_upstream() -> str:
    """Download the expected Voice PE config and check its checksum."""
    with urllib.request.urlopen(VOICE_PE_URL, timeout=30) as response:  # noqa: S310
        payload = response.read()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != VOICE_PE_SHA256:
        raise ValueError(f"Voice PE config has SHA-256 {actual}; expected {VOICE_PE_SHA256}")
    return payload.decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path(".build/voice-pe/gi-voice-pe.yaml"),
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    stage_firmware_assets(args.output)
    rendered = patch_voice_pe_config(download_upstream(), args.output.parent / "models/stop.json")
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
