#!/usr/bin/env python3
"""Create a canonical private pack. Run only against private controller inputs."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

from evidence import digest, manifest, safe_name


def pack(source, archive):
    entries = []
    for file in sorted(
        (p for p in source.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(source).as_posix().encode(),
    ):
        if file.is_symlink():
            raise ValueError("Pack input contains a symlink")
        name = safe_name(file.relative_to(source).as_posix())
        if name in ("manifest.json", "COMPLETE"):
            continue
        entries.append({"path": name, "bytes": file.stat().st_size, "sha256": digest(file)})
    doc = {
        "schemaVersion": 1,
        "fileCount": len(entries),
        "totalBytes": sum(f["bytes"] for f in entries),
        "files": entries,
    }
    data = (
        json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode()
    pack_hash = hashlib.sha256(data).hexdigest()
    manifest(data, pack_hash)
    (source / "manifest.json").write_bytes(data)
    names = sorted(["manifest.json", *(f["path"] for f in entries)], key=lambda p: p.encode())
    with tarfile.open(archive, "w", format=tarfile.USTAR_FORMAT) as tar:
        for name in names:
            file = source / name
            info = tarfile.TarInfo(name)
            info.size = file.stat().st_size
            info.mode = 0o644
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            with file.open("rb") as stream:
                tar.addfile(info, stream)
    return {
        "packHash": pack_hash,
        "archiveHash": digest(archive),
        "archiveBytes": archive.stat().st_size,
        "files": len(entries),
        "contentBytes": doc["totalBytes"],
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("archive", type=Path)
    args = cli.parse_args()
    print(json.dumps(pack(args.source, args.archive)))
