#!/usr/bin/env python3
"""Validate the synthetic API contracts without network access."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apis/synthetic-bank"
REAL_DATA_PATTERNS = (
    re.compile(r"\b\d{12,19}\b"),
    re.compile(r"@[a-z0-9.-]+\.[a-z]{2,}", re.I),
    re.compile(r"\b(?:\+?64|0)2\d{7,9}\b"),
)


def main() -> int:
    errors: list[str] = []
    specs = sorted(API_ROOT.glob("*/openapi.yaml"))
    if len(specs) != 6:
        errors.append(f"expected 6 API contracts, found {len(specs)}")

    for path in specs:
        spec = yaml.safe_load(path.read_text())
        api = path.parent.name
        text = path.read_text()
        if not str(spec.get("openapi", "")).startswith("3."):
            errors.append(f"{api}: OpenAPI 3.x is required")
        for field in ("title", "version", "description"):
            if not spec.get("info", {}).get(field):
                errors.append(f"{api}: info.{field} is required")
        if spec.get("x-banklab-api-domain") != api:
            errors.append(f"{api}: x-banklab-api-domain must match the directory")
        if spec.get("x-banklab-data-classification") != "synthetic":
            errors.append(f"{api}: data classification must be synthetic")
        if spec.get("x-banklab-auth-profile") != "kong-oss-auth":
            errors.append(f"{api}: the Kong OSS auth profile is required")
        for route, methods in spec.get("paths", {}).items():
            for method, operation in methods.items():
                if method == "parameters":
                    continue
                if not operation.get("operationId"):
                    errors.append(f"{api}: {method.upper()} {route} needs an operationId")
                if not operation.get("responses"):
                    errors.append(f"{api}: {method.upper()} {route} needs responses")
        if "404" not in text:
            errors.append(f"{api}: a 404 response is required")
        if any(pattern.search(text) for pattern in REAL_DATA_PATTERNS):
            errors.append(f"{api}: contract contains real-looking personal data")

    if errors:
        print("OpenAPI validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OpenAPI validation passed for {len(specs)} APIs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
