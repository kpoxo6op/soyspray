import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[1] / "app/src/lab.py"


class LabContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix=".agents-lab-check-", dir=Path.home())
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.root = self.parent / "lab"

    def call(self, action="run", root=None):
        return subprocess.run(
            [sys.executable, "-I", str(LAB), action, "--root", str(root or self.root)],
            capture_output=True,
            text=True,
        )

    def test_offline_lab_runs_twice_verifies_and_cleans_only_owned_root(self):
        sentinel = self.parent / "outside"
        sentinel.write_text("preserve")
        for action in ["run", "verify", "run", "cleanup"]:
            result = self.call(action)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.root.exists())
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_foreign_directory_refuses_before_any_write(self):
        self.root.mkdir()
        sentinel = self.root / "keep"
        sentinel.write_text("preserve")
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.root.iterdir()), [sentinel])

    def test_remote_and_symlink_refuse_before_any_write(self):
        subprocess.run(["git", "init", "-q", str(self.parent)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.parent),
                "remote",
                "add",
                "origin",
                "https://example.invalid/repo",
            ],
            check=True,
        )
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.root.exists())
        real = self.parent / "real"
        real.mkdir()
        link = self.parent / "link"
        link.symlink_to(real, target_is_directory=True)
        self.assertNotEqual(self.call(root=link).returncode, 0)
        self.assertEqual(list(real.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
