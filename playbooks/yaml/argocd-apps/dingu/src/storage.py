"""Filesystem operations for book file discovery"""

import logging
from pathlib import Path
from typing import List

log = logging.getLogger("dingu.storage")

# Supported ebook formats
SUPPORTED_EXT = {".epub", ".mobi", ".azw3", ".pdf"}

def list_files(root: Path) -> List[Path]:
    """Recursively find all supported ebook files in a directory"""
    try:
        return [p for p in root.rglob("*") if p.suffix.lower() in SUPPORTED_EXT and p.is_file()]
    except (PermissionError, OSError) as e:
        log.error("Error scanning directory %s: %s", root, e)
        return []

def scan_download_dir(title: str) -> List[Path]:
    """Search for book files matching title in downloads directory"""
    log.info("Searching filesystem directly for title: '%s'", title)
    root = Path("/downloads")

    if not root.exists():
        log.warning("Downloads directory %s does not exist", root)
        return []

    found_files = []
    title_lower = title.lower()

    # Split title into words for flexible matching
    title_words = [word.strip() for word in title_lower.split() if len(word.strip()) > 2]
    log.info("Searching for title words: %s", title_words)

    try:
        # Search for files with title in name
        for file_path in list_files(root):
            file_name_lower = file_path.name.lower()

            # Check if title matches exactly (existing behavior)
            if title_lower in file_name_lower:
                log.info("Found exact match: %s", file_path)
                found_files.append(file_path)
                continue

            # FIXED: Much stricter word matching - require ALL significant words to match
            # This prevents matching random books that share common words
            matches = sum(1 for word in title_words if word in file_name_lower)
            match_ratio = matches / len(title_words) if title_words else 0

            # Require ALL words to match (100% match ratio) for partial matches
            # This prevents "Tom Sawyer" from matching "Harry Potter" books with "Tom Riddle"
            if match_ratio >= 1.0:  # Changed from 0.5 to 1.0 - require ALL words
                log.info("Found strict word match (%d/%d words, %.1f%% match): %s", matches, len(title_words), match_ratio*100, file_path)
                found_files.append(file_path)

        # Search for directories with title in name and scan them
        for dir_path in root.rglob("*"):
            if (dir_path.is_dir() and title_lower in dir_path.name.lower()):
                log.info("Found potential directory: %s", dir_path)
                for file_path in list_files(dir_path):
                    if file_path not in found_files:
                        log.info("Found file in directory: %s", file_path)
                        found_files.append(file_path)

    except (PermissionError, OSError) as e:
        log.error("Error in filesystem search for '%s': %s", title, e)

    log.info("Filesystem search found %d files for '%s'", len(found_files), title)
    return found_files

def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes"""
    try:
        return file_path.stat().st_size / (1024 * 1024)
    except OSError:
        return 0.0
