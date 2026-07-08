#!/usr/bin/env python3
"""Render the goal-003 tenant Namespace prereqs used by synthetic APIs."""

from __future__ import annotations

import sys

try:
    from scripts.synthetic_bank_config import APIS, ROOT
except ModuleNotFoundError:
    from synthetic_bank_config import APIS, ROOT


def main() -> int:
    rendered: list[str] = []
    seen: set[str] = set()

    for api in APIS:
        if api.namespace in seen:
            continue
        seen.add(api.namespace)

        path = ROOT / "platform/namespaces" / f"{api.namespace}.yaml"
        if not path.is_file():
            print(f"missing tenant namespace manifest: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1

        content = path.read_text(encoding="utf-8").strip()
        if content:
            rendered.append(f"# Source: {path.relative_to(ROOT)}\n{content}")

    print("\n---\n".join(rendered))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
