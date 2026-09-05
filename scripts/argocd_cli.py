"""Use the upstream CLI version installed in the cluster."""

import hashlib
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

VERSION = "2.14.5"
SHA256 = "739af600a568728cfb0fcc9c96bb63e5f56cc9fdb61a9d7416bd5dbdc9985c9b"


def verify(binary):
    with binary.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != SHA256:
            raise ValueError("The cached Argo CLI does not match its pinned checksum.")


def argocd():
    if os.uname().sysname != "Linux" or os.uname().machine != "x86_64":
        raise ValueError("The pinned Argo CLI download supports Linux x86_64.")
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    binary = cache / "soyspray" / f"argocd-{VERSION}" / "argocd"
    if not binary.exists():
        binary.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/argoproj/argo-cd/releases/download/v{VERSION}/argocd-linux-amd64"
        print(f"Downloading upstream Argo CLI {VERSION} to the local cache.", flush=True)
        with tempfile.TemporaryDirectory(dir=binary.parent) as work:
            temporary = Path(work) / "argocd"
            with urllib.request.urlopen(url, timeout=60) as source, temporary.open("wb") as out:
                shutil.copyfileobj(source, out)
            verify(temporary)
            temporary.chmod(0o755)
            temporary.replace(binary)
    verify(binary)
    return binary
