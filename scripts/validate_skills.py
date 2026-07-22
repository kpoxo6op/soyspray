#!/usr/bin/env python3
"""Validate project-local Agent Skills without external tooling."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / ".agents" / "skills"


def validate_skill(directory: Path) -> list[str]:
    errors = []
    path = directory / "SKILL.md"
    if not path.is_file():
        return [f"{directory.relative_to(ROOT)}: missing SKILL.md"]

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return [f"{path.relative_to(ROOT)}: malformed YAML frontmatter"]

    frontmatter, body = text[4:].split("\n---\n", 1)
    try:
        metadata = yaml.safe_load(frontmatter)
    except yaml.YAMLError as exc:
        return [f"{path.relative_to(ROOT)}: invalid frontmatter: {exc}"]

    if not isinstance(metadata, dict):
        return [f"{path.relative_to(ROOT)}: frontmatter must be a mapping"]
    if metadata.get("name") != directory.name:
        errors.append(f"{path.relative_to(ROOT)}: name must match directory")
    if (
        not isinstance(metadata.get("description"), str)
        or len(metadata["description"].strip()) < 20
    ):
        errors.append(f"{path.relative_to(ROOT)}: description is missing or too short")
    if not body.strip():
        errors.append(f"{path.relative_to(ROOT)}: instructions are empty")
    if "TODO" in text:
        errors.append(f"{path.relative_to(ROOT)}: unresolved TODO")
    return errors


def main() -> int:
    directories = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())
    errors = [error for directory in directories for error in validate_skill(directory)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated {len(directories)} project skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
