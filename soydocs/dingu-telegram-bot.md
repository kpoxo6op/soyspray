# Dingu Telegram Bot - High Level Plan

## Overview

Dingu is a Telegram bot that integrates with the existing arr stack (Readarr/Prowlarr/qBittorrent/Calibre-Web) in the soyspray Kubernetes cluster to search and download books on demand.

## User Flow

1. **User Input**: User sends book title to bot in Telegram
2. **Search**: Bot queries Prowlarr API for available torrents/releases
3. **Selection**: Bot presents search results with clickable buttons
4. **Download**: User selects result → Bot queues download via qBittorrent API
5. **Monitoring**: Bot polls download status until complete
6. **Delivery**: Bot sends .epub/.pdf file directly to user via Telegram

## Architecture

### Communication Flow

```
[User] ←→ [Telegram API] ←→ [Dingu Bot in K8s] ←→ [Arr Stack Services]
```

### Bot Hosting Strategy

- **Location**: Self-hosted inside Kubernetes cluster (as Deployment)
- **Communication**: Bot polls Telegram API (no webhook/ingress needed)
- **Network**: Bot accesses arr services via cluster DNS or MetalLB IPs

## Technical Implementation

### 1. Telegram Bot Communication

- **Method**: Long polling via `getUpdates` API endpoint
- **Advantages**:
  - No public HTTPS endpoint required
  - Works behind NAT/VPN
  - Simple K8s deployment
  - Only needs outbound internet access

### 2. Arr Stack Integration

Based on soyspray repo analysis:

**Prowlarr** (Indexer Aggregator)

- Service: `prowlarr.media.svc.cluster.local:9696` or `192.168.1.133:9696`
- API: `/api/v1/search?query=<title>&type=search&apikey=<key>`
- Purpose: Search across configured book indexers

**qBittorrent** (Downloader)

- Service: `qbittorrent.media.svc:8080`
- API: `/api/v2/torrents/add` (POST with magnet/torrent URL)
- Purpose: Handle actual torrent downloads

**Readarr** (Optional - Library Management)

- Service: `readarr.media.svc.cluster.local:8787` or `192.168.1.131:8787`
- API: Add books and trigger searches for proper library integration
- Purpose: Post-processing and library organization

**Calibre-Web** (Library Frontend)

- Purpose: Serve completed books (alternative delivery method)

### 3. Download Workflow Options

**Option A: Direct qBittorrent (Simpler)**

1. Search via Prowlarr API
2. Present results to user
3. Send selected magnet link directly to qBittorrent
4. Monitor download progress via qBittorrent API
5. Retrieve file from shared volume once complete

**Option B: Via Readarr (Better Integration)**

1. Add book to Readarr library via API
2. Trigger Readarr search (uses Prowlarr automatically)
3. Readarr manages qBittorrent download + post-processing
4. File ends up properly organized in library

### 4. File Delivery

**Primary Method**: Send file directly via Telegram

- Mount shared downloads PVC in bot container
- Use `sendDocument` API to upload .epub/.pdf to chat
- File size limit: ~50MB (sufficient for most ebooks)

**Alternative**: Provide download link

- Serve via Calibre-Web interface
- Temporary HTTP endpoint (if needed for large files)

## Kubernetes Deployment

### Resources Needed

- **Deployment**: Bot container with polling loop
- **ConfigMap**: Configuration (API endpoints, timeouts)
- **Secret**: API keys (Telegram token, Prowlarr key, qBittorrent creds)
- **PVC Mount**: Access to downloads volume (read-only)
- **Network Policy**: Allow egress to Telegram API + internal services

### Security

- Bot runs with minimal permissions
- API keys stored as K8s secrets
- No internet ingress required
- Optional: Restrict bot to authorized Telegram user IDs

## Implementation Steps

### Phase 1: Basic Bot Framework

- [ ] Create Python bot using `python-telegram-bot` library
- [ ] Implement polling and basic command handling
- [ ] Deploy as K8s container with secrets
- [ ] Test Telegram connectivity

### Phase 2: Search Integration

- [ ] Integrate Prowlarr API for book searches
- [ ] Parse and format search results
- [ ] Implement inline keyboard for result selection
- [ ] Handle "no results found" cases

### Phase 3: Download Integration

- [ ] Implement qBittorrent API integration
- [ ] Queue downloads based on user selection
- [ ] Add download status acknowledgment

### Phase 4: Monitoring & Delivery

- [ ] Implement download progress monitoring
- [ ] Add file retrieval from shared volume
- [ ] Implement file delivery via Telegram
- [ ] Handle completion notifications

### Phase 5: Polish & Error Handling

- [ ] Add rate limiting and user authorization
- [ ] Implement download cancellation
- [ ] Add error handling for failed downloads
- [ ] Create ArgoCD application manifest

## Network Architecture

### Internal Cluster Communication

```
Bot Pod → Prowlarr Service (search)
       → qBittorrent Service (download)
       → Shared PVC (file access)
```

### External Communication

```
Bot Pod → api.telegram.org (polling/responses)
```

### Service Discovery

- Use K8s DNS: `prowlarr.media.svc.cluster.local`
- Or MetalLB IPs: `192.168.1.133` (Prowlarr), `192.168.1.131` (Readarr)

## Configuration

### Environment Variables

```yaml
TELEGRAM_BOT_TOKEN: <from-secret>
PROWLARR_API_KEY: <from-secret>
PROWLARR_URL: "http://prowlarr.media.svc.cluster.local:9696"
QBITTORRENT_URL: "http://qbittorrent.media.svc:8080"
QBITTORRENT_USER: <from-secret>
QBITTORRENT_PASS: <from-secret>
DOWNLOADS_PATH: "/downloads"
AUTHORIZED_USERS: "user1,user2"  # Optional restriction
```

### Volume Mounts

```yaml
- name: downloads
  mountPath: /downloads
  readOnly: true
```

## Advantages of This Approach

1. **Leverages Existing Infrastructure**: Uses current arr stack without changes
2. **K8s Native**: Deployed as standard container, managed via ArgoCD
3. **Simple Network**: No ingress/webhook complexity
4. **Secure**: No public endpoints, API keys in secrets
5. **User Friendly**: Direct file delivery to Telegram chat
6. **Extensible**: Can add features like progress bars, scheduling, etc.

## Future Enhancements

- [ ] Support for audiobooks (integration with other arr apps)
- [ ] Bulk download requests
- [ ] Download scheduling/queuing
- [ ] Integration with reading progress tracking
- [ ] Multi-user support with individual libraries
- [ ] Web dashboard for download management

## References

- Existing arr stack configuration in `playbooks/yaml/argocd-apps/`
- Media volume setup in deployment manifests
- API documentation for Prowlarr, qBittorrent, Readarr
- Telegram Bot API documentation
