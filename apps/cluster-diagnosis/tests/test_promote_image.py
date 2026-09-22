import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

APP = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("cluster_diagnosis_promote", APP / "promote-image.py")
promote_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(promote_module)

MANIFEST = APP / "manifests/deployment.yaml"
DIGEST = "ghcr.io/kpoxo6op/cluster-diagnosis@sha256:" + "a" * 64
OLD_DIGEST = "ghcr.io/kpoxo6op/cluster-diagnosis@sha256:" + "b" * 64
IMAGE_PREFIX = "ghcr.io/kpoxo6op/cluster-diagnosis@"


def package(text):
    """Write a package whose manifest holds the given text."""
    root = Path(tempfile.mkdtemp())
    (root / "manifests").mkdir()
    (root / "manifests/deployment.yaml").write_text(text)
    return root


def manifest_text(root):
    return (root / "manifests/deployment.yaml").read_text()


def with_image(text, image):
    """Return the manifest text with its container image set to the given value."""
    lines = [
        f"          image: {image}\n" if line.strip().startswith(f"image: {IMAGE_PREFIX}") else line
        for line in text.splitlines(True)
    ]
    return "".join(lines)


def reviewed_package():
    """A package that holds the reviewed pod with a fictional previous digest."""
    text = with_image(MANIFEST.read_text(), OLD_DIGEST)
    assert OLD_DIGEST in text
    return package(text)


class PromoteImageTest(unittest.TestCase):
    def test_promotion_changes_only_the_digest_line(self):
        root = reviewed_package()
        before = manifest_text(root).splitlines(True)
        self.assertTrue(promote_module.promote(DIGEST, root))
        after = manifest_text(root).splitlines(True)
        self.assertEqual(len(before), len(after))
        changed = [(old, new) for old, new in zip(before, after, strict=True) if old != new]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0][1].strip(), f"image: {DIGEST}")

    def test_promotion_keeps_the_manifest_comments(self):
        root = reviewed_package()
        promote_module.promote(DIGEST, root)
        promoted = manifest_text(root)
        for comment in (
            "# Recreate guarantees the previous pod is gone before the next starts.",
            "# No Kubernetes identity: the loop reads Alertmanager, Loki and Prometheus",
            "# No liveness probe on purpose: a dependency outage or an unreadable",
        ):
            self.assertIn(comment, promoted)

    def test_promotion_keeps_the_resulting_manifest_parseable(self):
        root = reviewed_package()
        promote_module.promote(DIGEST, root)
        deployment = yaml.safe_load(manifest_text(root))
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        self.assertEqual(container["image"], DIGEST)
        self.assertEqual(container["command"], ["python3", "/app/diagnosis.py"])

    def test_promotion_of_the_promoted_manifest_writes_nothing(self):
        root = reviewed_package()
        promote_module.promote(DIGEST, root)
        text = manifest_text(root)
        self.assertFalse(promote_module.promote(DIGEST, root))
        self.assertEqual(manifest_text(root), text)

    def test_promotion_refuses_an_unreviewed_digest(self):
        root = reviewed_package()
        for image in (
            "ghcr.io/kpoxo6op/cluster-diagnosis:latest",
            "ghcr.io/kpoxo6op/cluster-diagnosis@sha256:" + "a" * 63,
            "ghcr.io/kpoxo6op/other@sha256:" + "a" * 64,
        ):
            with self.assertRaises(ValueError):
                promote_module.promote(image, root)
        self.assertIn(OLD_DIGEST, manifest_text(root))

    def test_promotion_refuses_a_manifest_that_is_not_the_reviewed_pod(self):
        text = with_image(MANIFEST.read_text(), OLD_DIGEST)
        root = package(text.replace('command: ["python3", "/app/diagnosis.py"]', 'command: ["sh"]'))
        with self.assertRaises(ValueError):
            promote_module.promote(DIGEST, root)
        self.assertNotIn(DIGEST, manifest_text(root))

    def test_promotion_refuses_an_ambiguous_digest(self):
        text = with_image(MANIFEST.read_text(), OLD_DIGEST)
        root = package(text + f"# {OLD_DIGEST}\n")
        with self.assertRaises(ValueError):
            promote_module.promote(DIGEST, root)

    def test_the_repository_manifest_holds_a_reviewed_digest(self):
        deployment = yaml.safe_load(MANIFEST.read_text())
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        self.assertRegex(container["image"], promote_module.IMAGE)


if __name__ == "__main__":
    unittest.main()
