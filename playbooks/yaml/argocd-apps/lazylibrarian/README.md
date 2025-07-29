# LazyLibrarian API Commands

## Core Workflow Commands

### Queue a Book (Change Status from Skipped to Wanted)

```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=queueBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=BOOK_ID&type=eBook"
```

### Search for a Book (Trigger Download Search)


```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=searchBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=BOOK_ID&wait=true"
```

### Get Downloaded Books with URLs

```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=getSnatched&apikey=3723d36aa1e9e9955e3bf8982e94ee3c"
```

## GUI Workflow (Browser)

1. **Search & Add**: Use "Search" button → find book → add to database
2. **Queue**: Book defaults to "Skipped" → change to "Wanted"
3. **Download**: Click green "Search" button → status changes to "Snatched"
4. **Wait**: qBittorrent downloads file, LazyLibrarian processes
5. **Access**: Navigate to **eBooks → Downloads** → download book file

## LazyLibrarian → Prowlarr → qBittorrent Flow

1. **LazyLibrarian**: Manages book metadata and queues
2. **Prowlarr**: Provides torrent/download sources (RuTracker, TPB, etc.)
3. **qBittorrent**: Downloads the actual files

**Workflow**:

1. Find/add book: `findBook` → `addBook`
2. Queue book: `queueBook` (changes status from "Skipped" to "Wanted")
3. Search downloads: `searchBook` (triggers Prowlarr search)
4. Get download URLs: `getSnatched` (returns `NZBurl` field with downloadable URLs)

## OPDS Configuration

OPDS (Open Publication Distribution System) enables direct book file downloads from the LazyLibrarian library.

### Validate OPDS Configuration

**Check OPDS Status:**
```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=getConfig&apikey=3723d36aa1e9e9955e3bf8982e94ee3c" | jq '.data.opds_enable'
```

**Test OPDS Endpoint:**
```bash
# Should return OPDS XML feed (not "OPDS not enabled" error)
curl -s "https://lazylibrarian.soyspray.vip/opds"
```

## File Processing Pipeline

1. **qBittorrent**: Downloads completed torrents to `/downloads/books` (shared RWX PVC)
2. **LazyLibrarian**: Monitors `/downloads/books` for completed downloads (same PVC)
3. **Library**: Processes and moves files to `/books/Author/Title.epub` (dedicated books PVC)
4. **OPDS**: Serves organized library via `/opds` endpoint for direct book downloads
