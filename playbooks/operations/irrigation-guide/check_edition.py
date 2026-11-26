"""Validate the complete, flat-named static guide tree and its SHA256SUMS."""

import hashlib
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
manifest = root / "SHA256SUMS"
if root.is_symlink() or not root.is_dir() or manifest.is_symlink():
    sys.exit("Expected a real edition directory and regular manifest.")
expected = {}
for line in manifest.read_text().splitlines():
    match = re.fullmatch(r"([0-9a-f]{64})  ([a-zA-Z0-9_-][a-zA-Z0-9._/-]*)", line)
    if not match:
        sys.exit("Invalid checksum entry.")
    digest, name = match.groups()
    if any(p in ("", ".", "..") for p in name.split("/")) or name in expected:
        sys.exit("Invalid or repeated relative path.")
    expected[name] = digest
if not {"index.html", "film.mp4"} <= expected.keys():
    sys.exit("The guide needs an index and a movie.")
actual = set()
for path in root.rglob("*"):
    if path.is_symlink() or not (path.is_dir() or path.is_file()):
        sys.exit("Only directories and regular files may be published.")
    if path.is_file() and path != manifest:
        actual.add(path.relative_to(root).as_posix())
if actual != expected.keys():
    sys.exit("File inventory differs from the checksum manifest.")
for name, wanted in expected.items():
    with (root / name).open("rb") as stream:
        calculated = hashlib.file_digest(stream, "sha256").hexdigest()
    if calculated != wanted:
        sys.exit("Hash mismatch: " + name)
