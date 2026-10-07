"""Real HTTP evidence runner: reactions, SQL metrics, exclusions and scores."""

import http.cookiejar
import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from fixture import synthetic
from memes.catalog import normalize
from memes.server import server


class Client:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def request(self, path, payload=None):
        headers = {"Origin": self.base}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.base + path, json.dumps(payload).encode() if payload is not None else None, headers
        )
        with self.opener.open(req) as response:
            data = response.read()
            return (
                json.loads(data)
                if response.headers.get_content_type() == "application/json"
                else data
            )


def exercise(data, reactions=180):
    started = time.perf_counter()
    http = server(data, ("127.0.0.1", 0), secure=False)
    port = http.server_address[1]
    base = f"http://127.0.0.1:{port}"
    # Origin was unknown until port allocation. Handler uses origin by closure;
    # recreate at this known address before accepting connections.
    http.server_close()
    http = server(data, ("127.0.0.1", port), origin=base, secure=False)
    http.store.rng = np.random.default_rng(20261007)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    store = http.store
    client = Client(base)
    try:
        token = store.invite("local synthetic evaluation")
        client.request("/t/" + token)
        health = client.request("/healthz")
        feed = client.request("/api/feed")
        initial_ids = [r["impression_id"] for r in feed["items"]]
        client.request("/t/" + token)
        assert [r["impression_id"] for r in client.request("/api/feed")["items"]] == initial_ids
        vectors, labels = store.catalog.vectors, store.catalog.kmeans
        centers = normalize(np.array([vectors[labels == i].mean(axis=0) for i in range(15)]))
        taste = (vectors @ centers[[0, 1]].T).max(axis=1)
        threshold = float(np.quantile(taste, 0.75))
        count, first_id = 0, None
        for count in range(reactions):
            if not feed["items"]:
                break
            head = feed["items"][0]
            if first_id is None:
                first_id = head["impression_id"]
                assert client.request(head["image"])
            client.request("/api/render", {"impression_id": head["impression_id"]})
            with store.connect() as db:
                meme = db.execute(
                    "SELECT meme_id FROM impression WHERE impression_id=?", (head["impression_id"],)
                ).fetchone()[0]
            action = "like" if taste[meme] >= threshold else "dislike"
            feed = client.request(
                "/api/action",
                {
                    "impression_id": head["impression_id"],
                    "action": action,
                    "hidden_ms": 0,
                    "client_seq": count,
                },
            )
        else:
            count = reactions
        try:
            client.request(
                "/api/action",
                {"impression_id": first_id, "action": "like", "hidden_ms": 0, "client_seq": 999},
            )
            raise AssertionError("Repeat action accepted")
        except urllib.error.HTTPError as error:
            assert error.code == 409
        rendered_page = client.request("/results")
        assert b"Your results" in rendered_page
        result = client.request("/api/results")
        with store.connect() as db:
            user = db.execute("SELECT MAX(user_id) FROM tester").fetchone()[0]
            rows = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM impression WHERE user_id=? ORDER BY served_seq", (user,)
                )
            ]
            repeats = dict(
                db.execute(
                    "SELECT COUNT(*)-COUNT(DISTINCT meme_id) AS memes, COUNT(*)-COUNT(DISTINCT cluster_id) AS clusters FROM impression WHERE user_id=?",
                    (user,),
                ).fetchone()
            )
            refused = db.execute(
                "SELECT COUNT(*) FROM event WHERE user_id=? AND kind='refused-repeat'", (user,)
            ).fetchone()[0]
            sql = [
                dict(r)
                for r in db.execute(
                    "SELECT arm,assignment_prob,COUNT(*) AS selected,SUM(action='like') AS likes,SUM(action='dislike') AS dislikes,SUM(action='skip') AS skips FROM impression WHERE user_id=? GROUP BY arm,assignment_prob",
                    (user,),
                )
            ]
        assert (
            all(r["arm"] == "warmup" for r in rows[:15])
            and sum(r["arm"] == "warmup" for r in rows) == 15
        )
        assert len({store.catalog.kmeans[r["meme_id"]] for r in rows[:15]}) == 15
        assert repeats == {"memes": 0, "clusters": 0} and refused == 1
        for r in sql:
            if r["arm"] != "warmup":
                assert r["assignment_prob"] == (0.25 if r["arm"] == "random" else 0.75)
                assert result["arms"][r["arm"]]["likes"] == r["likes"]
                assert result["arms"][r["arm"]]["dislikes"] == r["dislikes"]
        for i in range(18, len(rows)):
            if rows[i]["arm"] == "rec":
                assert len({store.catalog.kmeans[r["meme_id"]] for r in rows[i - 3 : i + 1]}) > 1
        evaluated = [r for r in rows if r["arm"] != "warmup" and r["action"] in ("like", "dislike")]
        cut = len(evaluated) // 2
        for report, half in zip(result["halves"], [evaluated[:cut], evaluated[cut:]], strict=False):
            for arm in ("rec", "random"):
                selected = [r for r in half if r["arm"] == arm]
                assert report[arm]["likes"] == sum(r["action"] == "like" for r in selected)
                assert report[arm]["evaluated"] == len(selected)
        positives = [
            r["score"] for r in evaluated if r["arm"] == "random" and r["action"] == "like"
        ]
        negatives = [
            r["score"] for r in evaluated if r["arm"] == "random" and r["action"] == "dislike"
        ]
        direct_auc = (
            sum((a > b) + 0.5 * (a == b) for a in positives for b in negatives)
            / (len(positives) * len(negatives))
            if positives and negatives
            else None
        )
        assert result["auc"] == direct_auc
        return {
            "health": health,
            "actions": sum(r["action"] is not None for r in rows),
            "warmup": 15,
            "arm_sql": sql,
            "repeats": repeats,
            "refused_repeat": refused,
            "results_match_sql": True,
            "rates": {a: result["arms"][a]["like_rate"] for a in ("rec", "random")},
            "auc": result["auc"],
            "seconds": time.perf_counter() - started,
            "exhausted": feed["exhausted"],
        }
    finally:
        http.shutdown()
        http.server_close()
        thread.join()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--reactions", type=int, default=180)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.synthetic:
        synthetic(args.data, count=10000)
    report = exercise(args.data, args.reactions)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
