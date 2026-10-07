"""Selection-time scores, exclusions and hidden randomized allocation."""

import hashlib
import json
import os

import numpy as np

CONFIG = {
    "warmup": 15,
    "random_prob": 0.25,
    "top_k": 3,
    "dislike_weight": 0.5,
    "choose_top": 5,
    "queue": 2,
    "max_cluster_run": 3,
}
ALGO_VERSION = (
    os.environ.get("SOURCE_REVISION", "local")
    + ":"
    + hashlib.sha256(json.dumps(CONFIG, sort_keys=True).encode()).hexdigest()[:16]
)


def scores(vectors, likes, dislikes):
    result = np.zeros(len(vectors), dtype=np.float32)
    for indices, weight in ((likes, 1.0), (dislikes, -0.5)):
        if len(indices):
            cosines = vectors @ vectors[indices].T
            k = min(3, len(indices))
            result += weight * np.partition(cosines, -k, axis=1)[:, -k:].mean(axis=1)
    return result


def warmup_plan(catalog, rng):
    # Bipartite matching prevents exponential retries when templates span groups.
    choices = {
        int(g): [int(i) for i in rng.permutation(np.flatnonzero(catalog.kmeans == g))]
        for g in np.unique(catalog.kmeans)
    }
    owners, picked = {}, {}

    def assign(group, visited):
        for i in choices[group]:
            template = int(catalog.clusters[i])
            if template in visited:
                continue
            visited.add(template)
            previous = owners.get(template)
            if previous is None or assign(previous, visited):
                owners[template] = group
                picked[group] = i
                return True
        return False

    for group in rng.permutation(list(choices)):
        if not assign(int(group), set()):
            raise ValueError("Insufficient distinct templates for 15-cluster warm-up")
    return [int(i) for i in rng.permutation(list(picked.values()))]


def select(catalog, history, plan, rng):
    used = [r["cluster_id"] for r in history]
    eligible = np.flatnonzero(~np.isin(catalog.clusters, used))
    if not len(eligible):
        return None
    likes = [r["meme_id"] for r in history if r["action"] == "like"]
    dislikes = [r["meme_id"] for r in history if r["action"] == "dislike"]
    values = scores(catalog.vectors, likes, dislikes)
    seq = len(history)
    if seq < 15:
        i = plan[seq]
        if i not in eligible:
            raise ValueError("Warm-up plan violated eligibility")
        return i, "warmup", 1.0, None, float(values[i])
    random_arm = rng.random() < 0.25
    arm, prob = ("random", 0.25) if random_arm else ("rec", 0.75)
    if arm == "rec":
        if len(history) >= 3:
            last = [int(catalog.kmeans[r["meme_id"]]) for r in history[-3:]]
            if len(set(last)) == 1:
                eligible = eligible[catalog.kmeans[eligible] != last[0]]
        # Never violate the run constraint if only a blocked cluster remains.
        if not len(eligible):
            return None
        if likes or dislikes:
            order = eligible[np.argsort(-values[eligible], kind="stable")]
            i = int(rng.choice(order[:5]))
            rank = int(np.flatnonzero(order == i)[0]) + 1
            return i, arm, prob, rank, float(values[i])
    i = int(rng.choice(eligible))
    return i, arm, prob, None, float(values[i])
