"""Generated synthetic catalogs only; never include production meme assets."""

import hashlib
from pathlib import Path

import numpy as np
from memes.catalog import normalize, publish
from PIL import Image


def synthetic(data, count=300, seed=7):
    data = Path(data)
    directory = data / "catalog"
    (directory / "images").mkdir(parents=True)
    rng = np.random.default_rng(seed)
    centers = normalize(rng.normal(size=(15, 64)))
    labels = np.arange(count) % 15
    vectors = normalize(centers[labels] + rng.normal(scale=0.075, size=(count, 64)))
    Image.new("RGB", (600, 600), (55, 82, 112)).save(directory / "images/synthetic.jpg")
    sha = hashlib.sha256((directory / "images/synthetic.jpg").read_bytes()).hexdigest()
    records = [
        {
            "sha256": hashlib.sha256(f"synthetic-{seed}-{i}".encode()).hexdigest(),
            "image": "images/synthetic.jpg",
            "serving_sha256": sha,
            "cluster_id": i,
            "kmeans_id": int(labels[i]),
        }
        for i in range(count)
    ]
    publish(directory, records, vectors, {"synthetic": True, "seed": seed}, {})
    return centers


if __name__ == "__main__":
    import sys

    synthetic(sys.argv[1])
