"""Async Readarr API client"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import aiohttp

from .config import settings

log = logging.getLogger("dingu.readarr")

class Readarr:
    """Async client for Readarr API operations"""

    def __init__(self) -> None:
        self._headers = {
            "X-Api-Key": settings.readarr_key,
            "Content-Type": "application/json",
        }
        self._base = settings.readarr_url
        self._session: Optional[aiohttp.ClientSession] = None

    async def open(self) -> None:
        """Initialize the HTTP session"""
        self._session = aiohttp.ClientSession(
            headers=self._headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        log.info("Readarr client session opened")

    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session:
            await self._session.close()
            log.info("Readarr client session closed")

    async def get(self, path: str, **params) -> Any:
        """Make async GET request to Readarr API"""
        if not self._session:
            raise RuntimeError("Session not opened. Call open() first.")

        url = f"{self._base}{path}"
        log.debug("GET %s with params: %s", url, params)

        async with self._session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def post(self, path: str, payload: Dict[str, Any]) -> Any:
        """Make async POST request to Readarr API"""
        if not self._session:
            raise RuntimeError("Session not opened. Call open() first.")

        url = f"{self._base}{path}"
        log.debug("POST %s with payload: %s", url, payload)

        async with self._session.post(url, json=payload) as response:
            response.raise_for_status()
            return await response.json()

    # ---------- Domain API methods ----------

    async def authors(self) -> List[Dict[str, Any]]:
        """Get all authors from Readarr"""
        return await self.get("/api/v1/author")

    async def books(self) -> List[Dict[str, Any]]:
        """Get all books from Readarr"""
        return await self.get("/api/v1/book")

    async def find_author_by_name(self, author_name: str) -> Optional[int]:
        """Find author ID by name (exact or partial match)"""
        authors = await self.authors()

        # Try exact match first
        for author in authors:
            if author_name.lower() == author["authorName"].lower():
                log.info("Found exact author match: %s (ID: %s)", author["authorName"], author["id"])
                return author["id"]

        # Try partial match
        for author in authors:
            if author_name.lower() in author["authorName"].lower():
                log.info("Found partial author match: %s (ID: %s)", author["authorName"], author["id"])
                return author["id"]

        log.info("No author found for: %s", author_name)
        return None

    async def add_author(self, author_info: Dict[str, Any]) -> int:
        """Add author to Readarr and return author ID"""
        # Check if author already exists
        existing_id = await self.find_author_by_name(author_info["authorName"])
        if existing_id:
            log.info("Author already exists: %s (ID: %s)", author_info["authorName"], existing_id)
            return existing_id

        payload = {
            "foreignAuthorId": str(author_info["foreignAuthorId"]),
            "authorName": author_info["authorName"],
            "authorNameLastFirst": author_info["authorNameLastFirst"],
            "rootFolderId": settings.root_id,
            "rootFolderPath": str(settings.root_path),
            "qualityProfileId": settings.quality_profile_id,
            "metadataProfileId": settings.metadata_profile_id,
            "monitored": True,
            "searchForMissingBooks": False,
            "monitorNewItems": "none",
        }

        result = await self.post("/api/v1/author", payload)
        author_id = result["id"]
        log.info("Added new author: %s (ID: %s)", author_info["authorName"], author_id)
        return author_id

    async def refresh_author(self, author_id: int) -> None:
        """Trigger author refresh in Readarr"""
        await self.post("/api/v1/command", {"name": "RefreshAuthor", "authorId": author_id})
        log.info("Triggered refresh for author ID: %s", author_id)

    async def find_book_by_title(self, title: str) -> Optional[int]:
        """Find book ID by title (fuzzy match)"""
        books = await self.books()

        title_words = set(word.lower() for word in title.split() if len(word) > 2)
        log.debug("Looking for books with words: %s", title_words)

        best_match = None
        best_score = 0

        for book in books:
            book_title = book["title"].lower()
            book_words = set(word.lower() for word in book_title.split() if len(word) > 2)

            # Calculate match score (common words / total unique words)
            common_words = title_words.intersection(book_words)
            if common_words:
                score = len(common_words) / len(title_words.union(book_words))
                log.debug("Book '%s' score: %.2f (common: %s)", book["title"], score, common_words)

                # FIXED: Require stricter matching (70% instead of 30%) to prevent random matches
                if score > best_score and score > 0.7:  # Minimum 70% match
                    best_score = score
                    best_match = book

        if best_match:
            log.info("Found best book match: '%s' (ID: %s, score: %.2f)",
                    best_match["title"], best_match["id"], best_score)
            return best_match["id"]

        log.info("No book found for title: %s", title)
        return None

    async def find_book_by_external_id(self, foreign_book_id: str) -> Optional[int]:
        """Find book ID by external/foreign ID (more reliable than title)"""
        books = await self.books()

        for book in books:
            if str(book.get("foreignBookId")) == str(foreign_book_id):
                log.info("Found book by external ID: '%s' (ID: %s)", book["title"], book["id"])
                return book["id"]

        log.info("No book found for external ID: %s", foreign_book_id)
        return None

    async def find_book_by_author(self, author_id: int, title: str) -> Optional[int]:
        """Find book by author ID and title (more targeted search)"""
        try:
            author_books = await self.get(f"/api/v1/book", authorId=author_id)

            title_words = set(word.lower() for word in title.split() if len(word) > 2)

            best_match = None
            best_score = 0

            for book in author_books:
                book_title = book["title"].lower()
                book_words = set(word.lower() for word in book_title.split() if len(word) > 2)

                common_words = title_words.intersection(book_words)
                if common_words:
                    score = len(common_words) / len(title_words.union(book_words))

                    # FIXED: Require stricter matching (70% instead of 30%) to prevent random matches
                    if score > best_score and score > 0.7:
                        best_score = score
                        best_match = book

            if best_match:
                log.info("Found book by author search: '%s' (ID: %s, score: %.2f)",
                        best_match["title"], best_match["id"], best_score)
                return best_match["id"]

            log.info("No book found for title '%s' under author ID %s", title, author_id)
            return None

        except Exception as e:
            log.error("Error searching books by author %s: %s", author_id, e)
            return None

    async def search_book(self, book_id: int) -> Optional[int]:
        """Start book search and return command ID"""
        result = await self.post("/api/v1/command", {"name": "BookSearch", "bookIds": [book_id]})
        command_id = result.get("id")
        log.info("Started book search for ID %s (command: %s)", book_id, command_id)
        return command_id

    async def lookup_book(self, term: str) -> List[Dict[str, Any]]:
        """Search for books by term"""
        return await self.get("/api/v1/book/lookup", term=term)

    async def lookup_author(self, term: str) -> List[Dict[str, Any]]:
        """Search for authors by term"""
        return await self.get("/api/v1/author/lookup", term=term)

    async def get_book_details(self, book_id: int) -> Dict[str, Any]:
        """Get detailed information about a book"""
        return await self.get(f"/api/v1/book/{book_id}")

    async def get_queue(self) -> Dict[str, Any]:
        """Get current download queue"""
        return await self.get("/api/v1/queue")

    async def get_commands(self) -> List[Dict[str, Any]]:
        """Get command history/status"""
        return await self.get("/api/v1/command")

    async def check_search_failed(self, command_id: int) -> bool:
        """Check if a search command completed with 0 results"""
        try:
            commands = await self.get_commands()
            for cmd in commands:
                if (cmd.get("id") == command_id and
                    cmd.get("status") == "completed" and
                    "0 reports downloaded" in cmd.get("message", "")):
                    log.info("Search command %s failed with 0 reports", command_id)
                    return True
        except Exception as e:
            log.error("Error checking search status for command %s: %s", command_id, e)
        return False

    async def check_download_started(self, book_id: int) -> Tuple[bool, str]:
        """Check if download actually started for a book

        Returns:
            tuple: (download_started, status_message)
        """
        try:
            # Check if book is in download queue
            queue = await self.get_queue()
            for item in queue.get("records", []):
                if item.get("bookId") == book_id:
                    status = item.get("status", "unknown")
                    title = item.get("title", "Unknown")

                    if status in ["downloading", "queued"]:
                        log.info("Download started for book ID %s: %s (%s)", book_id, title, status)
                        return True, f"📥 Download {status}: {title}"
                    elif status == "completed":
                        log.info("Download already completed for book ID %s: %s", book_id, title)
                        return True, f"✅ Download completed: {title}"
                    else:
                        log.info("Download status for book ID %s: %s (%s)", book_id, title, status)
                        return True, f"📊 Download {status}: {title}"

            log.info("Book ID %s not found in download queue yet", book_id)
            return False, "🔍 Searching for sources..."

        except Exception as e:
            log.error("Error checking download status for book ID %s: %s", book_id, e)
            return False, f"❓ Status check failed: {e}"

    async def get_book_files(self, book_id: int) -> List[Path]:
        """Get file paths for a book from Readarr"""
        file_paths = []

        try:
            book_details = await self.get_book_details(book_id)
            book_title = book_details.get("title", "Unknown")

            # Check if book has imported files
            if book_details.get("hasFile") and book_details.get("bookFiles"):
                for book_file in book_details.get("bookFiles", []):
                    path = book_file.get("path")
                    if path:
                        file_path = Path(path)
                        if file_path.exists():
                            log.info("Found imported file for book ID %s: %s", book_id, file_path)
                            file_paths.append(file_path)

            # Check download queue for completed downloads
            if not file_paths:
                queue = await self.get_queue()
                for item in queue.get("records", []):
                    if (item.get("bookId") == book_id and
                        item.get("status") == "completed" and
                        item.get("outputPath")):
                        output_path = Path(item.get("outputPath"))
                        if output_path.exists():
                            if output_path.is_dir():
                                # Scan directory for ebook files
                                from .storage import list_files
                                for file_path in list_files(output_path):
                                    log.info("Found file in download directory: %s", file_path)
                                    file_paths.append(file_path)
                            elif output_path.is_file():
                                log.info("Found direct download file: %s", output_path)
                                file_paths.append(output_path)

            # FIXED: Check filesystem for downloaded but not-yet-imported files
            # This handles the "limbo" state where files exist but hasFile=false
            if not file_paths:
                log.info("No imported files found for '%s', checking filesystem directly", book_title)
                from .storage import scan_download_dir
                filesystem_files = scan_download_dir(book_title)
                if filesystem_files:
                    log.info("Found %d files via filesystem search for '%s': %s",
                            len(filesystem_files), book_title, filesystem_files)
                    file_paths.extend(filesystem_files)

        except Exception as e:
            log.error("Error getting book files for ID %s: %s", book_id, e)

        return file_paths
