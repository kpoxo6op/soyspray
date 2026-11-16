#!/usr/bin/env python3
"""Parse repository YAML files without requiring a cluster."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
YAML_ROOTS = [
    ".github",
    "apps",
    "argocd",
    "inventory",
    "playbooks",
    "roles",
    "tests",
]
SKIPPED_DIRECTORIES = {"node_modules"}


class RepositoryLoader(yaml.SafeLoader):
    """Safe loading that also rejects a mapping key written twice.

    YAML parsers keep the last duplicate and silently drop the others, so a
    repeated top-level key in a values file discards settings without a word.
    """

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = self.construct_object(key_node, deep=True)
            try:
                duplicate = key in seen
            except TypeError:
                continue
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", key_node.start_mark
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def tagged(loader, tag, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


RepositoryLoader.add_multi_constructor("!", tagged)


def load(text: str) -> list:
    return list(yaml.load_all(text, Loader=RepositoryLoader))


def yaml_files() -> list[Path]:
    paths: list[Path] = []
    for root in YAML_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        paths.extend(
            path
            for path in base.rglob("*")
            if path.suffix in {".yaml", ".yml"} and not SKIPPED_DIRECTORIES.intersection(path.parts)
        )
    return sorted(set(paths))


def main() -> int:
    errors: list[str] = []
    for path in yaml_files():
        try:
            load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    if errors:
        print("YAML validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"YAML validation passed for {len(yaml_files())} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
