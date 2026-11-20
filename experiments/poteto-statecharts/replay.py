#!/usr/bin/env python3
"""Replay publication interruptions against real code using disposable files only."""

import argparse
import importlib.util
import json
import multiprocessing
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def crash_install(evidence, archive, volume, identity, boundary):
    chmod, rename = Path.chmod, Path.rename

    def stop_after_marker(path, mode, *args, **kwargs):
        result = chmod(path, mode, *args, **kwargs)
        if path.name == "COMPLETE":
            os._exit(77)
        return result

    def stop_after_publish(path, target):
        result = rename(path, target)
        os._exit(77)
        return result

    method, replacement = (
        ("chmod", stop_after_marker) if boundary == "marker" else ("rename", stop_after_publish)
    )
    with patch.object(Path, method, replacement):
        evidence.install(archive, volume, identity["packHash"], identity["archiveHash"])


def intake_replays(repo):
    evidence = load("evidence", repo / "apps/agents/evidence.py")
    packer = load("pack", repo / "apps/agents/pack.py")
    results = []
    for boundary in ("marker", "rename"):
        with tempfile.TemporaryDirectory(prefix="poteto-replay-") as temp:
            root = Path(temp)
            source, volume, archive = root / "source", root / "volume", root / "pack.tar"
            source.mkdir()
            volume.mkdir()
            (source / "sample.txt").write_text("synthetic fixture version one\n")
            old = packer.pack(source, archive)
            evidence.install(archive, volume, old["packHash"], old["archiveHash"])
            (source / "sample.txt").write_text("synthetic fixture version two\n")
            identity = packer.pack(source, archive)
            child = multiprocessing.get_context("fork").Process(
                target=crash_install, args=(evidence, archive, volume, identity, boundary)
            )
            child.start()
            child.join(10)
            if child.is_alive():
                child.kill()
                child.join()
                raise RuntimeError("Crash replay timed out")
            assert child.exitcode == 77, child.exitcode
            final = volume / "versions" / identity["packHash"]
            partial = volume / "staging" / (identity["packHash"] + ".partial")
            interrupted = final if final.exists() else partial
            try:
                evidence.install(archive, volume, identity["packHash"], identity["archiveHash"])
            except ValueError as error:
                retry_error = str(error)
            else:
                raise AssertionError("Expected current-code retry failure did not reproduce")
            evidence.verify(volume / "versions" / old["packHash"], old["packHash"])
            try:
                evidence.verify(final, identity["packHash"])
            except (ValueError, FileNotFoundError):
                startup_rejected = True
            else:
                raise AssertionError("Interrupted version unexpectedly became ready")
            results.append(
                {
                    "boundary": boundary,
                    "child_exit": child.exitcode,
                    "marker_present": (interrupted / "COMPLETE").exists(),
                    "root_mode": oct(interrupted.stat().st_mode & 0o777),
                    "published_path_exists": final.exists(),
                    "retry_error": retry_error,
                    "previous_version_verified": True,
                    "interrupted_version_rejected_by_startup": startup_rejected,
                }
            )
    return results


def stale_replay(repo):
    sys.path.insert(0, str(repo / "apps/agents"))
    fixtures = load("stale_fixture", repo / "apps/agents/tests/test_stale_sync.py")
    fixture = fixtures.StaleSyncScope()
    fixture.setUp()
    from operations.retire_stale_sync import termination_patch

    request = termination_patch(fixture.app, fixture.expected, "new-main")
    checked_version = fixture.app["metadata"]["resourceVersion"]
    assert request["metadata"]["resourceVersion"] == checked_version

    # An API emulator, not a live Kubernetes request. The real client creates the patch.
    def apply_to_new_operation(body):
        return (
            "conflict"
            if body.get("metadata", {}).get("resourceVersion") == checked_version
            else "new-operation-terminated"
        )

    source = (repo / "apps/agents/operations/retire_stale_sync.py").read_text()
    before = '"metadata": {"resourceVersion": metadata["resourceVersion"]},'
    assert source.count(before) == 1
    with tempfile.TemporaryDirectory(prefix="poteto-mutant-") as temp:
        mutant_path = Path(temp) / "mutant.py"
        mutant_path.write_text(source.replace(before, '"metadata": {},'))
        mutant = load("stale_mutant", mutant_path)
        mutated = mutant.termination_patch(fixture.app, fixture.expected, "new-main")
    baseline, broken = apply_to_new_operation(request), apply_to_new_operation(mutated)
    assert baseline == "conflict" and broken == "new-operation-terminated"
    return {
        "current_client": baseline,
        "scratch_mutant": broken,
        "api": "local emulator of documented resourceVersion precondition; no live API call",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "intake": intake_replays(args.repo.resolve()),
                "stale_operation": stale_replay(args.repo.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
