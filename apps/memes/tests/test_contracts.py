"""Contracts missing from Soyspray's infrastructure and other app suites."""

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest
from e2e import exercise
from fixture import synthetic
from memes import metrics, recommender
from memes.importer import item_vectors, sample, template_clusters
from memes.store import Refused, Store
from PIL import Image


@pytest.fixture
def store(tmp_path):
    synthetic(tmp_path)
    instance = Store(tmp_path)
    cookie = instance.exchange(instance.invite("test"))
    return instance, instance.authenticate(cookie)


def test_http_evaluation_boundary(tmp_path):
    """HTTP reactions must improve clustered taste and agree with SQL, unlike a unit score test."""
    synthetic(tmp_path, count=10000)
    report = exercise(tmp_path)
    assert report["actions"] >= 150
    assert report["rates"]["rec"] > report["rates"]["random"]


def test_queue_concurrency_and_immutable_history(store):
    """Two tabs racing must commit one action and one tail slot; SQL also rejects rewrites."""
    instance, session = store
    feed = instance.feed(session)
    assert len(feed["items"]) == 3
    ids = [r["impression_id"] for r in feed["items"]]
    instance.mutate(session, ids[0], "render", {})

    def click(_):
        try:
            return instance.mutate(
                session, ids[0], "action", {"action": "like", "hidden_ms": 0, "client_seq": 1}
            )
        except Refused:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(click, range(2)))
    assert sum(r is not None for r in results) == 1
    next_feed = instance.feed(session)
    assert [r["impression_id"] for r in next_feed["items"][:2]] == ids[1:]
    with instance.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM impression").fetchone()[0] == 4
        assert (
            db.execute("SELECT COUNT(*) FROM event WHERE kind='refused-repeat'").fetchone()[0] == 1
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE impression SET action='dislike' WHERE impression_id=?", (ids[0],))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE impression SET score=score+1")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE event SET payload='{}'")


def test_repeat_insert_is_refused_and_logged(store):
    """Database uniqueness catches a selector regression before a repeated image can be served."""
    instance, session = store
    instance.feed(session)
    with instance.transaction() as db:
        first = db.execute("SELECT * FROM impression LIMIT 1").fetchone()
        assert not instance.commit_pick(db, session, (first["meme_id"], "random", 0.25, None, 0), 3)
    with instance.connect() as db:
        assert (
            db.execute("SELECT COUNT(*) FROM event WHERE kind='refused-repeat'").fetchone()[0] == 1
        )


def test_tail_uses_latest_feedback_after_warmup(store):
    """Committed preloads retain scores; the newly selected random/rec slot uses the latest click."""
    instance, session = store
    for seq in range(18):
        feed = instance.feed(session)
        head = feed["items"][0]["impression_id"]
        instance.mutate(session, head, "render", {})
        instance.mutate(
            session,
            head,
            "action",
            {"action": "like" if seq % 2 else "dislike", "hidden_ms": 0, "client_seq": seq},
        )
        with instance.connect() as db:
            rows = db.execute("SELECT * FROM impression ORDER BY served_seq").fetchall()
        tail = rows[-1]
        if tail["arm"] != "warmup":
            expected = recommender.scores(
                instance.catalog.vectors,
                [r["meme_id"] for r in rows if r["action"] == "like"],
                [r["meme_id"] for r in rows if r["action"] == "dislike"],
            )
            assert tail["score"] == pytest.approx(float(expected[tail["meme_id"]]))


def test_scores_and_no_likes():
    """Top-three scoring must ignore a fourth weaker neighbor, including dislike-only cold starts."""
    vectors = np.array([[1.0, 0.0], [0.9, 0.1], [0.8, 0.2], [0.7, 0.3], [0.0, 1.0]])
    assert recommender.scores(vectors, [1, 2, 3, 4], [4])[0] == pytest.approx(0.8)
    assert recommender.scores(vectors, [], [0])[0] == pytest.approx(-0.5)


def test_metrics_evaluated_halves_ties_and_wilson():
    """Skips/warm-up cannot inflate denominators; tied score pairs receive half credit."""
    rows = [
        dict(arm=a, action=b, score=c)
        for a, b, c in [
            ("warmup", "like", 9),
            ("rec", "skip", 4),
            ("random", "like", 1),
            ("rec", "dislike", 0),
            ("random", "dislike", 1),
            ("rec", "like", 2),
            ("random", "like", 2),
        ]
    ]
    result = metrics.results(rows)
    assert result["arms"]["rec"]["evaluated"] == 2
    assert result["arms"]["rec"]["skips"] == 1
    assert result["halves"][0]["random"]["likes"] == 1
    assert result["halves"][1]["random"]["likes"] == 1
    assert result["auc"] == 0.75
    assert result["arms"]["rec"]["wilson95"] == pytest.approx([0.0945312057, 0.9054687943])
    assert "Not enough data" in result["verdict"]
    assert metrics.auc([{"action": "like", "score": 1}]) is None


def test_import_filters_refill_freeze_and_transitive_templates(tmp_path):
    """Invalid/duplicate candidates must not consume target slots; similarity chains must union."""
    source, stage = tmp_path / "archive", tmp_path / "stage"
    source.mkdir()
    stage.mkdir()
    rng = np.random.default_rng(91)
    for i in range(20):
        Image.fromarray(
            rng.integers(0, 256, (400, 1600, 3) if i == 19 else (310, 310, 3), dtype=np.uint8)
        ).save(source / f"{i}.png")
    with Image.open(source / "0.png") as original:
        original.save(source / "near.bmp")
    (source / "copy.png").write_bytes((source / "0.png").read_bytes())
    Image.new("RGB", (10, 10)).save(source / "small.png")
    (source / "bad.png").write_text("invalid")
    records, population, rejected = sample(source.resolve(), 0, 42, stage)
    assert len(records) == 20 and population == 24 and rejected == 4
    assert len({r["sha256"] for r in records}) == 20
    assert all(max(Image.open(stage / r["image"]).size) <= 1080 for r in records)
    # A-B and B-C pass; A-C does not. Greedy representatives would miss C.
    angles = np.array([0, 0.3, 0.6])
    images = np.c_[np.cos(angles), np.sin(angles)]
    assert template_clusters(images, [0, 2**64 - 1, 0xAAAAAAAAAAAAAAAA]) == [0, 0, 0]
    with pytest.raises(ValueError, match="exhausted"):
        sample(source.resolve(), 21, 42, stage)


def test_item_vector_centering_and_missing_ocr():
    """Missing OCR contributes zeros, and passing text gets the specified relative weight."""
    images = np.array([[1, 0], [0, 1], [-1, 0]], dtype=np.float32)
    texts = np.array([[1, 0], [0, 0], [-1, 0]], dtype=np.float32)
    values = item_vectors(images, texts, np.array([True, False, True]))
    assert np.linalg.norm(values, axis=1) == pytest.approx([1, 1, 1])
    assert values[1, 2:].tolist() == [0, 0]
    assert np.linalg.norm(values[0, 2:]) / np.linalg.norm(values[0, :2]) == pytest.approx(0.5)


def test_admin_hash_exclusion_and_erasure(store):
    """Operator commands revoke cookies and remove tester events without touching the catalog."""
    instance, session = store
    token = instance.invite("second")
    with instance.connect() as db:
        assert token not in str([tuple(r) for r in db.execute("SELECT * FROM tester")])
    instance.feed(session)
    for cmd in ("exclude", "delete"):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "memes.admin",
                "--data",
                str(instance.data),
                cmd,
                "--user-id",
                str(session["user_id"]),
            ],
            check=True,
            capture_output=True,
        )
        if cmd == "exclude":
            assert instance.results(session)["excluded"]
    assert instance.authenticate("invalid") is None
    with instance.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM event").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM impression").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM catalog").fetchone()[0] == 300
    assert json.loads((Path(instance.data) / "catalog/catalog.json").read_text())["pins"][
        "synthetic"
    ]
