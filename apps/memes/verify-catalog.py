"""Read-only deployed/restore catalog checks; SQL joins verified vector metadata in TEMP."""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
from memes.catalog import Catalog

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--data", type=Path, default=Path("/data"))
parser.add_argument("--min-count", type=int, default=9500)
parser.add_argument("--expect-no-testers", action="store_true")
args = parser.parse_args()
root = args.data
catalog = Catalog(root / "catalog")
meta = json.loads((root / "catalog/catalog.json").read_text())
with sqlite3.connect((root / "memes.sqlite3").resolve().as_uri() + "?mode=ro", uri=True) as db:
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    db.execute(
        "CREATE TEMP TABLE verified_vectors(meme_id INTEGER PRIMARY KEY,dimension INTEGER,ocr_passed INTEGER)"
    )
    db.executemany(
        "INSERT INTO verified_vectors VALUES(?,?,?)",
        [(i, len(catalog.vectors[i]), int(r["ocr_passed"])) for i, r in enumerate(catalog.items)],
    )
    row = db.execute("""SELECT COUNT(*) catalog_count,COUNT(c.cluster_id) clustered,COUNT(v.meme_id) with_vector,
      SUM(v.dimension=1152) expected_dimension,SUM(v.ocr_passed) ocr_passes,
      COUNT(DISTINCT c.cluster_id) template_clusters,COUNT(DISTINCT c.kmeans_id) kmeans_clusters,
      COUNT(DISTINCT c.catalog_version) versions,MIN(c.catalog_version) catalog_version
      FROM catalog c LEFT JOIN verified_vectors v USING(meme_id)""").fetchone()
    names = [
        "catalog_count",
        "clustered",
        "with_vector",
        "expected_dimension",
        "ocr_passes",
        "template_clusters",
        "kmeans_clusters",
        "versions",
        "catalog_version",
    ]
    counts = dict(zip(names, row, strict=True))
    assert counts["catalog_count"] >= args.min_count
    assert counts["catalog_count"] == len(catalog.items)
    assert (
        counts["catalog_count"]
        == counts["clustered"]
        == counts["with_vector"]
        == counts["expected_dimension"]
    )
    assert (
        counts["versions"] == 1
        and counts["kmeans_clusters"] == 15
        and counts["catalog_version"] == catalog.version
    )
    assert db.execute(
        "SELECT meme_id,sha256,cluster_id,kmeans_id,image,catalog_version FROM catalog ORDER BY meme_id"
    ).fetchall() == [
        (i, r["sha256"], r["cluster_id"], r["kmeans_id"], r["image"], catalog.version)
        for i, r in enumerate(catalog.items)
    ], "SQL catalog mappings differ from the frozen catalog"
    counts["testers"] = db.execute("SELECT COUNT(*) FROM tester").fetchone()[0]
    counts["sessions"] = db.execute("SELECT COUNT(*) FROM session").fetchone()[0]
    counts["impressions"] = db.execute("SELECT COUNT(*) FROM impression").fetchone()[0]
    if args.expect_no_testers:
        assert counts["testers"] == counts["sessions"] == counts["impressions"] == 0
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
for i, r in enumerate(catalog.items):
    assert (
        hashlib.sha256((catalog.directory / r["image"]).read_bytes()).hexdigest()
        == r["serving_sha256"]
    )
    assert len(catalog.vectors[i]) == 1152 and np.isfinite(catalog.vectors[i]).all()
counts.update(
    sqlite_integrity="ok",
    serving_hashes_verified=len(catalog.items),
    report=meta["report"],
    model_revisions={k: meta["pins"][k]["revision"] for k in ("image", "text")},
)
print(json.dumps(counts, indent=2))
