"""Exercise the private workspace restore check against a real instance.

The check talks to the service through `kubectl`.  These tests put a small
`kubectl` in front of `PATH` that performs the same operations against a real
local instance and a temporary database, so the whole orchestration runs for
real: a copy is taken, streamed out of the directory, restored by an independent
reader, compared, and the live service is confirmed unchanged.

Only synthetic values are used.  The cluster is never contacted.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def app_source():
    """Find the private runtime, or report that it is not available.

    The runtime lives in a separate private repository, so this public check
    cannot depend on it.  When the runtime is present the whole orchestration is
    exercised for real; when it is absent these tests skip instead of failing a
    public gate.
    """
    override = os.environ.get("GI_APP_SOURCE")
    candidates = [Path(override)] if override else []
    candidates.append(ROOT.parent / "gi-app")
    for candidate in candidates:
        if (candidate / "gi_app" / "server.py").is_file():
            return candidate
    return None


APP_SOURCE = app_source()
if APP_SOURCE is not None:
    sys.path.insert(0, str(APP_SOURCE))
    from gi_app.server import AppServer  # noqa: E402
    from gi_app.store import DatasetStore  # noqa: E402

requires_runtime = unittest.skipUnless(
    APP_SOURCE is not None,
    "the private runtime is not available; set GI_APP_SOURCE to its checkout",
)

FAKE_KUBECTL = r"""#!/usr/bin/env bash
# Translate the check's kubectl calls onto a real local instance.
set -euo pipefail
STATE="${FAKE_STATE:?}"
if [ "$1" = "-n" ]; then shift 2; fi
case "$1" in
  exec)
    shift
    while [ "$1" != "--" ]; do shift; done
    shift
    if [ "$1" = "tar" ]; then
      # The check asks for: tar -C /backups -cf - <member>
      member="${@: -1}"
      exec tar -C "$STATE/backups" -cf - "$member"
    fi
    # Inside the container the command starts with its own interpreter or
    # utility name; this harness maps them onto local equivalents.
    command="$1"
    shift
    case "$command" in
      python)
        exec env GI_DB_PATH="$STATE/live.sqlite3" GI_BACKUP_DIR="$STATE/backups" \
          GI_STATIC_DIR="$STATE/static" PYTHONPATH="$STATE/app" "$FAKE_PYTHON" "$@"
        ;;
      sh)
        # Only the presence check this harness needs to serve.  The check runs
        # `sh -c "test -f /backups/<member> && echo present"`.
        script="${@: -1}"
        member="${script##*/}"
        member="${member%% *}"
        if [ -f "$STATE/backups/$member" ]; then echo present; else exit 1; fi
        ;;
      *)
        echo "unexpected in-pod command: $command" >&2
        exit 2
        ;;
    esac
    ;;
  get)
    case "$2" in
      deployment)
        printf '%s' "$(cat "$STATE/deployment.json")"
        ;;
      pods)
        printf '%s' "$(cat "$STATE/pods.json")"
        ;;
      *) echo "unexpected get: $*" >&2; exit 2 ;;
    esac
    ;;
  *) echo "unexpected: $*" >&2; exit 2 ;;
esac
"""


@requires_runtime
class RestoreCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.state = self.root / "state"
        self.backups = self.state / "backups"
        self.backups.mkdir(parents=True)
        (self.state / "static").mkdir()

        # A real instance with synthetic records.
        self.live = self.state / "live.sqlite3"
        store = DatasetStore(self.live)
        revision = 0
        for index in range(3):
            day = (date(2026, 1, 1) + timedelta(days=index)).isoformat()
            revision = store.create_record(
                revision,
                "balance",
                {
                    "date": day,
                    "mortgageCents": 400_000_00 - index,
                    "mortgageScope": "all home-loan accounts",
                },
                "synthetic statement",
            )["revision"]
        store.close()
        self.revision = revision

        # The application package on PYTHONPATH for the in-pod commands.
        app = self.state / "app"
        app.mkdir()
        shutil.copytree(APP_SOURCE / "gi_app", app / "gi_app")

        # A running instance for the API reads the fake kubectl performs.
        self.server = None

        # Fake kubectl.
        binary = self.root / "bin"
        binary.mkdir()
        kubectl = binary / "kubectl"
        kubectl.write_text(FAKE_KUBECTL)
        kubectl.chmod(kubectl.stat().st_mode | stat.S_IEXEC)
        self.binary = binary

        # Minimal cluster objects for the identity checks.
        (self.state / "deployment.json").write_text(
            json.dumps(
                {
                    "metadata": {"uid": "deployment-uid-1", "name": "gi"},
                    "spec": {"replicas": 1, "strategy": {"type": "Recreate"}},
                }
            )
        )
        digest = "sha256:" + "ab" * 32
        (self.state / "pods.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "metadata": {"name": "gi-pod-1"},
                            "spec": {
                                "containers": [
                                    {"name": "web", "image": f"ghcr.io/kpoxo6op/gi-app@{digest}"}
                                ]
                            },
                            "status": {
                                "containerStatuses": [
                                    {
                                        "name": "web",
                                        "ready": True,
                                        "imageID": f"ghcr.io/kpoxo6op/gi-app@{digest}",
                                    }
                                ]
                            },
                        }
                    ]
                }
            )
        )
        self.image = f"ghcr.io/kpoxo6op/gi-app@{digest}"

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        self.directory.cleanup()

    def start_instance(self) -> int:
        """Serve the live database on the port the application reads from."""
        store = DatasetStore(self.live)
        try:
            server = AppServer(("127.0.0.1", 8080), store, self.state / "static", self.backups)
        except OSError as exc:
            store.close()
            self.skipTest(f"port 8080 is in use: {exc}")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.server = server
        return server.server_port

    def run_check(self, *extra):
        environment = {
            **os.environ,
            "PATH": f"{self.binary}:{os.environ['PATH']}",
            "PYTHONPATH": str(ROOT),
            "FAKE_STATE": str(self.state),
            "FAKE_PYTHON": sys.executable,
        }
        output = self.root / "out"
        result = subprocess.run(
            [sys.executable, "-m", "scripts.gi_restore_check", "--output", str(output), *extra],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=environment,
            timeout=300,
        )
        report = json.loads((output / "report.json").read_text())
        return result, report

    def test_a_completed_copy_restores_and_the_live_service_is_unchanged(self) -> None:
        self.start_instance()
        result, report = self.run_check()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("passed", report["result"])
        self.assertEqual(self.image, report["image"])
        self.assertEqual(self.revision, report["backup"]["revision"])
        self.assertEqual(3, report["backup"]["records"])
        self.assertEqual(self.revision, report["restored"]["revision"])
        self.assertEqual(3, report["restored"]["records"])
        self.assertEqual(3, report["identity_restored"]["sources"])
        self.assertEqual(self.revision, report["live_unchanged"]["revision"])
        self.assertEqual(3, report["live_unchanged"]["records"])
        self.assertEqual("unchanged", report["original_resources"])
        self.assertEqual("retained", report["completed_copy"])
        self.assertEqual("removed", report["scratch"])
        self.assertEqual("in-cluster", report["location"])
        connection = sqlite3.connect(f"file:{self.live}?mode=ro", uri=True)
        try:
            dataset = json.loads(
                connection.execute("SELECT content FROM gi_dataset WHERE id = 1").fetchone()[0]
            )
        finally:
            connection.close()
        self.assertEqual(self.revision, dataset["revision"])
        self.assertEqual(3, len(dataset["records"]))

    def test_the_report_never_contains_a_stored_value(self) -> None:
        self.start_instance()
        result, report = self.run_check()
        self.assertEqual(0, result.returncode)
        text = json.dumps(report)
        # No record value, no source label, and no dataset body may appear.
        # Table names and digests are structure, not content.
        for forbidden in ("mortgageCents", "sourceIds", "synthetic statement", "SELECT content"):
            self.assertNotIn(forbidden, text)
        # Only counts, identifiers, sizes, ages, and content digests.
        self.assertEqual(
            {
                "app",
                "check",
                "location",
                "image",
                "pod",
                "backup",
                "restored",
                "identity_restored",
                "scratch",
                "live_unchanged",
                "original_resources",
                "completed_copy",
                "checked_at",
                "result",
            },
            set(report),
        )
        # The only content-shaped field is a digest, never a value.
        self.assertEqual(64, len(report["identity_restored"]["content_sha256"]))
        self.assertRegex(report["identity_restored"]["content_sha256"], r"^[0-9a-f]{64}$")

    def test_a_failed_copy_is_reported_rather_than_passing(self) -> None:
        self.start_instance()
        # Make the backup directory unusable so the application cannot copy.
        shutil.rmtree(self.backups)
        self.backups.write_text("a file blocks the directory")
        result, report = self.run_check()
        self.assertEqual(1, result.returncode)
        self.assertEqual("failed", report["result"])
        self.assertIn("error", report)

    def test_a_running_image_that_is_not_a_pinned_digest_is_refused(self) -> None:
        self.start_instance()
        pods = json.loads((self.state / "pods.json").read_text())
        pods["items"][0]["spec"]["containers"][0]["image"] = "ghcr.io/kpoxo6op/gi-app:latest"
        (self.state / "pods.json").write_text(json.dumps(pods))
        result, report = self.run_check()
        self.assertEqual(1, result.returncode)
        self.assertEqual("failed", report["result"])

    def test_it_can_check_a_named_completed_copy(self) -> None:
        self.start_instance()
        first, _ = self.run_check()
        self.assertEqual(0, first.returncode)
        name = sorted(path.name for path in self.backups.glob("*.sqlite3"))[-1]
        result, report = self.run_check("--backup", name)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(name, report["backup"]["file"])
        self.assertEqual(self.revision, report["restored"]["revision"])


if __name__ == "__main__":
    unittest.main()
