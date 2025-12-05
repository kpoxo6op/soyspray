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
