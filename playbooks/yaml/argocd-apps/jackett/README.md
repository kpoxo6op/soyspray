# jackett

## Container Tag in Use

`linuxserver/jackett:v0.22.1791-ls2`

## Purpose

Jackett aggregates private‑tracker search APIs behind a single endpoint.
Down‑stream tools such as **Readarr** query Jackett instead of each tracker directly.

## Minimal Validation (Before Moving On)

1. Web UI reachable at `http://192.168.1.129:9117/`.
2. At least one private tracker configured and returns results on a test search.

## Ladder Progression

**Next Step →** Deploy **`readarr`** once both validation checks pass.
