# Readarr + qBittorrent + Prowlarr — Longhorn Integration Guide

## 1  Directory layout on the single RWX PVC
Path | Purpose | AccessMode
/books/downloads | qBittorrent writes incomplete and finished torrents | RWX
/books/library | Readarr places final, organised e‑books | RWX
/config inside Readarr pod | SQLite DB and queue state | RWO (separate PVC)
/config inside qBittorrent pod | fast‑resume data, torrents | RWO (separate PVC)

### Volume claims
* books-pvc – Longhorn, ReadWriteMany, 128 GiB, mounted at /books.
* readarr-config-pvc – Longhorn, ReadWriteOnce, 5 GiB, mounted at /config.
* qbittorrent-config-pvc – Longhorn, ReadWriteOnce, 2 GiB, mounted at /config.

This layout guarantees atomic rename() moves, single‑copy storage, and full node‑failure resilience.

## 2  Mandatory application settings
Component | Key setting | Exact value
Readarr | Completed Download Handling | Enabled
Readarr | Remove Completed Downloads | True or False per retention policy
Readarr | Download client category | ebooks
qBittorrent | Default save path | /books/downloads
qBittorrent | Category for Readarr torrents | ebooks
Prowlarr | Indexer routing | Accept all; Readarr never talks to indexers directly

## 3  Network policy
Allow egress TCP 443 and UDP 53 for Readarr, qBittorrent, Prowlarr; deny unsolicited ingress except MetalLB VIP and WireGuard subnet.

## 4  Verification tests (run after every change)
Test ID | Command / Action | Expected result
T‑01 | Scale qBittorrent to 0 → 1 replicas | Readarr queue shows “Pending – Download client unavailable”, then resumes automatically.
T‑02 | curl -X POST https://READARR/api/v1/book … | Entry appears under Activity → Queue within 2 s.
T‑03 | Wait for torrent finish | File appears in /books/library/ and disappears from /books/downloads when “Remove” enabled.
T‑04 | Kill Readarr pod during import | New pod restores full queue and library state from /config PVC.
T‑05 | nc -vz api.bookinfo.club 443 from Readarr container | Connection successful, proving external metadata reachability.

## 5  Stick‑and‑box diagrams
text |Telegram → Readarr API → Queue (SQLite) | | | ▼ | +----------------+ | | Prowlarr | | +----------------+ | | | ▼ | +----------------+ | | qBittorrent | | +----------------+ | | | ▼ | Longhorn VC /books (downloads + library) |

text | +-----------+ +-----------+ | | /config |––RWO–> PVC ––| Longhorn | | +-----------+ +-----------+ | ▲ ▲ | | | | Readarr pod qBittorrent pod |

## 6  Operational checklist
1. Deploy PVCs exactly as specified.
2. Confirm identical mount path /books in both Helm charts.
3. Keep Completed Download Handling enabled at all times.
4. Run tests T‑01 … T‑05 after upgrades or experimentation with pod schedules.
5. Update quality profiles and retention only in Readarr to preserve single source of truth.
