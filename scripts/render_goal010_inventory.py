#!/usr/bin/env python3
"""Render the Goal010 expected runtime inventory deterministically."""

from __future__ import annotations

import sys

import yaml

try:
    from scripts.goal010_drift_guard_config import RENDERED_INVENTORY_PATH, load_inventory
except ModuleNotFoundError:
    from goal010_drift_guard_config import RENDERED_INVENTORY_PATH, load_inventory


def rendered_inventory_yaml() -> str:
    return yaml.safe_dump(load_inventory(), sort_keys=True)


def main() -> int:
    rendered = rendered_inventory_yaml()
    RENDERED_INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    RENDERED_INVENTORY_PATH.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
