"""Check deployed Prometheus rules with the matching upstream promtool."""

import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "playbooks/argocd/applications/observability/prometheus"
VERSION = "3.6.0"
SHA256 = "2002ef4a55a64161affccd2786c7081d4e3b3a8d08786a98b3bb110971414916"


def promtool():
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    binary = cache / "soyspray" / f"prometheus-{VERSION}" / "promtool"
    if binary.exists():
        return binary
    if os.uname().sysname != "Linux" or os.uname().machine != "x86_64":
        raise SystemExit("The pinned promtool download supports Linux x86_64.")
    archive = f"prometheus-{VERSION}.linux-amd64"
    url = f"https://github.com/prometheus/prometheus/releases/download/v{VERSION}/{archive}.tar.gz"
    binary.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=binary.parent) as work:
        compressed = Path(work) / "download.tar.gz"
        with urllib.request.urlopen(url, timeout=60) as source, compressed.open("wb") as out:
            shutil.copyfileobj(source, out)
        with compressed.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != SHA256:
                raise SystemExit("Prometheus archive checksum does not match.")
        with tarfile.open(compressed) as bundle:
            source = bundle.extractfile(f"{archive}/promtool")
            if source is None:
                raise SystemExit("Prometheus archive has no promtool.")
            temporary = Path(work) / "promtool"
            with source, temporary.open("wb") as out:
                shutil.copyfileobj(source, out)
        temporary.chmod(0o755)
        temporary.replace(binary)
    return binary


def main():
    tool = promtool()
    with tempfile.TemporaryDirectory(prefix="soyspray-prometheus-") as directory:
        work = Path(directory)
        rules = []
        for manifest in sorted((PACKAGE / "alerts").glob("*.yaml")):
            document = yaml.safe_load(manifest.read_text())
            target = work / manifest.name
            target.write_text(yaml.safe_dump(document["spec"]))
            rules.append(str(target))
        subprocess.run([str(tool), "check", "rules", *rules], check=True)
        for fixture in sorted((PACKAGE / "tests").glob("*.yaml")):
            document = yaml.safe_load(fixture.read_text())
            target = work / ("test-" + fixture.name)
            target.write_text(yaml.safe_dump(document))
            subprocess.run([str(tool), "test", "rules", str(target)], check=True)


if __name__ == "__main__":
    main()
