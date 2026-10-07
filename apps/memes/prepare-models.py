"""Verify upstream weights and export the vision tower; no archive access."""

import hashlib
import json
import os
from pathlib import Path

os.environ.update(HF_HUB_DISABLE_XET="1", HF_HUB_DISABLE_TELEMETRY="1")
from huggingface_hub import hf_hub_download
from transformers import AutoImageProcessor, AutoModel, AutoTokenizer, SiglipVisionModel

pins = json.loads(Path("models.json").read_text())
root = Path(os.environ.get("MODEL_OUTPUT", "/models"))
for kind in ("image", "text"):
    pin = pins[kind]
    weights = Path(hf_hub_download(pin["name"], "model.safetensors", revision=pin["revision"]))
    if hashlib.sha256(weights.read_bytes()).hexdigest() != pin["sha256"]:
        raise ValueError("Upstream model checksum mismatch")
    destination = root / kind
    if kind == "image":
        model = SiglipVisionModel.from_pretrained(
            pin["name"], revision=pin["revision"], use_safetensors=True
        )
        processor = AutoImageProcessor.from_pretrained(
            pin["name"], revision=pin["revision"], use_fast=False
        )
    else:
        model = AutoModel.from_pretrained(
            pin["name"], revision=pin["revision"], use_safetensors=True
        )
        processor = AutoTokenizer.from_pretrained(pin["name"], revision=pin["revision"])
    model.save_pretrained(destination, safe_serialization=True)
    processor.save_pretrained(destination)
    del model
checksums = {
    str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in root.rglob("*")
    if p.is_file()
}
(root / "verified.json").write_text(
    json.dumps(
        {"models": {k: pins[k] for k in ("image", "text")}, "sha256": checksums}, sort_keys=True
    )
)
