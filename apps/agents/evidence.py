#!/usr/bin/env python3
"""Bounded evidence intake and read-only startup validation; no Kubernetes client."""

import hashlib
import json
import os
import re
import shutil
import socket
import sys
import tarfile
import time
from pathlib import Path, PurePosixPath

MAX_ARCHIVE = 900 * 1024 * 1024
MAX_MANIFEST = 4 * 1024 * 1024
MAX_FILES = 5000


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expected(name):
    value = os.environ.get(name, "")
    if not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError(f"{name} must be a SHA256 digest")
    return value


def safe_name(name):
    p = PurePosixPath(name)
    if (
        not name
        or p.is_absolute()
        or ".." in p.parts
        or str(p) != name
        or not re.fullmatch(r"[A-Za-z0-9_./-]+", name)
    ):
        raise ValueError("Unsafe manifest path")
    return name


def manifest(data, pack_hash):
    if len(data) > MAX_MANIFEST or hashlib.sha256(data).hexdigest() != pack_hash:
        raise ValueError("Manifest hash or size mismatch")
    doc = json.loads(data)
    canonical = (
        json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode()
    if data != canonical or set(doc) != {"schemaVersion", "files", "fileCount", "totalBytes"}:
        raise ValueError("Manifest is not canonical JSON")
    entries = doc["files"]
    if doc.get("schemaVersion") != 1 or not 1 <= len(entries) <= MAX_FILES:
        raise ValueError("Invalid manifest schema or count")
    names = set()
    if [f["path"] for f in entries] != sorted(
        (f["path"] for f in entries), key=lambda p: p.encode()
    ):
        raise ValueError("Manifest entries are not sorted")
    for f in entries:
        name = safe_name(f["path"])
        if name.casefold() in names or name in ("manifest.json", "COMPLETE"):
            raise ValueError("Duplicate or reserved manifest path")
        names.add(name.casefold())
        if (
            set(f) != {"path", "bytes", "sha256"}
            or type(f["bytes"]) is not int
            or not 0 <= f["bytes"] <= MAX_ARCHIVE
        ):
            raise ValueError("Invalid file size")
        if not re.fullmatch(r"[a-f0-9]{64}", f["sha256"]):
            raise ValueError("Invalid file digest")
    total = sum(f["bytes"] for f in entries)
    if (
        total > MAX_ARCHIVE
        or doc.get("totalBytes") != total
        or doc.get("fileCount") != len(entries)
    ):
        raise ValueError("Manifest count or total size mismatch")
    return doc


def verify(root, pack_hash, require_complete=True):
    if root.is_symlink():
        raise ValueError("Symlinked pack root")
    doc = manifest((root / "manifest.json").read_bytes(), pack_hash)
    expected_names = {f["path"] for f in doc["files"]} | {"manifest.json"}
    if require_complete:
        expected_names.add("COMPLETE")
        if (root / "COMPLETE").read_text().strip() != pack_hash:
            raise ValueError("Pack completion marker mismatch")
        if root.stat().st_mode & 0o777 != 0o555:
            raise ValueError("Published pack directory is not read-only")
    names = set()
    for file in root.rglob("*"):
        if file.is_symlink():
            raise ValueError("Symlink in pack")
        if file.is_file():
            names.add(file.relative_to(root).as_posix())
    if names != expected_names:
        raise ValueError("Pack file set mismatch")
    for f in doc["files"]:
        file = root / f["path"]
        if file.stat().st_size != f["bytes"] or digest(file) != f["sha256"]:
            raise ValueError(f"File hash mismatch: {f['path']}")
    return doc


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def install(archive, volume, pack_hash, archive_hash):
    if archive.stat().st_size > MAX_ARCHIVE or digest(archive) != archive_hash:
        raise ValueError("Archive hash or size mismatch")
    if volume.is_symlink() or any(
        (volume / child).is_symlink() for child in ("staging", "versions")
    ):
        raise ValueError("Symlinked intake parent")
    final = volume / "versions" / pack_hash
    if final.exists():
        verify(final, pack_hash)
        return {"status": "already-identical", "packHash": pack_hash}
    if volume.is_symlink():
        raise ValueError("Symlinked volume")
    for child in ("staging", "versions"):
        if (volume / child).is_symlink():
            raise ValueError("Symlinked intake parent")
    with tarfile.open(archive, mode="r:") as tar:
        members = tar.getmembers()
        if len(members) > MAX_FILES + 1:
            raise ValueError("Too many archive members")
        names = set()
        for member in members:
            safe_name(member.name)
            if (
                not member.isfile()
                or member.name.casefold() in names
                or member.size > MAX_ARCHIVE
                or member.pax_headers
                or member.sparse
                or member.uid != 0
                or member.gid != 0
                or member.mtime != 0
                or member.mode != 0o644
            ):
                raise ValueError("Archive contains links, duplicate names or non-regular files")
            names.add(member.name.casefold())
        item = tar.getmember("manifest.json")
        if item.size > MAX_MANIFEST:
            raise ValueError("Oversized manifest")
        data = tar.extractfile(item).read()
        doc = manifest(data, pack_hash)
        mapping = {f["path"]: f for f in doc["files"]}
        if names != {n.casefold() for n in mapping} | {"manifest.json"}:
            raise ValueError("Archive and manifest file sets differ")
        stage_parent = volume / "staging"
        stage_parent.mkdir(exist_ok=True)
        stage = stage_parent / f"{pack_hash}.partial"
        owner = {"packHash": pack_hash, "archiveHash": archive_hash}
        if stage.exists():
            if stage.is_symlink() or any(p.is_symlink() for p in stage.rglob("*")):
                raise ValueError("Symlink in partial intake")
            if (stage / ".INTAKE").exists():
                owned = json.loads((stage / ".INTAKE").read_text()) == owner
            else:
                # Recovery after the final verification but before publication.
                verify(stage, pack_hash, require_complete=(stage / "COMPLETE").exists())
                owned = True
            if not owned:
                raise ValueError("Unknown partial intake; deliberate recovery required")
            # Resume only our matching partial version; never touch previous versions.
            for directory in [stage, *(p for p in stage.rglob("*") if p.is_dir())]:
                if directory.is_symlink():
                    raise ValueError("Symlink in partial intake")
                directory.chmod(0o755)
            shutil.rmtree(stage)
        stage.mkdir()
        with (stage / ".INTAKE").open("x") as ownership:
            ownership.write(json.dumps(owner))
            ownership.flush()
            os.fsync(ownership.fileno())
        for member in members:
            expected_size = (
                len(data) if member.name == "manifest.json" else mapping[member.name]["bytes"]
            )
            if member.size != expected_size:
                raise ValueError("Archive member size mismatch")
            destination = stage / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as output, tar.extractfile(member) as source:
                shutil.copyfileobj(source, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            destination.chmod(0o444)
        (stage / ".INTAKE").unlink()
    verify(stage, pack_hash, require_complete=False)
    with (stage / "COMPLETE").open("x") as marker:
        marker.write(pack_hash + "\n")
        marker.flush()
        os.fsync(marker.fileno())
    (stage / "COMPLETE").chmod(0o444)
    directories = sorted(
        (p for p in stage.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True
    )
    for directory in directories:
        fsync_dir(directory)
        directory.chmod(0o555)
    fsync_dir(stage)
    final.parent.mkdir(exist_ok=True)
    if final.parent.is_symlink():
        raise ValueError("Symlinked versions directory")
    stage.rename(final)
    # Moving a directory across parents needs owner write permission for '..'.
    # Startup also checks this final mode, so publication is not ready before it is set.
    final.chmod(0o555)
    fsync_dir(final)
    fsync_dir(final.parent)
    return {
        "status": "installed",
        "packHash": pack_hash,
        "files": doc["fileCount"],
        "bytes": doc["totalBytes"],
    }


def receive(root=Path("/evidence")):
    pack_hash, archive_hash = expected("PACK_HASH"), expected("ARCHIVE_HASH")
    final = root / "versions" / pack_hash
    if final.exists():
        doc = verify(final, pack_hash)
        print(
            json.dumps(
                {
                    "status": "already-identical",
                    "packHash": pack_hash,
                    "files": doc["fileCount"],
                    "bytes": doc["totalBytes"],
                }
            ),
            flush=True,
        )
        return
    sockpath = "/tmp/evidence-intake.sock"
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(sockpath)
        os.chmod(sockpath, 0o600)
        server.listen(1)
        server.settimeout(3600)
        connection, _ = server.accept()
        with connection, Path("/tmp/intake.tar").open("xb") as output:
            count = 0
            while chunk := connection.recv(1024 * 1024):
                count += len(chunk)
                if count > MAX_ARCHIVE:
                    raise ValueError("Intake exceeds archive bound")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    print(
        json.dumps(install(Path("/tmp/intake.tar"), root, pack_hash, archive_hash)),
        flush=True,
    )


def send():
    with socket.socket(socket.AF_UNIX) as client:
        client.connect("/tmp/evidence-intake.sock")
        remaining = int(os.environ["ARCHIVE_BYTES"])
        if not 0 < remaining <= MAX_ARCHIVE:
            raise ValueError("Invalid archive transfer size")
        while remaining:
            chunk = sys.stdin.buffer.read(min(256 * 1024, remaining))
            if not chunk:
                raise ValueError("Truncated archive transfer")
            client.sendall(chunk)
            remaining -= len(chunk)
        client.shutdown(socket.SHUT_WR)


def main():
    action = sys.argv[1]
    if action == "receive":
        receive()
    elif action == "send":
        send()
    elif action == "verify":
        pack_hash = expected("PACK_HASH")
        root = Path("/evidence/versions") / pack_hash
        for _ in range(1200):
            if (root / "COMPLETE").exists():
                print(json.dumps({"verified": True, "files": verify(root, pack_hash)["fileCount"]}))
                return
            time.sleep(3)
        raise RuntimeError("Evidence intake did not complete within one hour")
    else:
        raise ValueError("Unknown fixed evidence operation")


if __name__ == "__main__":
    main()
