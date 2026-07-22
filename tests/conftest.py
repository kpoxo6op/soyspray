from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text())


def load_all(path: str) -> list[dict]:
    return [item for item in yaml.safe_load_all((ROOT / path).read_text()) if item]
