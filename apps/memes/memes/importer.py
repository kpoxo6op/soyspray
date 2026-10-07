"""Read-only, seeded archive import; stage then atomically freeze the catalog."""

import os

os.environ.update(
    OMP_NUM_THREADS="4",
    MKL_NUM_THREADS="4",
    OPENBLAS_NUM_THREADS="4",
    TOKENIZERS_PARALLELISM="false",
    HF_HUB_DISABLE_TELEMETRY="1",
    HF_HUB_DISABLE_XET="1",
)

import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import re
import resource
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .catalog import normalize, publish

PINS_PATH = Path(__file__).resolve().parent.parent / "models.json"


def dhash(image):
    pixels = np.asarray(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS))
    return sum(int(value) << i for i, value in enumerate((pixels[:, :-1] > pixels[:, 1:]).ravel()))


def sample(source, target, seed, stage):
    paths = sorted(
        p
        for p in source.rglob("*")
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
        and p.is_file()
        and not p.is_symlink()
        and p.resolve().is_relative_to(source)
    )
    rng = np.random.default_rng(seed)
    accepted, rejected, hashes, dhashes = [], [], set(), []
    (stage / "images").mkdir(exist_ok=True)
    for index in rng.permutation(len(paths)):
        path = paths[index]
        relative = str(path.relative_to(source))
        try:
            with Image.open(path) as image:
                if getattr(image, "n_frames", 1) != 1:
                    rejected.append({"source": relative, "reason": "animated"})
                    continue
                image.load()
                image = ImageOps.exif_transpose(image).convert("RGB")
                if min(image.size) < 300:
                    rejected.append({"source": relative, "reason": "too-small"})
                    continue
                sha = hashlib.sha256(path.read_bytes()).hexdigest()
                h = dhash(image)
                if sha in hashes:
                    rejected.append({"source": relative, "reason": "sha-duplicate", "sha256": sha})
                    continue
                match = next(
                    (i for i, previous in enumerate(dhashes) if (h ^ previous).bit_count() <= 6),
                    None,
                )
                if match is not None:
                    rejected.append(
                        {
                            "source": relative,
                            "reason": "dhash-duplicate",
                            "of": accepted[match]["sha256"],
                            "sha256": sha,
                        }
                    )
                    continue
                filename = f"images/{sha}.jpg"
                record = {
                    "sha256": sha,
                    "source": relative,
                    "dhash": h,
                    "image": filename,
                    "width": image.width,
                    "height": image.height,
                }
                image.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
                image.save(stage / filename, "JPEG", quality=85, optimize=True)
                record["serving_sha256"] = hashlib.sha256(
                    (stage / filename).read_bytes()
                ).hexdigest()
                accepted.append(record)
                hashes.add(sha)
                dhashes.append(h)
                if target and len(accepted) == target:
                    break
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
            rejected.append({"source": relative, "reason": "decode", "error": type(error).__name__})
    (stage / "rejections.json").write_text(json.dumps(rejected))
    (stage / "sample.json").write_text(
        json.dumps({"records": accepted, "population": len(paths), "rejected": len(rejected)})
    )
    if target and len(accepted) != target:
        raise ValueError(f"Archive exhausted: {len(accepted)} eligible, target {target}")
    if len(accepted) < 15:
        raise ValueError("At least 15 eligible images are required")
    return accepted, len(paths), len(rejected)


def ocr(path, tessdata):
    result = subprocess.run(
        [
            "tesseract",
            str(path),
            "stdout",
            "--tessdata-dir",
            str(tessdata),
            "-l",
            "rus+eng",
            "--psm",
            "11",
            "tsv",
        ],
        env={**os.environ, "OMP_THREAD_LIMIT": "1", "OMP_NUM_THREADS": "1"},
        capture_output=True,
        check=True,
        timeout=90,
    )
    words = []
    for row in csv.DictReader(io.StringIO(result.stdout.decode()), delimiter="\t"):
        text = row.get("text", "").strip()
        if float(row.get("conf", -1)) >= 60 and re.search(r"[A-Za-zА-Яа-яЁё]{2,}", text):
            words.append(text)
    return {"text": " ".join(words), "words": len(words), "passed": len(words) >= 3}


def feature_vectors(paths, texts, stage, pins, model_dir):
    import torch
    from transformers import AutoImageProcessor, AutoModel, AutoTokenizer, SiglipVisionModel

    if model_dir:
        stamp = json.loads((model_dir / "verified.json").read_text())
        if stamp["models"] != {k: pins[k] for k in ("image", "text")}:
            raise ValueError("Exported model pin mismatch")
        for relative, expected in stamp["sha256"].items():
            if hashlib.sha256((model_dir / relative).read_bytes()).hexdigest() != expected:
                raise ValueError("Exported model checksum mismatch")
    else:
        from huggingface_hub import hf_hub_download

        for kind in ("image", "text"):
            pin = pins[kind]
            checkpoint = hf_hub_download(
                pin["name"], "model.safetensors", revision=pin["revision"], local_files_only=True
            )
            if hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest() != pin["sha256"]:
                raise ValueError("Upstream model checksum mismatch")
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.manual_seed(pins["config"]["seed"])
    available = sorted(os.sched_getaffinity(0))
    if len(available) > 4:
        os.sched_setaffinity(0, set(available[:4]))
    model = pins["image"]
    location = str(model_dir / "image") if model_dir else model["name"]
    kwargs = (
        {"local_files_only": True}
        if model_dir
        else {"revision": model["revision"], "local_files_only": True}
    )
    processor = AutoImageProcessor.from_pretrained(location, use_fast=False, **kwargs)
    vision = (
        SiglipVisionModel.from_pretrained(
            location, use_safetensors=True, attn_implementation="sdpa", **kwargs
        )
        .eval()
        .to("cpu")
    )
    image_rows = []
    with torch.inference_mode():
        for start in range(0, len(paths), 8):
            pixels = []
            for path in paths[start : start + 8]:
                with Image.open(path) as image:
                    pixels.append(ImageOps.exif_transpose(image).convert("RGB"))
            image_rows.append(
                vision(**processor(images=pixels, return_tensors="pt")).pooler_output.numpy()
            )
    image_vectors = np.concatenate(image_rows)
    np.save(stage / "image-raw.npy", image_vectors)
    del vision
    passing = [i for i, t in enumerate(texts) if t["passed"]]
    text_vectors = np.zeros((len(paths), 384), dtype=np.float32)
    if passing:
        model = pins["text"]
        location = str(model_dir / "text") if model_dir else model["name"]
        kwargs = (
            {"local_files_only": True}
            if model_dir
            else {"revision": model["revision"], "local_files_only": True}
        )
        tokenizer = AutoTokenizer.from_pretrained(location, **kwargs)
        text_model = (
            AutoModel.from_pretrained(
                location, use_safetensors=True, attn_implementation="sdpa", **kwargs
            )
            .eval()
            .to("cpu")
        )
        with torch.inference_mode():
            for start in range(0, len(passing), 16):
                indices = passing[start : start + 16]
                inputs = tokenizer(
                    ["query: " + texts[i]["text"] for i in indices],
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                )
                states = text_model(**inputs).last_hidden_state
                mask = inputs["attention_mask"].unsqueeze(-1)
                pooled = (states * mask).sum(1) / mask.sum(1)
                text_vectors[indices] = torch.nn.functional.normalize(pooled, p=2, dim=1).numpy()
        del text_model
    np.save(stage / "text-raw.npy", text_vectors)
    return image_vectors, text_vectors


def item_vectors(images, texts, passing):
    image_part = normalize(images - images.mean(axis=0))
    text_part = np.zeros_like(texts)
    if np.any(passing):
        text_part[passing] = normalize(texts[passing] - texts[passing].mean(axis=0))
    return normalize(np.concatenate([image_part, text_part * 0.5], axis=1))


def template_clusters(images, hashes, threshold=0.92):
    parent = list(range(len(images)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = find(int(i)), find(int(j))
        parent[max(a, b)] = min(a, b)

    unit = normalize(images)
    for start in range(0, len(unit), 256):
        sim = unit[start : start + 256] @ unit.T
        for local, j in zip(*np.where(sim >= threshold), strict=False):
            i = start + int(local)
            if j > i:
                union(i, j)
    for i, h in enumerate(hashes):
        for j in range(i):
            if (h ^ hashes[j]).bit_count() <= 6:
                union(i, j)
    return [find(i) for i in range(len(images))]


def run(source, data, target, seed, tessdata, model_dir=None, resume=False, require_readonly=True):
    start = time.perf_counter()
    source, data, tessdata = Path(source).resolve(), Path(data).resolve(), Path(tessdata)
    if not source.is_dir() or data.is_relative_to(source) or source.is_relative_to(data):
        raise ValueError("Source and destination must be separate existing archive paths")
    if require_readonly and not os.statvfs(source).f_flag & os.ST_RDONLY:
        raise ValueError("Archive must be mounted read-only")
    if (data / "catalog").exists():
        raise ValueError("Frozen catalog already exists; refusing overwrite")
    pins = json.loads(PINS_PATH.read_text())
    pins["config"]["seed"] = seed
    pins["versions"] = {
        p: importlib.metadata.version(p)
        for p in [
            "torch",
            "transformers",
            "numpy",
            "pillow",
            "scikit-learn",
            "tokenizers",
            "safetensors",
            "sentencepiece",
        ]
    }
    pins["python"] = __import__("platform").python_version()
    actual = (
        subprocess.check_output(["tesseract", "--version"], stderr=subprocess.STDOUT)
        .decode()
        .splitlines()[0]
        .split()[-1]
    )
    if actual != pins["tesseract"]:
        raise ValueError("Tesseract version differs from pin")
    for language, expected in pins["tessdata"].items():
        if (
            hashlib.sha256((tessdata / f"{language}.traineddata").read_bytes()).hexdigest()
            != expected
        ):
            raise ValueError("Traineddata checksum differs from pin")
    data.mkdir(parents=True, exist_ok=True)
    stage = data / ".import-stage"
    config = {"source": str(source), "target": target, "pins": pins}
    if stage.exists():
        if not resume or json.loads((stage / "config.json").read_text()) != config:
            raise ValueError("Staging exists; use --resume with identical inputs")
    else:
        stage.mkdir(mode=0o700)
        (stage / "config.json").write_text(json.dumps(config, sort_keys=True))
    if (stage / "sample.json").exists():
        info = json.loads((stage / "sample.json").read_text())
        records, population, rejected = info["records"], info["population"], info["rejected"]
        if target and len(records) != target:
            raise ValueError("Incomplete sample; destination must be reset deliberately")
    else:
        records, population, rejected = sample(source, target, seed, stage)
    paths = [source / r["source"] for r in records]
    for path, record in zip(paths, records, strict=False):
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Source changed during import")
    print(
        json.dumps(
            {
                "stage": "sample",
                "accepted": len(records),
                "population": population,
                "rejected": rejected,
            }
        ),
        flush=True,
    )
    if (stage / "ocr.json").exists():
        texts = json.loads((stage / "ocr.json").read_text())
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            texts = list(pool.map(lambda p: ocr(p, tessdata), paths))
        (stage / "ocr.json").write_text(json.dumps(texts, ensure_ascii=False))
    print(json.dumps({"stage": "ocr", "passed": sum(t["passed"] for t in texts)}), flush=True)
    if (stage / "text-raw.npy").exists() and (stage / "image-raw.npy").exists():
        images, text = np.load(stage / "image-raw.npy"), np.load(stage / "text-raw.npy")
    else:
        images, text = feature_vectors(
            paths, texts, stage, pins, Path(model_dir) if model_dir else None
        )
    vectors = item_vectors(images, text, np.array([t["passed"] for t in texts]))
    if not np.isfinite(vectors).all():
        raise ValueError("Nonfinite features")
    from sklearn.cluster import KMeans
    from threadpoolctl import threadpool_limits

    with threadpool_limits(limits=4):
        templates = template_clusters(images, [r["dhash"] for r in records])
        groups = KMeans(n_clusters=15, n_init=10, max_iter=100, random_state=seed).fit_predict(
            vectors
        )
    for r, template, group, t in zip(records, templates, groups, texts, strict=False):
        r.update(cluster_id=int(template), kmeans_id=int(group), ocr_passed=t["passed"])
    report = {
        "accepted": len(records),
        "population": population,
        "rejected": rejected,
        "templates": len(set(templates)),
        "ocr_passed": sum(t["passed"] for t in texts),
        "wall_seconds": time.perf_counter() - start,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }
    publish(stage, records, vectors, pins, report)
    # Fail before publication if template exclusions make warm-up impossible.
    from .catalog import Catalog
    from .recommender import warmup_plan

    warmup_plan(Catalog(stage), np.random.default_rng(seed))
    for r in records:
        if hashlib.sha256((stage / r["image"]).read_bytes()).hexdigest() != r["serving_sha256"]:
            raise ValueError("Serving copy checksum failed")
    os.rename(stage, data / "catalog")
    print(json.dumps(report), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="/archive")
    parser.add_argument("--data", default="/data")
    parser.add_argument("--target", type=int, default=10000, help="0 imports all eligible images")
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument(
        "--tessdata",
        default=os.environ.get("TESSDATA_PREFIX", "/usr/share/tesseract-ocr/5/tessdata"),
    )
    parser.add_argument("--models", default=os.environ.get("MEMES_MODELS"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--local-sample",
        action="store_true",
        help="Allow writable local copies; never use on cluster archive",
    )
    args = parser.parse_args()
    if args.target < 0:
        parser.error("target must be nonnegative")
    run(
        args.source,
        args.data,
        args.target,
        args.seed,
        args.tessdata,
        args.models,
        args.resume,
        not args.local_sample,
    )


if __name__ == "__main__":
    main()
