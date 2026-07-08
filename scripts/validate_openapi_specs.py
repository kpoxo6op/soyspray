#!/usr/bin/env python3
"""Validate goal-003 OpenAPI specs without network access."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.synthetic_bank_config import APIS, AUTH_PROFILE, ROOT
except ModuleNotFoundError:
    from synthetic_bank_config import APIS, AUTH_PROFILE, ROOT


REAL_DATA_PATTERNS = (
    re.compile(r"\b\d{12,19}\b"),
    re.compile(r"@[a-z0-9.-]+\.[a-z]{2,}", re.I),
    re.compile(r"\b(?:\+?64|0)2\d{7,9}\b"),
)


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def validate() -> list[str]:
    errors: list[str] = []
    for api in APIS:
        path = ROOT / "apis/synthetic-bank" / api.key / "openapi.yaml"
        require(path.is_file(), errors, f"missing OpenAPI spec: {path.relative_to(ROOT)}")
        if not path.is_file():
            continue
        spec = load_yaml(path)
        text = path.read_text(encoding="utf-8")
        require(str(spec.get("openapi", "")).startswith("3."), errors, f"{api.key} must use OpenAPI 3.x")
        require(spec.get("info", {}).get("title"), errors, f"{api.key} missing info.title")
        require(spec.get("info", {}).get("version"), errors, f"{api.key} missing info.version")
        require(spec.get("info", {}).get("description"), errors, f"{api.key} missing info.description")
        require(spec.get("servers"), errors, f"{api.key} missing servers")
        require(spec.get("tags"), errors, f"{api.key} missing tags")
        require(spec.get("x-banklab-api-domain") == api.key, errors, f"{api.key} domain extension mismatch")
        require(spec.get("x-banklab-lifecycle") == "sandbox", errors, f"{api.key} lifecycle extension mismatch")
        require(spec.get("x-banklab-data-classification") == "synthetic", errors, f"{api.key} classification extension mismatch")
        require(spec.get("x-banklab-auth-profile") == AUTH_PROFILE, errors, f"{api.key} auth extension mismatch")
        paths = spec.get("paths", {})
        require(f"{api.prefix}/health" in paths, errors, f"{api.key} missing health path")
        for route, methods in paths.items():
            require(route.startswith(api.prefix), errors, f"{api.key} route outside prefix: {route}")
            for method, operation in methods.items():
                require(operation.get("operationId"), errors, f"{api.key} {method.upper()} {route} missing operationId")
                require(operation.get("responses"), errors, f"{api.key} {method.upper()} {route} missing responses")
        require("404" in text, errors, f"{api.key} must include an error response example")
        for pattern in REAL_DATA_PATTERNS:
            require(not pattern.search(text), errors, f"{api.key} appears to include real-looking data: {pattern.pattern}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("OpenAPI validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OpenAPI validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
