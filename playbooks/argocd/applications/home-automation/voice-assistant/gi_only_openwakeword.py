#!/usr/bin/env python3
"""Create a fail-closed GI-only copy of the pinned Wyoming package."""

from __future__ import annotations

import hashlib
import pathlib
import shutil
import sys

HANDLER_SHA256 = "ec7f2d79b9c9cb3bf426b285b2ef5e6ca1224aee8cbd9e31bc2d5b5a37235a95"


def replace_once(source: str, old: str, new: str) -> str:
    """Replace one exact upstream fragment and reject source drift."""
    count = source.count(old)
    if count != 1:
        raise ValueError(f"expected one patch fragment, found {count}: {old[:80]!r}")
    return source.replace(old, new)


def patch_handler(source: str, expected_sha256: str = HANDLER_SHA256) -> str:
    """Keep GI fail-closed and require voiced, consecutive high wake scores."""
    actual_sha256 = hashlib.sha256(source.encode()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(f"handler.py checksum is {actual_sha256}, expected {expected_sha256}")

    source = replace_once(
        source,
        "from pyopen_wakeword import Model, OpenWakeWord, OpenWakeWordFeatures",
        "from pyopen_wakeword import OpenWakeWord, OpenWakeWordFeatures",
    )
    source = replace_once(
        source,
        """import logging
import time
from dataclasses import dataclass""",
        """import logging
import os
import time
import wave
from array import array
from dataclasses import dataclass""",
    )
    source = replace_once(
        source,
        "_LOGGER = logging.getLogger(__name__)",
        """_LOGGER = logging.getLogger(__name__)

CAPTURE_PATH = os.environ.get("GI_CAPTURE_PATH")
try:
    CAPTURE_EXPIRES_AT = float(os.environ.get("GI_CAPTURE_EXPIRES_AT") or "0")
except ValueError:
    CAPTURE_EXPIRES_AT = 0
CAPTURE_MAX_BYTES = 4 * 16000 * 2
_capture_attempted = bool(CAPTURE_PATH and os.path.exists(CAPTURE_PATH))


def _gi_capture_enabled() -> bool:
    return bool(
        CAPTURE_PATH
        and time.time() < CAPTURE_EXPIRES_AT
        and not _capture_attempted
    )


def _gi_capture_failed(error: Exception) -> None:
    global _capture_attempted
    _capture_attempted = True
    _LOGGER.warning(
        "GI_CAPTURE_FAILED path=%s error=%s", CAPTURE_PATH, type(error).__name__
    )


def _save_gi_capture_once(audio: bytearray) -> None:
    global _capture_attempted
    if not _gi_capture_enabled():
        audio.clear()
        return

    _capture_attempted = True
    try:
        with open(
            CAPTURE_PATH,
            "xb",
            opener=lambda path, _: os.open(
                path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            ),
        ) as capture_file:
            with wave.open(capture_file, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(audio)
        _LOGGER.info("GI_CAPTURE_SAVED path=%s bytes=%s", CAPTURE_PATH, len(audio))
    except Exception as error:
        _gi_capture_failed(error)
    finally:
        audio.clear()""",
    )
    source = replace_once(source, "\nDEFAULT_MODEL = Model.OKAY_NABU\n", "")
    source = replace_once(
        source,
        """            if detect.names:
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
""",
        """            if detect.names:
                for ww_name in detect.names:
                    if ww_name in self.state.custom_models:
                        ww_names.add(ww_name)
""",
    )
    source = replace_once(
        source,
        """                model_path = self.state.custom_models.get(ww_name)
                if model_path is not None:
                    oww_model = OpenWakeWord.from_model(model_path)
                else:
                    try:
                        model = Model(ww_name)
                        oww_model = OpenWakeWord.from_builtin(model)
                    except ValueError:
                        pass
""",
        """                model_path = self.state.custom_models.get(ww_name)
                if model_path is not None:
                    oww_model = OpenWakeWord.from_model(model_path)
""",
    )
    source = replace_once(
        source,
        """        for model in Model:
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

""",
        "",
    )
    source = replace_once(
        source,
        """        self.audio_timestamp = 0

        _LOGGER.debug("Client connected: %s", self.client_id)
""",
        """        self.audio_timestamp = 0
        self.voice_grace_ms = 0
        self.last_gate_peak = 0
        self.capture_buffer = bytearray()

        _LOGGER.debug("Client connected: %s", self.client_id)
""",
    )
    source = replace_once(
        source,
        """            self.audio_timestamp = 0
            self.oww_features.reset()
""",
        """            self.audio_timestamp = 0
            self.voice_grace_ms = 0
            self.last_gate_peak = 0
            self.capture_buffer.clear()
            self.oww_features.reset()
""",
    )
    source = replace_once(
        source,
        """        elif AudioChunk.is_type(event.type):
            chunk = self.converter.convert(AudioChunk.from_event(event))
            for features in self.oww_features.process_streaming(chunk.audio):
""",
        """        elif AudioChunk.is_type(event.type):
            chunk = self.converter.convert(AudioChunk.from_event(event))
            if _gi_capture_enabled():
                try:
                    self.capture_buffer.extend(chunk.audio)
                    if len(self.capture_buffer) > CAPTURE_MAX_BYTES:
                        del self.capture_buffer[:-CAPTURE_MAX_BYTES]
                except Exception as error:
                    _gi_capture_failed(error)
                    self.capture_buffer.clear()
            else:
                self.capture_buffer.clear()

            samples = array("h")
            samples.frombytes(chunk.audio)
            chunk_peak = max((abs(sample) for sample in samples), default=0)
            if chunk_peak >= 12:
                self.voice_grace_ms = 2000
                self.last_gate_peak = chunk_peak
            else:
                self.voice_grace_ms = max(0, self.voice_grace_ms - chunk.milliseconds)

            for features in self.oww_features.process_streaming(chunk.audio):
""",
    )
    source = replace_once(
        source,
        """                        if prob <= self.threshold:
                            continue

                        detector.triggers_left -= 1
""",
        """                        if prob <= self.threshold:
                            detector.triggers_left = self.trigger_level
                            continue

                        gate_open = self.voice_grace_ms > 0
                        if gate_open:
                            detector.triggers_left -= 1
                        else:
                            detector.triggers_left = self.trigger_level

                        _LOGGER.info(
                            "GI_CANDIDATE client_id=%s model=%s audio_timestamp=%s "
                            "score=%.6f chunk_peak=%s last_gate_peak=%s "
                            "remaining_grace_ms=%s gate_open=%s triggers_left=%s",
                            self.client_id,
                            detector.id,
                            self.audio_timestamp,
                            prob,
                            chunk_peak,
                            self.last_gate_peak,
                            self.voice_grace_ms,
                            gate_open,
                            detector.triggers_left,
                        )
                        if not gate_open:
                            continue
""",
    )

    source = replace_once(
        source,
        """                        _LOGGER.debug(
                            "Detected %s at %s", detector.id, self.audio_timestamp
                        )
""",
        """                        _save_gi_capture_once(self.capture_buffer)
                        _LOGGER.info(
                            "GI_DETECTION client_id=%s model=%s audio_timestamp=%s "
                            "score=%.6f chunk_peak=%s last_gate_peak=%s "
                            "remaining_grace_ms=%s gate_open=%s triggers_left=%s",
                            self.client_id,
                            detector.id,
                            self.audio_timestamp,
                            prob,
                            chunk_peak,
                            self.last_gate_peak,
                            self.voice_grace_ms,
                            gate_open,
                            detector.triggers_left,
                        )
                        _LOGGER.debug(
                            "Detected %s at %s", detector.id, self.audio_timestamp
                        )
""",
    )

    forbidden = ("OKAY_NABU", "Model(ww_name)", "for model in Model:")
    for value in forbidden:
        if value in source:
            raise ValueError(f"GI-only handler still contains {value!r}")
    if "for custom_model in self.state.custom_models" not in source:
        raise ValueError("GI-only handler no longer advertises custom models")
    if "chunk_peak = max((abs(sample) for sample in samples), default=0)" not in source:
        raise ValueError("GI-only handler no longer measures the current chunk peak once")
    if "if chunk_peak >= 12:" not in source:
        raise ValueError("GI-only handler no longer requires voiced audio")
    return source


def main() -> None:
    source_package = pathlib.Path("/usr/src/wyoming_openwakeword")
    target_package = pathlib.Path("/patched/wyoming_openwakeword")
    if len(sys.argv) == 3:
        source_package = pathlib.Path(sys.argv[1])
        target_package = pathlib.Path(sys.argv[2])

    shutil.copytree(source_package, target_package)
    handler_path = target_package / "handler.py"
    handler_path.write_text(patch_handler(handler_path.read_text(encoding="utf-8")))
    print(target_package)


if __name__ == "__main__":
    main()
