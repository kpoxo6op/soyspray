"""Serialized WAL transactions and fill-once impression events."""

import hashlib
import json
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from . import metrics, recommender
from .catalog import Catalog


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Refused(ValueError):
    pass


class Store:
    def __init__(self, data):
        self.data = Path(data)
        self.catalog = Catalog(self.data / "catalog")
        self.lock = threading.RLock()
        self.rng = np.random.default_rng()
        with self.connect() as db:
            db.executescript(Path(__file__).with_name("schema.sql").read_text())
            old = db.execute("SELECT DISTINCT catalog_version FROM catalog").fetchall()
            if old and {r[0] for r in old} != {self.catalog.version}:
                raise ValueError("Refusing catalog replacement under existing history")
            db.executemany(
                "INSERT OR IGNORE INTO catalog VALUES (?,?,?,?,?,?)",
                [
                    (
                        i,
                        r["sha256"],
                        r["cluster_id"],
                        r["kmeans_id"],
                        r["image"],
                        self.catalog.version,
                    )
                    for i, r in enumerate(self.catalog.items)
                ],
            )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.data / "memes.sqlite3", timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA secure_delete=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.lock, self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            yield db

    def invite(self, name):
        token = secrets.token_urlsafe(32)
        plan = recommender.warmup_plan(self.catalog, self.rng)
        with self.transaction() as db:
            db.execute(
                "INSERT INTO tester(name,token_hash,created_at,warmup_plan) VALUES(?,?,?,?)",
                (name, digest(token), now(), json.dumps(plan)),
            )
        return token

    def exchange(self, token):
        with self.transaction() as db:
            user = db.execute(
                "SELECT user_id FROM tester WHERE token_hash=?", (digest(token),)
            ).fetchone()
            if user is None:
                return None
            cookie, session = secrets.token_urlsafe(32), secrets.token_hex(16)
            db.execute(
                "INSERT INTO session VALUES(?,?,?,?,?)",
                (
                    session,
                    user[0],
                    digest(cookie),
                    now(),
                    (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
                ),
            )
        return cookie

    def authenticate(self, cookie):
        with self.connect() as db:
            return db.execute(
                "SELECT * FROM session WHERE cookie_hash=? AND expires_at>?",
                (digest(cookie), now()),
            ).fetchone()

    def event(self, db, user, impression, kind, payload):
        db.execute(
            "INSERT INTO event(user_id,impression_id,kind,occurred_at,payload) VALUES(?,?,?,?,?)",
            (user, impression, kind, now(), json.dumps(payload, sort_keys=True)),
        )

    def commit_pick(self, db, session, pick, seq):
        i, arm, prob, rank, score = pick
        user = session["user_id"]
        try:
            db.execute(
                "INSERT INTO impression(user_id,session_id,meme_id,cluster_id,arm,assignment_prob,rank,score,algo_version,catalog_version,served_at,served_seq) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    user,
                    session["session_id"],
                    i,
                    int(self.catalog.clusters[i]),
                    arm,
                    prob,
                    rank,
                    score,
                    recommender.ALGO_VERSION,
                    self.catalog.version,
                    now(),
                    seq,
                ),
            )
        except sqlite3.IntegrityError:
            self.event(db, user, None, "refused-repeat", {"meme_id": i})
            return False
        return True

    def fill(self, db, session):
        user = session["user_id"]
        history = db.execute(
            "SELECT * FROM impression WHERE user_id=? ORDER BY served_seq", (user,)
        ).fetchall()
        plan = json.loads(
            db.execute("SELECT warmup_plan FROM tester WHERE user_id=?", (user,)).fetchone()[0]
        )
        missing = 3 - sum(r["action"] is None for r in history)
        for _ in range(missing):
            pick = recommender.select(self.catalog, history, plan, self.rng)
            if pick is None:
                break
            if not self.commit_pick(db, session, pick, len(history)):
                break
            history = db.execute(
                "SELECT * FROM impression WHERE user_id=? ORDER BY served_seq", (user,)
            ).fetchall()

    def feed_rows(self, db, user):
        return db.execute(
            "SELECT * FROM impression WHERE user_id=? AND action IS NULL ORDER BY served_seq",
            (user,),
        ).fetchall()

    def public_feed(self, rows):
        return {
            "items": [
                {
                    "impression_id": r["impression_id"],
                    "image": f"/images/{r['meme_id']}",
                    "sequence": r["served_seq"],
                }
                for r in rows
            ],
            "exhausted": not rows,
        }

    def feed(self, session):
        with self.transaction() as db:
            self.fill(db, session)
            return self.public_feed(self.feed_rows(db, session["user_id"]))

    def mutate(self, session, impression_id, kind, payload):
        user = session["user_id"]
        refusal = None
        with self.transaction() as db:
            head = db.execute(
                "SELECT * FROM impression WHERE user_id=? AND action IS NULL ORDER BY served_seq LIMIT 1",
                (user,),
            ).fetchone()
            owned = db.execute(
                "SELECT * FROM impression WHERE user_id=? AND impression_id=?",
                (user, impression_id),
            ).fetchone()
            if owned is None or head is None or head["impression_id"] != impression_id:
                self.event(
                    db,
                    user,
                    owned["impression_id"] if owned else None,
                    "refused-repeat",
                    {"request": kind, "requested_id": impression_id},
                )
                refusal = "That impression is no longer current."
            elif kind == "render":
                if head["rendered_at"] is None:
                    db.execute(
                        "UPDATE impression SET rendered_at=? WHERE impression_id=?",
                        (now(), impression_id),
                    )
                    self.event(db, user, impression_id, "render", {})
            elif head["rendered_at"] is None:
                refusal = "Render the current image before reacting."
            else:
                timestamp = now()
                elapsed = max(
                    0,
                    int(
                        (
                            datetime.fromisoformat(timestamp)
                            - datetime.fromisoformat(head["rendered_at"])
                        ).total_seconds()
                        * 1000
                    ),
                )
                hidden = min(elapsed, payload["hidden_ms"])
                db.execute(
                    "UPDATE impression SET action=?,acted_at=?,response_ms=?,hidden_ms=?,client_seq=? WHERE impression_id=?",
                    (
                        payload["action"],
                        timestamp,
                        max(0, elapsed - hidden),
                        hidden,
                        payload["client_seq"],
                        impression_id,
                    ),
                )
                self.event(
                    db,
                    user,
                    impression_id,
                    "action",
                    {**payload, "hidden_ms": hidden, "response_ms": max(0, elapsed - hidden)},
                )
                self.fill(db, session)
            response = self.public_feed(self.feed_rows(db, user))
        if refusal:
            raise Refused(refusal)
        return response

    def results(self, session):
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM impression WHERE user_id=? ORDER BY served_seq",
                (session["user_id"],),
            ).fetchall()
            excluded = bool(
                db.execute(
                    "SELECT excluded FROM tester WHERE user_id=?", (session["user_id"],)
                ).fetchone()[0]
            )
        return metrics.results(rows, excluded)

    def image(self, session, meme_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT c.image FROM catalog c JOIN impression i USING(meme_id) WHERE i.user_id=? AND i.meme_id=?",
                (session["user_id"], meme_id),
            ).fetchone()
        if row is None:
            return None
        path = (self.data / "catalog" / row[0]).resolve()
        if not path.is_relative_to((self.data / "catalog" / "images").resolve()):
            raise ValueError("Invalid catalog image path")
        return path
