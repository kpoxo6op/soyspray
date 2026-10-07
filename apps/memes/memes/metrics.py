"""Evaluated denominators and descriptive uncertainty for adaptive feeds."""

import math

import numpy as np


def summary(rows):
    likes = sum(r["action"] == "like" for r in rows)
    dislikes = sum(r["action"] == "dislike" for r in rows)
    skips = sum(r["action"] == "skip" for r in rows)
    n = likes + dislikes
    interval = None
    if n:
        p, z = likes / n, 1.959963984540054
        center = (p + z * z / (2 * n)) / (1 + z * z / n)
        radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        interval = [max(0, center - radius), min(1, center + radius)]
    return {
        "impressions": len(rows),
        "likes": likes,
        "dislikes": dislikes,
        "skips": skips,
        "evaluated": n,
        "like_rate": likes / n if n else None,
        "wilson95": interval,
    }


def auc(rows):
    positive = np.array([r["score"] for r in rows if r["action"] == "like"])
    negative = np.array([r["score"] for r in rows if r["action"] == "dislike"])
    if not len(positive) or not len(negative):
        return None
    negative.sort()
    lower = np.searchsorted(negative, positive, side="left")
    upper = np.searchsorted(negative, positive, side="right")
    return float(np.sum((lower + upper) / 2) / (len(positive) * len(negative)))


def results(rows, excluded=False):
    evaluated = [
        r for r in rows if r["arm"] in ("rec", "random") and r["action"] in ("like", "dislike")
    ]
    cut = len(evaluated) // 2

    def split(subset):
        return {a: summary([r for r in subset if r["arm"] == a]) for a in ("rec", "random")}

    arms = split(rows)
    rec, random = arms["rec"], arms["random"]
    if min(rec["evaluated"], random["evaluated"]) < 30:
        verdict = "Not enough data yet; rate at least 30 picks from each group."
    elif rec["like_rate"] > random["like_rate"]:
        verdict = "You liked the recommender’s picks more often than the random picks."
    elif rec["like_rate"] < random["like_rate"]:
        verdict = "You liked the random picks more often than the recommender’s picks."
    else:
        verdict = "Both groups have the same like rate so far."
    return {
        "arms": arms,
        "warmup": summary([r for r in rows if r["arm"] == "warmup"]),
        "halves": [split(evaluated[:cut]), split(evaluated[cut:])],
        "auc": auc([r for r in evaluated if r["arm"] == "random"]),
        "verdict": verdict,
        "excluded": excluded,
    }
