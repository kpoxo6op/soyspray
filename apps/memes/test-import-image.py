"""Offline CPU/model/OCR check on generated pixels inside the importer image."""

import json
import tempfile
from pathlib import Path

import numpy as np
from memes.importer import feature_vectors, item_vectors, ocr
from PIL import Image, ImageDraw

pins = json.loads(Path("/app/models.json").read_text())
with tempfile.TemporaryDirectory() as directory:
    stage = Path(directory)
    path = stage / "generated.png"
    image = Image.new("RGB", (600, 600), "white")
    ImageDraw.Draw(image).text((20, 30), "hello world meme catalog", fill="black", font_size=36)
    image.save(path)
    text = ocr(path, Path("/tessdata"))
    assert text["passed"], text
    images, texts = feature_vectors([path], [text], stage, pins, Path("/models"))
    assert images.shape == (1, 768) and texts.shape == (1, 384)
    # Centering a singleton is zero; use opposing test vectors for this kernel.
    vectors = item_vectors(
        np.concatenate([images, -images]), np.concatenate([texts, -texts]), np.array([True, True])
    )
    assert np.isfinite(vectors).all() and np.allclose(np.linalg.norm(vectors, axis=1), 1)
print("IMPORT_IMAGE_OK: offline SigLIP2/E5, CPU, rus+eng OCR, checksum pins")
