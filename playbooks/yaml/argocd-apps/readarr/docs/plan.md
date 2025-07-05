# Readarr Book Request Workflow

**Note:** Metadata service is automatically configured to `api.bookinfo.pro` in bootstrap job (fixes retired `api.bookinfo.club`).

## How Dingu Bot Should Add Books

When a user requests a book like "1984", the bot workflow is:

1. **Search for the book** - this returns the author
2. **Add the author first** (required before adding books)
3. **Find and monitor the specific book**

## Successful Author Add API Call

```bash
curl -s -X POST -H "Content-Type: application/json" -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
  -d '{
    "foreignAuthorId": "3706",
    "authorName": "George Orwell",
    "authorNameLastFirst": "Orwell, George",
    "rootFolderId": 1,
    "rootFolderPath": "/downloads/BooksLibrary",
    "qualityProfileId": 1,
    "metadataProfileId": 1,
    "monitored": false,
    "searchForMissingBooks": false,
    "monitorNewItems": "none"
  }' \
  "http://192.168.1.131:8787/api/v1/author"
```

**Response:**
```json
{
  "authorName": "George Orwell",
  "id": 1
}
```

## Key Points

- `monitored: false` - Don't download all author's books automatically
- `monitorNewItems: "none"` - Don't monitor new releases
- `searchForMissingBooks: false` - Don't immediately search for books
- Must include both `rootFolderId` and `rootFolderPath`
- Need to trigger `RefreshAuthor` command after adding to load book metadata

## Complete Dingu Bot Workflow (TESTED)

After adding author successfully:

1. **Trigger metadata refresh:**
```bash
curl -s -X POST -H "Content-Type: application/json" -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
  -d '{"name": "RefreshAuthor", "authorId": 1}' \
  "http://192.168.1.131:8787/api/v1/command"
```

2. **Find the specific book:**
```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
  "http://192.168.1.131:8787/api/v1/book" | \
  jq 'map(select(.title | contains("1984"))) | .[0] | {title: .title, id: .id, monitored: .monitored}'
```
**Result:** Found "1984" with ID 3

3. **Trigger search for specific book:**
```bash
curl -s -X POST -H "Content-Type: application/json" -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
  -d '{"name": "BookSearch", "bookIds": [3]}' \
  "http://192.168.1.131:8787/api/v1/command"
```
**Response:** `{"status": "queued", "name": "BookSearch"}`

## Summary for Dingu Bot

When user requests "Download 1984":
1. Search API finds George Orwell (author)
2. Add George Orwell as unmonitored author
3. Refresh author metadata to load his books
4. Find "1984" book ID
5. Trigger search for that specific book ID
6. Readarr will download it via qBittorrent when found

## Verification & Monitoring Commands

**Check command status:**
```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
  "http://192.168.1.131:8787/api/v1/command" | \
  jq 'map(select(.name == "BookSearch")) | .[0] | {status: .status, started: .started, ended: .ended}'
```

**Check download queue:**
```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
  "http://192.168.1.131:8787/api/v1/queue" | \
  jq '.records[] | {title: .title, status: .status, timeLeft: .timeleft}'
```

**Check download history:**
```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
  "http://192.168.1.131:8787/api/v1/history" | \
  jq '.records[0] | {eventType: .eventType, sourceTitle: .sourceTitle, date: .date}'
```

**Verify book has file:**
```bash
curl -s -H "X-Api-Key: a85bb8f2ab19425f9c8c0bbc6f0aa29c" \
  "http://192.168.1.131:8787/api/v1/book/3" | \
  jq '{title: .title, hasFile: .hasFile, monitored: .monitored}'
```

**Check actual files in library:**
```bash
kubectl exec -n media deployment/readarr -- ls -la "/downloads/BooksLibrary/George Orwell/"
```

## Successful Test Results ✅

**Download completed:** `2025-07-02T00:29:35Z`
**History event:** `bookFileImported` - "Nineteen Eighty-Four - George Orwell"
**File location:** `/downloads/BooksLibrary/George Orwell/Nineteen Eighty-Four - George Orwell.epub`
**File size:** `1.9MB`
**qBittorrent folder:** `George Orwell - Ninteteen Eighty-Four/`

## Bot Implementation Notes

- **Error handling**: Check command status before proceeding to next step
- **Timing**: RefreshAuthor takes ~5-10 seconds, BookSearch takes ~15-20 seconds
- **File verification**: Use history API to confirm successful import
- **User feedback**: Can provide download progress via queue API
- **Cleanup**: Consider adding author removal if download fails
