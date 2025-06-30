## API Integration Commands - Issue #39

**Check existing root folders**

```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" http://192.168.1.131:8787/api/v1/rootfolder | jq '.'
```

**Get quality profiles**

```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" http://192.168.1.131:8787/api/v1/qualityprofile | jq '.[] | {id: .id, name: .name}'
```

**Get metadata profiles**

```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" http://192.168.1.131:8787/api/v1/metadataprofile | jq '.[] | {id: .id, name: .name}'
```

**Add BooksLibrary root folder**

```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" -H "Content-Type: application/json" -X POST http://192.168.1.131:8787/api/v1/rootfolder -d '{"name": "BooksLibrary", "path": "/downloads/BooksLibrary/", "defaultQualityProfileId": 1, "defaultMetadataProfileId": 1, "accessible": true, "freeSpace": 0, "unmappedFolders": []}'
```

**Verify root folder added**

```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" http://192.168.1.131:8787/api/v1/rootfolder | jq '.[] | {id: .id, name: .name, path: .path, accessible: .accessible}'
```

**Test Calibre-Web OPDS feed**

```bash
curl -s http://192.168.1.132:8083/opds | head -10
```

**Check import list schemas**

```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" http://192.168.1.131:8787/api/v1/importlist/schema | jq '.[] | {name: .name, implementation: .implementation}'
```

**Result**: Integration complete via file sharing - Readarr downloads to `/downloads/BooksLibrary/`, Calibre-Web import job processes automatically.

---

## K8s Integration Points

### 1. Enhanced Bootstrap Script
**File**: `bootstrap-scripts-cm.yaml`
```bash
# TODO: Add root folder API integration to existing qBittorrent bootstrap
# - Check if BooksLibrary root folder exists
# - Add root folder if missing (idempotent)
# - Verify root folder accessibility
# - Log all operations for debugging
```

### 2. Root Folder Payload
**File**: `rootfolder_payload.json` (new)
```json
# TODO: Create JSON payload for root folder creation
# - Use dynamic profile IDs from API discovery
# - Include all required fields from manual testing
# - Make configurable via environment variables
```

### 3. Kustomization Update
**File**: `kustomization.yaml`
```yaml
# TODO: Add new configMap generator for rootfolder payload
# - Include rootfolder_payload.json in configMapGenerator
# - Mount in bootstrap job alongside qbittorrent payload
```

### 4. Bootstrap Job Enhancement
**File**: `bootstrap-job.yaml`
```yaml
# TODO: Mount rootfolder payload in bootstrap container
# - Add rootfolder-payloads volume mount
# - Ensure proper ordering after qBittorrent integration
```
