"""Read every restored file and validate supported structured formats in private copies."""

import configparser
import hashlib
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import yaml


def check(root):
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or "lost+found" in path.parts:
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            header = stream.read(16)
            digest.update(header)
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        item = {
            "path": str(path.relative_to(root)),
            "bytes": path.stat().st_size,
            "sha256": digest.hexdigest(),
        }
        if header.startswith(b"SQLite format 3\0"):
            db = sqlite3.connect(path)
            try:
                if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ValueError("Restored SQLite integrity failed")
                tables = [
                    row[0]
                    for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                ]
                item["sqlite_rows"] = {
                    table: db.execute(
                        'SELECT count(*) FROM "' + table.replace('"', '""') + '"'
                    ).fetchone()[0]
                    for table in tables
                }
            finally:
                db.close()
        elif path.name == "database.db" and header.lstrip().startswith(b"{"):
            records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            item["json_records"] = len(records)
        elif path.suffix in {".ini", ".conf"} and path.stat().st_size:
            content = path.read_text()
            if content.lstrip().startswith("["):
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read_string(content)
                item["format"] = "ini"
        elif path.suffix == ".json" and path.stat().st_size:
            json.loads(path.read_text())
            item["format"] = "json"
        elif path.suffix in {".yaml", ".yml"} and path.stat().st_size:
            yaml.load(path.read_text(), Loader=yaml.BaseLoader)
            item["format"] = "yaml"
        elif path.suffix == ".xml" and path.stat().st_size:
            ET.parse(path)
            item["format"] = "xml"
        elif path.suffix.lower() in {".epub", ".zip"}:
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    raise ValueError("Restored ZIP integrity failed")
            item["format"] = "zip"
        files.append(item)
    return {
        "files": files,
        "file_count": len(files),
        "bytes": sum(item["bytes"] for item in files),
        "content": "restored files" if files else "empty volume",
    }


if __name__ == "__main__":
    print(json.dumps(check(Path(sys.argv[1]))))
