# Thumbnail Generation Error Report
## Immich Restore Test Instance

**Date**: 2025-12-05 (UTC)
**Instance**: immich-restore-test
**Namespace**: immich-restore-test
**Database**: immich-db-b (restore test database)

## Summary

After restoring the database and media assets, the majority of thumbnails were successfully regenerated. However, a minority of assets failed thumbnail generation, and regeneration attempts were unreliable - some assets were fixed after repeated attempts, while others remained broken.

## Current State

- **Total Assets**: 254
- **Assets with Generated Thumbnails**: ~248 (majority)
- **Assets with Failed Thumbnail Generation**: ~6 (minority)

## Issue

Some images cannot be displayed in the UI (showing as "damaged" or "cannot be opened"), even though:
- Original files exist and are valid
- Files can be downloaded successfully
- Files are not corrupted

The issue is missing thumbnail/preview files that failed to generate.

## Regeneration Reliability

Thumbnail regeneration is **not reliable** for the affected assets:
- Some assets were fixed after multiple regeneration attempts
- Some assets remain broken despite repeated attempts
- No clear pattern identified for why some succeed and others fail

## Examples: Successful Regeneration

### Asset 1: `ef219e63-2f42-46ad-8ee2-2cbc0bb209af`
- **Original File**: `IMG_20250518_183815_928.jpg`
- **Status**: Successfully regenerated after manual trigger
- **Timeline** (UTC / NZST):
  - `8:38:55 PM UTC` (`8:38:55 AM NZST`) - Last error (file missing)
  - `8:38:59 PM UTC` (`8:38:59 AM NZST`) - Preview created (216,717 bytes)
  - `8:38:59 PM UTC` (`8:38:59 AM NZST`) - Thumbnail created (22,484 bytes)
- **Result**: Display now works correctly

### Asset 2: `8e0b1642-91d4-481e-9154-af59a613e58a`
- **Status**: Successfully regenerated after manual trigger
- **Timeline** (UTC / NZST):
  - `8:55:54 PM UTC` (`8:55:54 AM NZST`) - Last error (preview file missing)
  - `8:55:59 PM UTC` (`8:55:59 AM NZST`) - Preview created
  - `8:55:59 PM UTC` (`8:55:59 AM NZST`) - Thumbnail created
- **Result**: Display now works correctly

## Comparison: Successful vs Failed Regeneration (Verbose Logging)

### Successful Regeneration: `9a088b09-0526-48a0-b25a-f00a6556e321`
- **Original File**: `Screenshot_20251017-233253.png`
- **Timeline** (UTC / NZST):
  - `9:09:42 PM UTC` (`9:09:42 AM NZST`) - Last error (preview file missing)
  - `9:09:45 PM UTC` (`9:09:45 AM NZST`) - `regenerate-thumbnail` job submitted (POST /api/assets/jobs 204)
  - `9:09:46 PM UTC` (`9:09:46 AM NZST`) - Thumbnail created (20,428 bytes)
  - `9:09:46 PM UTC` (`9:09:46 AM NZST`) - Preview created (177,748 bytes)
  - `9:09:47 PM UTC` (`9:09:47 AM NZST`) - First successful GET request (200 status)
- **Processing Time**: ~1-2 seconds from job submission to file creation
- **Result**: ✅ Success - Files created and display works

**Key Logs:**
```
[VERBOSE] {"assetIds":["9a088b09-0526-48a0-b25a-f00a6556e321"],"name":"regenerate-thumbnail"}
[DEBUG] GET /api/assets/9a088b09-0526-48a0-b25a-f00a6556e321/thumbnail?size=thumbnail 200 17.95ms
```

### Failed Regeneration (First Attempt): `0c5dc9f6-39a7-4eb5-a763-97f555ebed5c`
- **Original File**: `IMG_20251016_130940_551.jpg` (37,995 bytes - EXISTS)
- **First Attempt Timeline** (UTC / NZST):
  - `9:07:57 PM UTC` (`9:07:57 AM NZST`) - `refresh-metadata` job submitted
  - `9:08:01 PM UTC` (`9:08:01 AM NZST`) - `regenerate-thumbnail` job submitted (POST /api/assets/jobs 204)
  - `9:08:20 PM UTC` (`9:08:20 AM NZST`) - Second `regenerate-thumbnail` job submitted (POST /api/assets/jobs 204)
  - **No files created** - Thumbnail/preview still missing
- **Processing Time**: Jobs queued but never processed
- **Result**: ❌ Failure - Jobs accepted but not processed by microservices worker

**First Attempt Logs:**
```
[VERBOSE] {"assetIds":["0c5dc9f6-39a7-4eb5-a763-97f555ebed5c"],"name":"regenerate-thumbnail"}
[DEBUG] POST /api/assets/jobs 204 20.24ms  (job accepted)
[ERROR] Unable to send file: ENOENT: no such file or directory (files never created)
```

### Successful Regeneration (Retry): `0c5dc9f6-39a7-4eb5-a763-97f555ebed5c`
- **Original File**: `IMG_20251016_130940_551.jpg` (37,995 bytes - EXISTS)
- **Retry Timeline** (UTC / NZST):
  - `12:18:27 AM UTC` (`12:18:27 PM NZST`) - Last error (preview file missing)
  - `12:18:31 AM UTC` (`12:18:31 PM NZST`) - `regenerate-thumbnail` job submitted (POST /api/assets/jobs 204)
  - `12:18:31 AM UTC` (`12:18:31 PM NZST`) - Thumbnail created (5,824 bytes)
  - `12:18:31 AM UTC` (`12:18:31 PM NZST`) - Preview created (56,780 bytes)
  - `12:18:32 AM UTC` (`12:18:32 PM NZST`) - First successful GET request (200 status)
- **Processing Time**: ~1 second from job submission to file creation
- **Result**: ✅ Success - Files created and display works

**Retry Logs:**
```
[VERBOSE] {"assetIds":["0c5dc9f6-39a7-4eb5-a763-97f555ebed5c"],"name":"regenerate-thumbnail"}
[DEBUG] GET /api/assets/0c5dc9f6-39a7-4eb5-a763-97f555ebed5c/thumbnail?size=thumbnail 200 9.97ms
```

**Difference**: The successful asset processed the job immediately (1-2 seconds), while the first attempt's jobs were queued but never processed by the microservices worker. The retry attempt succeeded, demonstrating the unreliable nature of thumbnail regeneration - the same asset failed on first attempt but succeeded on retry.

## Example: Failed Assets

**Thumbnail Generation Failures** (from logs):
```
Thumbnail generation failed for asset 9ae281db-083d-4db7-9ffc-bd989a3dc7ab: not found
Thumbnail generation failed for asset 341de08e-3e41-488b-8211-2c668a6fec83: not found
Thumbnail generation failed for asset 2021f63f-f358-4600-acb7-5d219b404f21: not found
Thumbnail generation failed for asset c6517db2-a3d0-4dcb-9ebe-3ffb298bce84: not found
Thumbnail generation failed for asset 4cef6864-e5a2-47f8-99f1-15e2d070a99b: not found
Thumbnail generation failed for asset c179671b-7bce-4966-85e8-bfa44ae8a500: not found
```

**Note**: These 6 assets are from December 1-5, which is **after** the database restore date (2025-11-29). They exist in production but not in the restore test database, so these errors are expected.

## What Was Tried

1. **Manual Thumbnail Regeneration**: Multiple attempts via UI
   - Result: Some fixed, some not
2. **Pod Restart**: Rolled the immich-server pod
   - Result: No improvement for failed assets
3. **File Verification**: Confirmed all original files exist and are valid
   - Result: Files are intact and accessible

## Technical Details

- All original files exist at correct paths
- File permissions are correct (644, root:root)
- Files are valid (verified via SHA256 checksums and file headers)
- Database has thumbnail/preview entries for all assets
- Missing thumbnails/previews are the root cause of display issues
