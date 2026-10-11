import hashlib
import io
import json
import multiprocessing
import os
import sys
import tarfile
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence import digest, install, manifest, receive, verify
from pack import pack


class EvidenceContract(unittest.TestCase):
    """Observable trust boundary: only a complete hash-pinned pack becomes readable."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "index.json").write_text('{"schemaVersion":1}\n')
        (self.source / "video.mp4").write_bytes(b"original-test-content")
        self.archive = self.root / "pack.tar"
        self.identity = pack(self.source, self.archive)
        self.volume = self.root / "volume"
        self.volume.mkdir()

    def intake(self, archive=None, pack_hash=None):
        archive = archive or self.archive
        return install(
            archive, self.volume, pack_hash or self.identity["packHash"], digest(archive)
        )

    def malformed(self, change):
        output = self.root / "bad.tar"
        with (
            tarfile.open(self.archive, "r:") as original,
            tarfile.open(output, "w", format=tarfile.USTAR_FORMAT) as target,
        ):
            for item in original.getmembers():
                payload = original.extractfile(item).read()
                if change == "missing" and item.name == "video.mp4":
                    continue
                if item.name == "video.mp4":
                    if change == "traversal":
                        item.name = "../outside"
                    elif change == "absolute":
                        item.name = "/outside"
                    elif change == "symlink":
                        item.type = tarfile.SYMTYPE
                        item.linkname = "/outside"
                        item.size = 0
                    elif change == "device":
                        item.type = tarfile.CHRTYPE
                        item.size = 0
                    elif change == "wrong-hash":
                        payload = b"x" * len(payload)
                    elif change == "oversize":
                        item.size = 901 * 1024 * 1024
                        target.fileobj.write(item.tobuf(format=tarfile.USTAR_FORMAT))
                        continue
                target.addfile(item, io.BytesIO(payload) if item.isfile() else None)
                if change == "duplicate":
                    target.addfile(item, io.BytesIO(payload) if item.isfile() else None)
            if change == "extra":
                item = tarfile.TarInfo("extra.json")
                item.mode = 0o644
                item.size = 2
                target.addfile(item, io.BytesIO(b"{}"))
        return output

    def test_complete_pack_is_readonly_and_identical_retry_is_noop(self):
        result = self.intake()
        final = self.volume / "versions" / self.identity["packHash"]
        self.assertEqual(result["status"], "installed")
        self.assertEqual(verify(final, self.identity["packHash"])["fileCount"], 2)
        self.assertEqual((final / "video.mp4").stat().st_mode & 0o777, 0o444)
        self.assertEqual(final.stat().st_mode & 0o777, 0o555)
        before = (final / "COMPLETE").stat().st_mtime_ns
        self.assertEqual(self.intake()["status"], "already-identical")
        self.assertEqual((final / "COMPLETE").stat().st_mtime_ns, before)

    def test_untrusted_archives_never_publish(self):
        # A tar flag is not validation. Links, traversal and metadata attacks cross the write boundary.
        for attack in [
            "traversal",
            "absolute",
            "symlink",
            "device",
            "duplicate",
            "extra",
            "missing",
            "wrong-hash",
            "oversize",
        ]:
            with (
                self.subTest(attack=attack),
                tempfile.TemporaryDirectory(dir=self.root) as isolated,
            ):
                self.volume = Path(isolated)
                with self.assertRaises((ValueError, tarfile.TarError, KeyError, OSError)):
                    self.intake(self.malformed(attack))
                self.assertFalse((self.volume / "versions" / self.identity["packHash"]).exists())
                self.assertFalse((self.root / "outside").exists())

    def test_completed_hook_retry_exits_without_opening_transfer_socket(self):
        self.intake()
        output = io.StringIO()
        with (
            patch.dict(
                os.environ,
                {
                    "PACK_HASH": self.identity["packHash"],
                    "ARCHIVE_HASH": self.identity["archiveHash"],
                },
            ),
            patch("evidence.socket.socket", side_effect=AssertionError("no transfer allowed")),
            redirect_stdout(output),
        ):
            receive(self.volume)
        self.assertEqual(json.loads(output.getvalue())["status"], "already-identical")

    def test_foreign_partial_is_retained_and_cannot_disturb_previous_version(self):
        original = self.identity.copy()
        self.intake()
        (self.source / "recovery-validation.json").write_text('{"schemaVersion":1}\n')
        self.identity = pack(self.source, self.archive)
        partial = self.volume / "staging" / f"{self.identity['packHash']}.partial"
        partial.mkdir()
        ownership = {"packHash": original["packHash"], "archiveHash": original["archiveHash"]}
        (partial / ".INTAKE").write_text(json.dumps(ownership))
        (partial / "sentinel").write_bytes(b"retain unknown data")
        with self.assertRaisesRegex(ValueError, "Unknown partial"):
            self.intake()
        self.assertEqual((partial / "sentinel").read_bytes(), b"retain unknown data")
        verify(self.volume / "versions" / original["packHash"], original["packHash"])
        self.assertFalse((self.volume / "versions" / self.identity["packHash"]).exists())

    def test_manifest_identity_and_total_are_checked(self):
        doc = json.loads((self.source / "manifest.json").read_bytes())
        doc["totalBytes"] += 1
        data = (json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaisesRegex(ValueError, "total"):
            manifest(data, hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(ValueError, "hash"):
            self.intake(pack_hash="0" * 64)

    def test_readonly_startup_rejects_tampering_missing_complete_and_wrong_id(self):
        self.intake()
        final = self.volume / "versions" / self.identity["packHash"]
        with self.assertRaises(ValueError):
            verify(final, "0" * 64)
        video = final / "video.mp4"
        video.chmod(0o644)
        video.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash"):
            verify(final, self.identity["packHash"])
        final.chmod(0o755)
        (final / "COMPLETE").unlink()
        with self.assertRaises(FileNotFoundError):
            verify(final, self.identity["packHash"])

    def test_canonical_manifest_vector_and_archive_reproducibility(self):
        second = self.root / "second.tar"
        again = pack(self.source, second)
        self.assertEqual(self.identity, again)
        self.assertEqual(self.archive.read_bytes(), second.read_bytes())
        vector = b'{"fileCount":1,"files":[{"bytes":0,"path":"empty","sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}],"schemaVersion":1,"totalBytes":0}\n'
        self.assertEqual(manifest(vector, hashlib.sha256(vector).hexdigest())["fileCount"], 1)
        with self.assertRaisesRegex(ValueError, "canonical"):
            manifest(vector + b" ", hashlib.sha256(vector + b" ").hexdigest())

    def test_killed_intake_leaves_no_complete_and_matching_retry_recovers(self):
        for i in range(600):
            (self.source / f"part-{i:04}.json").write_bytes(b"x" * 4096)
        self.identity = pack(self.source, self.archive)
        child = multiprocessing.Process(
            target=install,
            args=(
                self.archive,
                self.volume,
                self.identity["packHash"],
                self.identity["archiveHash"],
            ),
        )
        child.start()
        partial = self.volume / "staging" / f"{self.identity['packHash']}.partial"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (partial / ".INTAKE").exists():
            time.sleep(0.001)
        self.assertTrue((partial / ".INTAKE").exists())
        child.kill()
        child.join()
        self.assertFalse((self.volume / "versions" / self.identity["packHash"]).exists())
        self.assertFalse((partial / "COMPLETE").exists())
        self.assertEqual(self.intake()["status"], "installed")


if __name__ == "__main__":
    unittest.main()
