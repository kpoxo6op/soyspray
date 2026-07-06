#!/usr/bin/env python3
"""Regenerate the goal-003 API catalog index from metadata."""

from __future__ import annotations

import yaml

try:
    from scripts.synthetic_bank_config import APIS, ROOT
except ModuleNotFoundError:
    from synthetic_bank_config import APIS, ROOT


def main() -> int:
    rows = []
    for api in APIS:
        ownership = yaml.safe_load((ROOT / "apis/synthetic-bank" / api.key / "ownership.yaml").read_text(encoding="utf-8"))
        rows.append(
            f"| {api.title} | `{api.key}` | {ownership['owning_team']} | `{ownership['tenant_namespace']}` | "
            f"{ownership['exposure']} | `{ownership['route_host']}` | `{ownership['route_paths'][0]}` | "
            f"`{ownership['auth_profile']}` | `{ownership['future_auth_goal']}` |"
        )
    content = f"""# Synthetic API Catalog

| API | Domain | Owner | Namespace | Exposure | Host | Path | Temporary auth posture | Future auth goal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}

All APIs are synthetic sandbox APIs. Authentication, authorization, and rate limiting are deferred to goal 004.
"""
    (ROOT / "docs/api-catalog/index.md").write_text(content, encoding="utf-8")
    print("docs/api-catalog/index.md generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
