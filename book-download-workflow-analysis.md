# qBittorrent → Readarr Book Download Workflow Analysis & Optimization

## Current Setup Analysis

### Infrastructure
- **qBittorrent**: Downloads to `/downloads/incoming/books` and `/downloads/incoming/incomplete`
- **Readarr**: Monitors `/downloads/incoming/books` and organizes books in `/downloads/BooksLibrary`
- **Shared Storage**: Single `qbittorrent-downloads` PVC (ReadWriteMany, 10Gi) mounted by both applications
- **Automation**: Dingu Telegram bot for search/download requests via Prowlarr

### Current Workflow Issues

1. **Messy Folder Structure**: qBittorrent creates subfolders based on torrent names, causing inconsistent paths
2. **Manual Intervention**: Downloads don't always get picked up by Readarr automatically
3. **Duplicate Handling**: No clear deduplication strategy when same book exists in different formats
4. **File Naming**: Inconsistent naming conventions between download sources and Readarr expectations

## Streamlined Solutions

### Option 1: Enhanced Readarr Integration (Recommended)
**Best for**: Automated library management with proper metadata

#### Implementation Steps:

1. **Optimize qBittorrent Configuration**
   ```ini
   # Enhanced qBittorrent settings
   [BitTorrent]
   Session\DefaultSavePath=/downloads/incoming/books
   Session\TempPath=/downloads/incoming/incomplete
   Session\AutoDeleteAddedTorrentFile=IfAdded
   Session\CreateTorrentSubfolder=false  # Prevents messy subfolders
   
   [Preferences]
   Downloads\SavePath=/downloads/incoming/books
   Downloads\TempPath=/downloads/incoming/incomplete
   Downloads\FinishedTorrentExportDir=/downloads/incoming/books/.finished
   Downloads\TorrentExportDir=/downloads/incoming/books/.torrents
   ```

2. **Configure Readarr Completed Download Handling**
   - Enable "Completed Download Handling"
   - Set "Remove Completed Downloads" to true
   - Configure category matching: `ebooks`
   - Set proper file naming format

3. **Automated Post-Processing Script**
   ```bash
   #!/bin/bash
   # Auto-organize script for better file structure
   DOWNLOAD_DIR="/downloads/incoming/books"
   
   # Move files from subdirs to main download dir
   find "$DOWNLOAD_DIR" -mindepth 2 -type f \( -name "*.epub" -o -name "*.pdf" -o -name "*.mobi" \) -exec mv {} "$DOWNLOAD_DIR/" \;
   
   # Remove empty directories
   find "$DOWNLOAD_DIR" -type d -empty -delete
   
   # Trigger Readarr manual import scan
   curl -X POST "http://readarr.media.svc.cluster.local:8787/api/v1/command" \
     -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
     -H "Content-Type: application/json" \
     -d '{"name": "ManualImport", "path": "/downloads/incoming/books"}'
   ```

### Option 2: Direct Download Management
**Best for**: Simple, direct control over downloads

#### Implementation Steps:

1. **Simplified Directory Structure**
   ```
   /downloads/
   ├── incoming/          # qBittorrent downloads
   │   ├── books/         # Completed downloads
   │   └── incomplete/    # In-progress downloads
   ├── processing/        # Temporary processing area
   └── BooksLibrary/      # Final organized library
   ```

2. **Enhanced Dingu Bot Integration**
   - Direct qBittorrent management
   - Automatic file organization
   - Progress tracking and notifications

### Option 3: Hybrid Approach with Automation (Most Comprehensive)

#### Components:

1. **Smart Download Processor**
   - Monitors qBittorrent completion
   - Automatically processes files
   - Handles naming and organization
   - Integrates with Readarr API

2. **Enhanced Workflow**
   ```mermaid
   graph TD
     A[User Request via Dingu Bot] --> B[Search Prowlarr]
     B --> C[Add to Readarr via API]
     C --> D[Readarr sends to qBittorrent]
     D --> E[qBittorrent Downloads]
     E --> F[Download Processor]
     F --> G[File Organization]
     G --> H[Readarr Import]
     H --> I[Library Update]
   ```

## Recommended Implementation: Enhanced Readarr Integration

### Step 1: Update qBittorrent Configuration

```yaml
# Enhanced qBittorrent ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: qbittorrent-conf
  namespace: media
data:
  qBittorrent.conf: |-
    [AutoRun]
    enabled=true
    program=/scripts/post-download.sh "%F" "%N" "%L"

    [BitTorrent]
    Session\AddTorrentStopped=false
    Session\DefaultSavePath=/downloads/incoming/books
    Session\Port=49160
    Session\QueueingSystemEnabled=true
    Session\SSL\Port=9007
    Session\ShareLimitAction=Stop
    Session\TempPath=/downloads/incoming/incomplete
    Session\CreateTorrentSubfolder=false

    [Preferences]
    Connection\PortRangeMin=49160
    Connection\UPnP=false
    Downloads\SavePath=/downloads/incoming/books
    Downloads\TempPath=/downloads/incoming/incomplete
    Downloads\FinishedTorrentExportDir=/downloads/incoming/books/.finished
    Downloads\TorrentExportDir=/downloads/incoming/books/.torrents
    WebUI\Address=*
    WebUI\ServerDomains=*
    WebUI\Username=admin
    WebUI\Password_PBKDF2="@ByteArray(6GuqwbIxFz5yNRLYBYPQIQ==:WyiZHyQ5Hgwnc71PuKmt1NKVAUD9tstuLBcJrP82SkQfalql8giGHqbOc7lly/xbqXEKuvcvrc3Dbg62PNPZBA==)"
```

### Step 2: Create Post-Download Processing Script

```bash
#!/bin/bash
# Post-download processor for qBittorrent
# Arguments: %F (content path), %N (torrent name), %L (category)

CONTENT_PATH="$1"
TORRENT_NAME="$2"
CATEGORY="$3"
READARR_API="http://readarr.media.svc.cluster.local:8787"
API_KEY="a85bb8f2ab19425f9c8c0bbc6f0aa29c"

echo "Processing completed download: $TORRENT_NAME"
echo "Content path: $CONTENT_PATH"
echo "Category: $CATEGORY"

# Only process ebook categories
if [[ "$CATEGORY" == "ebooks" ]]; then
    # Flatten directory structure
    if [[ -d "$CONTENT_PATH" ]]; then
        find "$CONTENT_PATH" -type f \( -name "*.epub" -o -name "*.pdf" -o -name "*.mobi" -o -name "*.azw*" \) -exec mv {} "/downloads/incoming/books/" \;
        # Remove empty directories
        find "$CONTENT_PATH" -type d -empty -delete
    fi
    
    # Trigger Readarr import scan
    curl -X POST "$READARR_API/api/v1/command" \
        -H "X-Api-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"name": "ManualImport", "path": "/downloads/incoming/books"}' \
        > /dev/null 2>&1
fi
```

### Step 3: Update Readarr Configuration

```json
{
  "enable": true,
  "name": "qBittorrent",
  "implementation": "QBittorrent",
  "implementationName": "qBittorrent",
  "protocol": "torrent",
  "priority": 1,
  "removeCompletedDownloads": true,
  "removeFailedDownloads": true,
  "configContract": "QBittorrentSettings",
  "fields": [
    {
      "name": "host",
      "value": "qbittorrent.media.svc.cluster.local"
    },
    {
      "name": "port",
      "value": 8080
    },
    {
      "name": "username",
      "value": "admin"
    },
    {
      "name": "password",
      "value": "123"
    },
    {
      "name": "category",
      "value": "ebooks"
    },
    {
      "name": "initialState",
      "value": 0
    },
    {
      "name": "sequentialOrder",
      "value": false
    },
    {
      "name": "firstAndLast",
      "value": false
    }
  ]
}
```

### Step 4: Enhanced Dingu Bot Integration

```python
# Enhanced workflow for Dingu bot
async def download_book(update, context):
    """Enhanced download workflow"""
    # 1. Search via Prowlarr
    results = await search_prowlarr(query)
    
    # 2. Add to Readarr (preferred method)
    if add_to_readarr:
        await add_book_to_readarr(selected_book)
        await trigger_readarr_search(selected_book)
    else:
        # 3. Fallback: Direct qBittorrent
        await add_torrent_to_qbittorrent(magnet_link, category="ebooks")
    
    # 4. Monitor progress
    await monitor_download_progress(torrent_hash)
    
    # 5. Notify completion
    await notify_download_complete(chat_id, book_title)
```

## Benefits of This Approach

1. **Automated Processing**: Files are automatically organized and imported
2. **Consistent Structure**: No more messy subfolders from torrent names
3. **Better Integration**: Readarr maintains complete control over library management
4. **Deduplication**: Readarr handles duplicate detection automatically
5. **Metadata**: Proper book metadata and organization
6. **Monitoring**: Complete download tracking and status updates

## Additional Optimizations

### 1. Quality Profiles
- Configure Readarr quality profiles for preferred formats (EPUB > PDF > MOBI)
- Set up automatic quality upgrades

### 2. Naming Convention
```
# Readarr naming format
{Book Title} - {Author Name}/{Author Name} - {Book Title}{ (Release Year)}.{Format}
```

### 3. Storage Optimization
- Implement automatic cleanup of old downloads
- Configure retention policies
- Set up backup strategies for library

### 4. Monitoring and Alerts
- Set up Prometheus metrics for download success rates
- Configure alerts for failed downloads
- Monitor storage usage

## Migration Steps

1. **Backup Current Setup**
   ```bash
   kubectl create backup readarr-config
   kubectl create backup qbittorrent-config
   ```

2. **Update Configurations**
   - Apply new qBittorrent ConfigMap
   - Update Readarr settings via API
   - Deploy post-processing script

3. **Test Workflow**
   - Download a test book
   - Verify automatic processing
   - Check Readarr import

4. **Monitor and Optimize**
   - Check download success rates
   - Monitor file organization
   - Adjust configurations as needed

This streamlined approach eliminates the "messy folders" issue while maintaining full automation and proper library management through Readarr.