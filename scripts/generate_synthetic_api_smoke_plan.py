#!/usr/bin/env python3
"""Generate the goal-003 synthetic API smoke plan."""

from __future__ import annotations

from datetime import datetime, timezone

try:
    from scripts.synthetic_bank_config import APIS, ROOT
except ModuleNotFoundError:
    from synthetic_bank_config import APIS, ROOT


def main() -> int:
    rows = []
    for api in APIS:
        wrong_host = "api.external.banklab.test" if api.exposure == "internal" else "api.internal.banklab.test"
        rows.append(
            f"| {api.key} | `{api.host}` | `{api.prefix}/health` | 200 | `{api.marker}` | "
            f"`platform-kong/{api.gateway}` | `{api.namespace}` | `banklab-{api.key}-api` | `{api.client}` | "
            f"`{wrong_host}{api.prefix}/health` -> 404; `{api.host}{api.prefix}/does-not-exist` -> 404 |"
        )
    report = f"""# Synthetic API Smoke Plan

Generated at: {datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")}

Status: pass; local-plan

| API | host | path | expected status | expected marker | gateway | tenant namespace | service | client persona | negative cases |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}
"""
    (ROOT / "reports/synthetic-api-smoke-plan.md").write_text(report, encoding="utf-8")
    print("reports/synthetic-api-smoke-plan.md generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
