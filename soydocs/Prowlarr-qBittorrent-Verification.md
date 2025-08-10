# Prowlarr → qBittorrent Essential Commands

**Summary:** Direct URLs from Prowlarr fail in qBittorrent. Working method: download torrent file from Prowlarr, upload file to qBittorrent.

## Working Method: File Upload

### Search Prowlarr

```bash
curl -s -H "X-Api-Key: 7057f5abbbbb4499a54941f51992a68c" \
  "http://192.168.50.213:9696/api/v1/search?query=SEARCH_TERM&cat=7020" | \
  jq '.[0] | {title: .title, downloadUrl: .downloadUrl}'
```

### Get Download URL and Download File

```bash
DOWNLOAD_URL=$(curl -s -H "X-Api-Key: 7057f5abbbbb4499a54941f51992a68c" \
  "http://192.168.50.213:9696/api/v1/search?query=SEARCH_TERM&cat=7020" | \
  jq -r '.[0].downloadUrl')

curl -s "$DOWNLOAD_URL" > /tmp/torrent-file.torrent
```

### qBittorrent Login

```bash
curl -c /tmp/qb_cookies -d "username=admin&password=123" \
  "http://192.168.50.207:8080/api/v2/auth/login"
```

### Upload to qBittorrent (WORKING)

```bash
curl -b /tmp/qb_cookies \
  -F "torrents=@/tmp/torrent-file.torrent" \
  -F "category=CATEGORY_NAME" \
  "http://192.168.50.207:8080/api/v2/torrents/add"
```

### Verify Upload

```bash
curl -b /tmp/qb_cookies -s "http://192.168.50.207:8080/api/v2/torrents/info" | \
  jq '.[] | select(.category == "CATEGORY_NAME")'
```

## API Keys

- **Prowlarr:** `7057f5abbbbb4499a54941f51992a68c`
- **qBittorrent:** `admin/123`
