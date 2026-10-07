"""Shared immutable catalog format; no ML runtime dependencies."""

import hashlib
import json
from pathlib import Path

import numpy as np


def normalize(values):
    values = np.asarray(values, dtype=np.float32)
    return values / np.maximum(np.linalg.norm(values, axis=1, keepdims=True), 1e-12)


def version(records, pins):
    payload = {"sha256": sorted(r["sha256"] for r in records), "features": pins}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def publish(directory, records, vectors, pins, report):
    directory = Path(directory)
    np.save(directory / "vectors.npy", np.asarray(vectors, dtype=np.float32))
    metadata = {
        "catalog_version": version(records, pins),
        "pins": pins,
        "items": records,
        "report": report,
    }
    (directory / "catalog.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    checksums = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [directory / "vectors.npy", directory / "catalog.json"]
    }
    (directory / "READY").write_text(json.dumps(checksums, sort_keys=True))


class Catalog:
    def __init__(self, directory):
        self.directory = Path(directory)
        checksums = json.loads((self.directory / "READY").read_text())
        for name in ("catalog.json", "vectors.npy"):
            if hashlib.sha256((self.directory / name).read_bytes()).hexdigest() != checksums[name]:
                raise ValueError("Catalog integrity check failed")
        meta = json.loads((self.directory / "catalog.json").read_text())
        self.items, self.version = meta["items"], meta["catalog_version"]
        if version(self.items, meta["pins"]) != self.version:
            raise ValueError("Catalog version mismatch")
        self.vectors = np.load(self.directory / "vectors.npy", allow_pickle=False)
        if (
            self.vectors.ndim != 2
            or len(self.vectors) != len(self.items)
            or not np.isfinite(self.vectors).all()
        ):
            raise ValueError("Invalid vectors")
        if not np.allclose(np.linalg.norm(self.vectors, axis=1), 1, atol=1e-4):
            raise ValueError("Vectors must have unit norm")
        self.clusters = np.array([r["cluster_id"] for r in self.items])
        self.kmeans = np.array([r["kmeans_id"] for r in self.items])
        if len(set(self.kmeans)) != 15:
            raise ValueError("Catalog must have 15 warm-up clusters")
