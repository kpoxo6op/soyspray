"""Telegram bot handlers for Dingu"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from .readarr import Readarr
from .storage import scan_download_dir

log = logging.getLogger("dingu.telegram")

class Handlers:
    """Clean, testable Telegram bot handlers"""

    def __init__(self, readarr: Readarr) -> None:
        self.readarr = readarr
        self.last_request: Dict[int, int] = {}  # chat_id -> book_id
        self.waiting_tasks: Dict[int, asyncio.Task] = {}  # chat_id -> task

    # ---------- Commands ----------

    async def start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        await update.message.reply_text("🐕 Dingu ready – send a book title")

    async def help_cmd(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        await update.message.reply_text(
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/ping - Test bot response\n"
            "/status - Check latest request status\n\n"
            "Or just type the title you want to download!"
        )

    async def ping(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ping command"""
        await update.message.reply_text("pong")

    async def status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        chat_id = update.effective_chat.id
        book_id = self.last_request.get(chat_id)

        if not book_id:
            await ctx.bot.send_message(chat_id, "No recent request")
            return

        try:
            book_details = await self.readarr.get_book_details(book_id)
            status = "imported" if book_details.get("hasFile") else "queued"
            await ctx.bot.send_message(chat_id, f"Latest request status: {status}")
        except Exception as e:
            log.error("Error checking status for book ID %s: %s", book_id, e)
            await ctx.bot.send_message(chat_id, f"Error checking status: {e}")

    # ---------- Main text processor ----------

    async def handle_title(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle book title requests"""
        title = update.message.text.strip()
        chat_id = update.effective_chat.id

        log.info("Processing request for title: '%s' from chat %s", title, chat_id)
        await ctx.bot.send_message(chat_id, f'🔍 Searching for "{title}"')

        try:
            # Cancel any existing waiting task for this chat
            await self._cancel_existing_task(chat_id)

            # 1. FIRST check filesystem for existing files
            log.info("Checking filesystem first for title: '%s'", title)
            filesystem_files = scan_download_dir(title)
            if filesystem_files:
                log.info("Filesystem found %d files for '%s'", len(filesystem_files), title)
                await ctx.bot.send_message(chat_id, "📁 Found existing files!")
                await self._send_files(chat_id, title, filesystem_files, ctx)
                return

            # 2. Check if book already exists in Readarr
            book_id = await self.readarr.find_book_by_title(title)
            if book_id:
                log.info("Found existing book ID: %s for title '%s'", book_id, title)
                sent = await self._deliver_existing(chat_id, book_id, ctx, title)
                if sent:
                    return

            # 3. Full acquisition workflow
            log.info("No existing downloads found, starting acquisition for '%s'", title)
            await self._acquire_and_deliver(chat_id, title, ctx)

        except Exception as e:
            log.error("Error processing title '%s': %s", title, e)
            await ctx.bot.send_message(chat_id, f"❌ Error: {e}")

    # ---------- Private helpers ----------

    async def _cancel_existing_task(self, chat_id: int) -> None:
        """Cancel any existing waiting task for this chat"""
        if chat_id in self.waiting_tasks:
            self.waiting_tasks[chat_id].cancel()
            try:
                await self.waiting_tasks[chat_id]
            except asyncio.CancelledError:
                pass
            del self.waiting_tasks[chat_id]
            log.info("Cancelled previous waiting task for chat %s", chat_id)

    async def _deliver_existing(self, chat_id: int, book_id: int, ctx: ContextTypes.DEFAULT_TYPE, title: str) -> bool:
        """Try to deliver existing downloaded files"""
        file_paths = await self.readarr.get_book_files(book_id)

        if not file_paths:
            return False

        await self._send_files(chat_id, title, file_paths, ctx)
        return True

    async def _acquire_and_deliver(self, chat_id: int, title: str, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        """Full book acquisition workflow"""
        # Lookup book information
        lookup_results = await self.readarr.lookup_book(title)
        if not lookup_results:
            log.info("No books found in lookup for '%s'", title)
            await ctx.bot.send_message(chat_id, "📚 Nothing found")
            return

        book_info = lookup_results[0]
        author_title = book_info.get("authorTitle", "")

        # Extract author name from authorTitle
        author_name = author_title.split(book_info["title"])[0].strip()

        # Handle "Last, First" name format
        if "," in author_name:
            parts = [p.strip() for p in author_name.split(",")]
            if len(parts) == 2:
                author_name = f"{parts[1]} {parts[0]}".title()

        log.info("Extracted author name: '%s' from '%s'", author_name, author_title)

        # Lookup author information
        author_lookup = await self.readarr.lookup_author(author_name)
        if not author_lookup:
            log.info("Author lookup failed for '%s'", author_name)
            await ctx.bot.send_message(chat_id, f"❌ Author '{author_name}' not found")
            return

        # Find exact match or use first result
        author_info = None
        for candidate in author_lookup:
            if candidate["authorName"].lower() == author_name.lower():
                author_info = candidate
                break

        if not author_info:
            log.info("Exact author match not found for '%s', using fallback", author_name)
            author_info = author_lookup[0]
            log.info("Using fallback author: '%s'", author_info["authorName"])

        # Add author to Readarr
        author_id = await self.readarr.add_author(author_info)
        log.info("Author ID: %s for '%s'", author_id, author_name)
        await ctx.bot.send_message(chat_id, "✅ Author added")

        # Refresh author to get latest books
        await self.readarr.refresh_author(author_id)

        # Wait for refresh to complete (increased time for better reliability)
        await asyncio.sleep(20)

        # Find the book after refresh - try multiple methods for reliability
        book_id = None

        # Method 1: Try to find by external ID (most reliable)
        if book_info.get("foreignBookId"):
            book_id = await self.readarr.find_book_by_external_id(book_info["foreignBookId"])
            if book_id:
                log.info("Found book by external ID: %s", book_id)

        # Method 2: Try to find by author + title (more targeted)
        if not book_id:
            book_id = await self.readarr.find_book_by_author(author_id, title)
            if book_id:
                log.info("Found book by author search: %s", book_id)

        # Method 3: Fallback to general title search
        if not book_id:
            book_id = await self.readarr.find_book_by_title(title)
            if book_id:
                log.info("Found book by title search: %s", book_id)

        if not book_id:
            log.error("Book not found after refresh for '%s' (tried all methods)", title)
            await ctx.bot.send_message(chat_id, "❌ Book not found after refresh")
            return

        # Track this request
        self.last_request[chat_id] = book_id

        # Start book search
        log.info("Starting search for book ID %s ('%s')", book_id, title)
        command_id = await self.readarr.search_book(book_id)
        await ctx.bot.send_message(chat_id, "🔍 Search started")

        # Start waiting task
        task = asyncio.create_task(self._wait_and_deliver(chat_id, book_id, title, ctx, command_id))
        self.waiting_tasks[chat_id] = task

    async def _wait_and_deliver(self, chat_id: int, book_id: int, title: str, ctx: ContextTypes.DEFAULT_TYPE, command_id: Optional[int]) -> None:
        """Wait for download completion and deliver files"""
        log.info("Starting download wait for book ID %s in chat %s", book_id, chat_id)
        await ctx.bot.send_message(chat_id, "⏳ Waiting for download…")

        try:
            for attempt in range(30):  # Wait up to 5 minutes
                log.info("Download check attempt %d/30 for book ID %s", attempt + 1, book_id)

                # Shorter initial waits, longer later waits
                wait_time = 5 if attempt < 5 else 10
                await asyncio.sleep(wait_time)

                # Check if search failed early
                if command_id and await self.readarr.check_search_failed(command_id):
                    log.info("Search failed for book ID %s - no sources found", book_id)
                    await ctx.bot.send_message(chat_id, "😕 Sorry, this book isn't available right now")
                    await ctx.bot.send_message(chat_id,
                        "The book exists but no one is sharing it at the moment. "
                        "This happens with older, rare, or very new books.")
                    return

                # Check for completed files
                file_paths = await self.readarr.get_book_files(book_id)
                if file_paths:
                    log.info("Download completed! Found %d files for book ID %s", len(file_paths), book_id)
                    await self._send_files(chat_id, title, file_paths, ctx)
                    log.info("Successfully delivered %d files for book ID %s", len(file_paths), book_id)
                    return

                log.info("No files ready yet for book ID %s, continuing to wait...", book_id)

            # Timeout reached
            log.error("Download wait timed out for book ID %s after 30 attempts", book_id)
            await ctx.bot.send_message(chat_id, "⏰ Download timed out")

        except asyncio.CancelledError:
            log.info("Waiting task cancelled for book ID %s in chat %s", book_id, chat_id)
            await ctx.bot.send_message(chat_id, "🚫 Search cancelled - starting new request")
            raise
        except Exception as e:
            log.error("Error in waiting task for book ID %s: %s", book_id, e)
            await ctx.bot.send_message(chat_id, f"❌ Error: {e}")
        finally:
            # Clean up
            if chat_id in self.waiting_tasks:
                del self.waiting_tasks[chat_id]
                log.info("Cleaned up waiting task for chat %s", chat_id)

    async def _send_files(self, chat_id: int, title: str, file_paths: List[Path], ctx: ContextTypes.DEFAULT_TYPE) -> None:
        """Send multiple files to user"""
        log.info("Sending %d files for '%s'", len(file_paths), title)

        if len(file_paths) > 1:
            await ctx.bot.send_message(chat_id, f"📚 Found {len(file_paths)} format(s) - sending all:")

        sent_count = 0
        for file_path in file_paths:
            try:
                # Check file size (Telegram has 50MB limit)
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > 50:
                    await ctx.bot.send_message(chat_id,
                        f"⚠️ File too large to send: {file_path.name} ({file_size_mb:.1f}MB)")
                    continue

                with open(file_path, "rb") as f:
                    await ctx.bot.send_document(chat_id, f, filename=file_path.name)
                sent_count += 1
                log.info("Successfully sent file %d/%d: %s", sent_count, len(file_paths), file_path)

            except Exception as e:
                log.error("Error sending file %s: %s", file_path, e)
                await ctx.bot.send_message(chat_id, f"❌ Error sending {file_path.name}: {e}")

        if sent_count > 0:
            message = f"📚 Delivered!" if sent_count == 1 else f"📚 Delivered {sent_count}/{len(file_paths)} files"
            await ctx.bot.send_message(chat_id, message)
        else:
            await ctx.bot.send_message(chat_id, "❌ No files could be sent")
