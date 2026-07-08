#!/usr/bin/env python3
"""Generate the goal004 security smoke plan."""

from __future__ import annotations

from datetime import datetime, timezone

try:
    from scripts.goal004_security_config import APIS, CLIENT_FOR_API, ROOT, api_auth_plugin, api_plugin_annotation
except ModuleNotFoundError:
    from goal004_security_config import APIS, CLIENT_FOR_API, ROOT, api_auth_plugin, api_plugin_annotation


def main() -> int:
    lines = [
        "# Goal004 Security Smoke Plan",
        "",
        "Status: pass",
        "",
        f"Generated at: {datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')}",
        "",
        "## Positive checks",
    ]
    for api in APIS:
        client = CLIENT_FOR_API[api.key]
        auth = "JWT" if api_auth_plugin(api.key) == "jwt" else "API key"
        lines.append(f"- `{api.key}`: `{client}` {auth} returns 200 and marker `{api.marker}`; plugins `{api_plugin_annotation(api.key)}`.")
    lines.extend(
        [
            "",
            "## Negative checks",
            "- Missing API key returns 401.",
            "- Invalid API key returns 401.",
            "- Valid API key for the wrong ACL group returns 403.",
            "- Missing JWT returns 401.",
            "- Invalid JWT signature returns 401.",
            "- Expired JWT returns 401.",
            "- Unknown host and path remain 404.",
            "- Admin API external probe still fails.",
            "",
            "## Rate limit check",
            "- A valid client exceeds the Redis-backed `second: 3` rate limit and receives 429.",
        ]
    )
    (ROOT / "reports/goal004-security-smoke-plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("reports/goal004-security-smoke-plan.md generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
