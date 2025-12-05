# Thumbnail Generation Error Report
## Immich Restore Test Instance

**Date**: 2025-12-05
**Instance**: immich-restore-test
**Namespace**: immich-restore-test
**Database**: immich-db-b (restore test database)

## Issue Summary

Some images in the restore test instance cannot be displayed in the UI, showing as "damaged" or "cannot be opened", even though:
- Original files exist and are valid
- Files can be downloaded successfully
- Files are not corrupted (verified via SHA256 checksums and file headers)

The issue affects a subset of assets where thumbnail generation fails with "not found" errors.

## Symptoms

1. **UI Behavior**: Some images show blurred thumbnails that cannot be opened in the viewer
2. **Download Works**: Original files can be downloaded successfully
3. **Error Pattern**: Thumbnail generation fails for specific assets with "not found" errors
4. **Partial Success**: Some images were fixed after manual thumbnail regeneration, but not all

## Investigation Findings

### Database State

- **Total Assets**: 254
- **Assets with Thumbnail Entries**: 254 (100%)
- **Assets with Preview Entries**: 254 (100%)
- **Assets with ORIGINAL Entries**: 0 (0%)

**Key Finding**: The `asset_file` table contains entries for `thumbnail` and `preview` types, but NO entries for `ORIGINAL` type. This is consistent across both production (immich-db-a) and restore test (immich-db-b) databases, suggesting this is expected Immich behavior.

### File System State

- **Original Files**: All exist at correct paths per database `originalPath` field
- **File Permissions**: All files have correct permissions (644, root:root)
- **File Integrity**: Verified via SHA256 checksums - files are not corrupted
- **File Headers**: Valid JPEG headers confirmed (FF D8 FF E0)
- **Thumbnail Files**: 474 generated files exist in `/usr/src/app/upload/thumbs/`
- **Directory Structure**: 158 directories exist in thumbs path

### Error Logs

**Thumbnail Generation Failures** (6 unique assets):
```
Thumbnail generation failed for asset 9ae281db-083d-4db7-9ffc-bd989a3dc7ab: not found
Thumbnail generation failed for asset 341de08e-3e41-488b-8211-2c668a6fec83: not found
Thumbnail generation failed for asset 2021f63f-f358-4600-acb7-5d219b404f21: not found
Thumbnail generation failed for asset c6517db2-a3d0-4dcb-9ebe-3ffb298bce84: not found
Thumbnail generation failed for asset 4cef6864-e5a2-47f8-99f1-15e2d070a99b: not found
Thumbnail generation failed for asset c179671b-7bce-4966-85e8-bfa44ae8a500: not found
```

**API Errors** (when trying to view assets):
```
Error: ENOENT: no such file or directory, access '/usr/src/app/upload/thumbs/.../5eb7c011-f91f-4e96-9ec3-cf7fe01ead74-thumbnail.webp'
Error: ENOENT: no such file or directory, access '/usr/src/app/upload/thumbs/.../5eb7c011-f91f-4e96-9ec3-cf7fe01ead74-preview.jpeg'
```

### Example Asset Analysis

**Broken Asset**: `5eb7c011-f91f-4e96-9ec3-cf7fe01ead74`
- **Original File**: `IMG_20250313_083932_626.jpg`
- **Database Path**: `/usr/src/app/upload/upload/8403ce5a-701f-4e93-b657-4fa6dc420684/2b/75/2b75d3e3-b42f-42c3-8279-23cfbb2b3e10.jpg`
- **File Exists**: YES
- **File Size**: 91,767 bytes
- **File Readable**: YES
- **File Valid**: YES (valid JPEG header)
- **Thumbnail Path**: `/usr/src/app/upload/thumbs/8403ce5a-701f-4e93-b657-4fa6dc420684/5e/b7/5eb7c011-f91f-4e96-9ec3-cf7fe01ead74-thumbnail.webp`
- **Thumbnail Exists**: NO
- **Preview Path**: `/usr/src/app/upload/thumbs/8403ce5a-701f-4e93-b657-4fa6dc420684/5e/b7/5eb7c011-f91f-4e96-9ec3-cf7fe01ead74-preview.jpeg`
- **Preview Exists**: NO

**Working Asset** (for comparison): `4765241b-7cdb-4e35-bdd3-d40d96a6c236`
- **Original File**: `IMG_20250217_090829_600.jpg`
- **File Exists**: YES
- **File Size**: 80,302 bytes
- **File Readable**: YES
- **Thumbnail Exists**: YES
- **Preview Exists**: YES

## Root Cause Analysis

### Primary Issue

The thumbnail generation process fails with "not found" errors for specific assets, even though:
1. The original files exist at the correct paths
2. Files are readable and valid
3. Permissions are correct
4. Database paths match actual file locations

### What Was Tried

1. **Manual Thumbnail Regeneration**: User triggered regeneration multiple times via UI
   - Result: Some images fixed, but not all
2. **Pod Restart**: Rolled the immich-server pod
   - Result: Server came back online, but thumbnail issues persisted
3. **File Verification**: Verified all original files exist and are valid
   - Result: Files confirmed intact and accessible
4. **Database Verification**: Checked asset_file table entries
   - Result: All assets have thumbnail/preview entries, but no ORIGINAL entries (normal)

## Current State

- **Total Assets**: 254
- **Assets with Generated Thumbnails**: ~248 (estimated, based on 474 thumbnail files)
- **Assets with Failed Thumbnail Generation**: 6 (confirmed in logs)
- **Assets with Partial Issues**: Unknown (some may have thumbnails but missing previews, or vice versa)
