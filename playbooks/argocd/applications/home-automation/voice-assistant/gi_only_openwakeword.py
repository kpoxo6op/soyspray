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
    """Remove all built-in wake models and every default-model fallback."""
    actual_sha256 = hashlib.sha256(source.encode()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(f"handler.py checksum is {actual_sha256}, expected {expected_sha256}")

    source = replace_once(
        source,
        "from pyopen_wakeword import Model, OpenWakeWord, OpenWakeWordFeatures",
        "from pyopen_wakeword import OpenWakeWord, OpenWakeWordFeatures",
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

    forbidden = ("OKAY_NABU", "Model(ww_name)", "for model in Model:")
    for value in forbidden:
        if value in source:
            raise ValueError(f"GI-only handler still contains {value!r}")
    if "for custom_model in self.state.custom_models" not in source:
        raise ValueError("GI-only handler no longer advertises custom models")
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
