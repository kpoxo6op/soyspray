"""Compile a verified successful DeepSeek interpretation into an exact local sentence.

Input is a private GI Everyday audit record, augmented with verified=true only
after observing the intended real device action. Output is reviewed and shipped
through the normal source-image and promotion PRs; this never edits live HA.
"""

import argparse
import json
import re
from pathlib import Path

import yaml
from custom_components.gi_voice.control import ACTIONS, BLOCKED


def compile_record(record, document):
    if record.get("route") != "deepseek" or record.get("verified") is not True:
        raise ValueError("A verified successful DeepSeek action is required")
    if (
        record.get("intent") != "GiControl"
        or record.get("speech", {}).get("plain", {}).get("speech") != "Done."
    ):
        raise ValueError("The intent did not report successful execution")
    phrase = record["text"].strip().rstrip(".!?")
    if (
        not 1 <= len(phrase) <= 160
        or BLOCKED.search(phrase)
        or re.search(r"[{}\[\]()<>|;\n\r]", phrase)
    ):
        raise ValueError("Unsafe or non-literal phrase")
    slots = {
        k: v for k, v in record["slots"].items() if k in {"command", "target_name", "value", "area"}
    }
    if slots.get("command") not in ACTIONS:
        raise ValueError("Unsupported action")
    data = document.setdefault("intents", {}).setdefault("GiControl", {}).setdefault("data", [])
    for row in data:
        if phrase in row["sentences"]:
            if row["slots"] != slots:
                raise ValueError("Conflicting learned action")
            return document
    data.append({"sentences": [phrase], "slots": slots})
    document["language"] = "en"
    return document


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    document = yaml.safe_load(args.output.read_text()) if args.output.exists() else {}
    document = compile_record(json.loads(args.receipt.read_text()), document)
    args.output.write_text(yaml.safe_dump(document, sort_keys=False, allow_unicode=True))
