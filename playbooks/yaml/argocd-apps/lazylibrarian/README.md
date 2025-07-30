# LazyLibrarian API Commands

## Core Workflow Commands

### Find and Add Book

```bash
# Find book (returns JSON with bookid)
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=findBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&name=Terry+Pratchett+Color+Magic"

# Add to database
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=addBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=BOOK_ID"
```

### Queue and Download Book

```bash
# Queue for download (Skipped → Wanted)
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=queueBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=BOOK_ID&type=eBook"

# Trigger download search
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=searchBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=BOOK_ID&wait=true"

# Check downloads
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=getSnatched&apikey=3723d36aa1e9e9955e3bf8982e94ee3c"
```

## Complete Workflow Example

```bash
# 1. Find and add book
BOOK_ID="34497"  # Extract from findBook response
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=addBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=$BOOK_ID"

# 2. Queue and search
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=queueBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=$BOOK_ID&type=eBook"
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=searchBook&apikey=3723d36aa1e9e9955e3bf8982e94ee3c&id=$BOOK_ID&wait=true"
```

## Flow: LazyLibrarian → Prowlarr → qBittorrent

1. **LazyLibrarian**: Find/queue books, manage metadata
2. **Prowlarr**: Provide torrent sources (RuTracker, TPB, etc.)
3. **qBittorrent**: Download files with category "books"

## File Processing Pipeline

1. **qBittorrent**: Downloads to `/downloads/books` (shared RWX PVC)
2. **LazyLibrarian**: Monitors `/downloads/books`, copies to `/books/Author/Title.epub` (dedicated PVC)
3. **OPDS**: Serves organized library at `/opds` endpoint

## OPDS Configuration

**Check OPDS Status:**

```bash
curl -s "https://lazylibrarian.soyspray.vip/api?cmd=getConfig&apikey=3723d36aa1e9e9955e3bf8982e94ee3c" | jq '.data.opds_enable'
```

**Test OPDS Endpoint:**

```bash
curl -s "https://lazylibrarian.soyspray.vip/opds"
```

## Integration Status

✅ **Tested and Working** - Complete API flow functional: findBook → addBook → queueBook → searchBook → qBittorrent download with "books" category → copy-only processing to organized library
