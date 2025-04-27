# Media Diagram

## User Flow (User-Centric View)

```sh
   [ User ]
     │
     │ Searches for "Mystery at the Beach"
     ▼
  ┌───────────┐
  │  Readarr  │
  │  (front-end
  │   for user) ── (User sees books, picks new ones)
  └───────────┘
     │  (API call to check for matches)
     ▼
  ┌───────────────┐
  │   Prowlarr    │
  │   (finds best │
  │   torrent)    │
  └───────────────┘
     │  (torrent or magnet link returned)
     ▼
  ┌─────────────────┐
  │  qBittorrent    │
  │  (downloads .epub)
  └─────────────────┘
     │ (download completes)
     ▼
  ┌───────────┐
  │  Readarr  │
  │ (post-    │
  │ processing)│
  └───────────┘
     │ (rename, move final .epub)
     ▼
  ┌─────────────────┐
  │  Calibre-Web    │
  │ (ebook library  │
  │  for the user)  │
  └─────────────────┘
     │ (user sees new book)
     ▼
   [ User ]
     Reads "Mystery at the Beach"
```

## System Architecture (Volume-Centric View)

### Volumes and Flow

```sh
                ┌─────────────────────────┐
                │       Prowlarr          │
                └─────────┬───────────────┘
                          │  (searches .torrent/.magnet)
                          │
             ┌────────────┴─────────────┐
             │       Readarr            │
             │  /downloads + /books     │
             └───────┬─────────┬────────┘
                     │         │
                     │  (snatches torrent info)
                     │         │
  ┌──────────────────┴──────────────────┐
  │           qBittorrent               │
  │    /config + /downloads PVC         │
  └──────────────────┬──────────────────┘
                     │ (download completed EPUBs)
                     │
             ┌───────┴─────────┐
             │  (post-process) │
             └───────┬─────────┘
                     │ (final .epub)
                     v
             ┌───────────────────┐
             │  /books   Volume  │
             └───────────┬───────┘
                         │
                         v
             ┌───────────────────┐
             │   Calibre-Web     │
             │ /library PVC      │
             └───────────────────┘
```

## Volume/Path Overview

### qBittorrent

- Has two PVCs:
  - `/config` (RWO)
  - `/downloads` (RWX, shared as qbittorrent-downloads)

### Readarr

- Uses the same qbittorrent-downloads for `/downloads`
- Also mounts a RWO PVC for its own `/config`
- After download completes, it post-processes the final .epub into `/books`
  (which is also the same qbittorrent-downloads mount, often re-used or
  symlinked as the "books" folder)

### Calibre-Web

- Mounts a RWO PVC for `/config`
- Also mounts qbittorrent-downloads read-only as `/books`
- An initContainer automatically imports books from `/books` into
  `/config/Calibre_Library`

### Prowlarr

- Replaces Jackett but functions similarly
- Has a simple RWO PVC for `/config`; no direct file sharing with the others is
  needed
- Provides torrent/magnet metadata to Readarr or Radarr

These PVC arrangements allow qBittorrent, Readarr, and Calibre-Web to share or
access the same physical files for downloads and eBook libraries.

## User Story

Imagine your wife wants a brand-new eBook called "Mystery at the Beach". She
opens `Readarr` in her browser and types the title into the search box. In one
click, she selects it to add to her reading list. Behind the scenes, Readarr
quietly talks to `Prowlarr`, which tracks down a torrent with the best copy
available. `qBittorrent` automatically starts downloading it and, within a few
minutes, saves the completed .epub file.

Once the eBook is fully downloaded, Readarr spots it in the shared "downloads"
folder and does a quick "tidy-up": it renames and files the .epub where it
belongs. `Calibre-Web` then sees a fresh eBook in its "books" folder, imports it
into the online library, and displays it with a cover and summary.

Moments later, your wife opens Calibre-Web in her browser, sees "Mystery at the
Beach" waiting on the virtual shelf, and starts reading on her device. No
hassle, just a few clicks to discover, download, and read the latest book—all in
one place.
