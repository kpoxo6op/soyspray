import os
import asyncio
import logging
import requests
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dingu")

READARR = "http://192.168.1.131:8787"
KEY = "a85bb8f2ab19425f9c8c0bbc6f0aa29c"
ROOT_ID = 1
ROOT_PATH = "/downloads/BooksLibrary"
QP_ID = 1
MP_ID = 1
TOKEN = os.getenv("DINGU_TELEGRAM_BOT_TOKEN", "")
HEAD = {"X-Api-Key": KEY, "Content-Type": "application/json"}

last_request = {}
waiting_tasks = {}

def _post(path, data):
    log.info("POST %s", path)
    r = requests.post(f"{READARR}{path}", json=data, headers=HEAD, timeout=15)
    r.raise_for_status()
    return r.json()

def _get(path, params=None):
    log.info("GET %s", path)
    r = requests.get(f"{READARR}{path}", params=params, headers=HEAD, timeout=15)
    r.raise_for_status()
    return r.json()

def _find_author_id(author_name):
    # Try exact match first
    for a in _get("/api/v1/author"):
        if author_name.lower() == a["authorName"].lower():
            return a["id"]
    # Then try partial match
    for a in _get("/api/v1/author"):
        if author_name.lower() in a["authorName"].lower():
            return a["id"]
    return None

def _add_author(author_info):
    existing_id = _find_author_id(author_info["authorName"])
    if existing_id:
        return existing_id

    payload = {
        "foreignAuthorId": str(author_info["foreignAuthorId"]),
        "authorName": author_info["authorName"],
        "authorNameLastFirst": author_info["authorNameLastFirst"],
        "rootFolderId": ROOT_ID,
        "rootFolderPath": ROOT_PATH,
        "qualityProfileId": QP_ID,
        "metadataProfileId": MP_ID,
        "monitored": True,
        "searchForMissingBooks": True,
        "monitorNewItems": "all",
    }
    return _post("/api/v1/author", payload)["id"]

def _refresh_author(author_id):
    _post("/api/v1/command", {"name": "RefreshAuthor", "authorId": author_id})

def _find_book_id(title):
    for b in _get("/api/v1/book"):
        if title.lower() in b["title"].lower():
            return b["id"]
    return None

def _search_book(book_id):
    result = _post("/api/v1/command", {"name": "BookSearch", "bookIds": [book_id]})
    return result.get("id")

def _check_search_failed(command_id):
    """Check if a search command completed with 0 results"""
    try:
        commands = _get("/api/v1/command")
        for cmd in commands:
            if (cmd.get("id") == command_id and
                cmd.get("status") == "completed" and
                "0 reports downloaded" in cmd.get("message", "")):
                log.info("Search command %s failed with 0 reports", command_id)
                return True
    except Exception as e:
        log.error("Error checking search status for command %s: %s", command_id, e)
    return False

def _check_already_downloaded(book_id):
    """Check if book is already downloaded and ready to send"""
    log.info("Checking if book ID %s is already downloaded", book_id)
    if book_id:
        file_paths = _get_book_file_paths(book_id)
        if file_paths:
            existing_files = [fp for fp in file_paths if os.path.isfile(fp)]
            if existing_files:
                log.info("Found %d existing download(s) for book ID %s: %s", len(existing_files), book_id, existing_files)
                return existing_files
        log.info("No existing downloads found for book ID %s", book_id)
    return []

def _check_download_completed_in_queue(book_id):
    """Check if book download is completed in queue (even if import failed)"""
    log.info("Checking queue for completed download of book ID %s", book_id)
    try:
        queue = _get("/api/v1/queue")
        for item in queue.get("records", []):
            if (item.get("bookId") == book_id and
                item.get("status") == "completed" and
                item.get("outputPath")):
                log.info("Found completed download in queue for book ID %s: %s", book_id, item.get("outputPath"))
                return item.get("outputPath")
        log.info("No completed download found in queue for book ID %s", book_id)
    except Exception as e:
        log.error("Error checking queue for book ID %s: %s", book_id, e)
    return None

def _get_book_file_paths(book_id):
    """Get all available file paths for a book"""
    log.info("Getting all file paths for book ID %s", book_id)
    file_paths = []

    b = _get(f"/api/v1/book/{book_id}")
    if b.get("hasFile") and b.get("bookFiles"):
        for book_file in b.get("bookFiles", []):
            path = book_file.get("path")
            if path:
                log.info("Found imported file for book ID %s: %s", book_id, path)
                file_paths.append(path)

    if not file_paths:
        output_path = _check_download_completed_in_queue(book_id)
        if output_path:
            try:
                if os.path.isdir(output_path):
                    log.info("Scanning directory %s for all readable files", output_path)
                    for file in os.listdir(output_path):
                        if file.endswith(('.epub', '.mobi', '.azw3', '.pdf')):
                            full_path = os.path.join(output_path, file)
                            log.info("Found readable file: %s", full_path)
                            file_paths.append(full_path)
                elif os.path.isfile(output_path):
                    log.info("Found direct file: %s", output_path)
                    file_paths.append(output_path)
            except Exception as e:
                log.error("Error scanning download directory %s: %s", output_path, e)

    log.info("Found %d file(s) for book ID %s: %s", len(file_paths), book_id, file_paths)
    return file_paths

def _get_book_file_path(book_id):
    """Get first available file path for a book (backward compatibility)"""
    paths = _get_book_file_paths(book_id)
    return paths[0] if paths else None

async def _send_multiple_files(chat_id, file_paths, ctx, title):
    """Send multiple files to user"""
    log.info("Sending %d files for '%s'", len(file_paths), title)
    await ctx.bot.send_message(chat_id, f"📚 Found {len(file_paths)} format(s) - sending all:")

    sent_count = 0
    for file_path in file_paths:
        try:
            with open(file_path, "rb") as f:
                await ctx.bot.send_document(chat_id, f, filename=os.path.basename(file_path))
            sent_count += 1
            log.info("Successfully sent file %d/%d: %s", sent_count, len(file_paths), file_path)
        except Exception as e:
            log.error("Error sending file %s: %s", file_path, e)
            await ctx.bot.send_message(chat_id, f"❌ Error sending {os.path.basename(file_path)}: {e}")

    if sent_count > 0:
        await ctx.bot.send_message(chat_id, f"📚 Delivered {sent_count}/{len(file_paths)} files")
        return True
    return False

async def _wait_and_send_file(chat_id, book_id, ctx, command_id=None):
    log.info("Starting download wait for book ID %s in chat %s (command: %s)", book_id, chat_id, command_id)
    await ctx.bot.send_message(chat_id, "⏳ Waiting for download…")

    try:
        for attempt in range(30):
            log.info("Download check attempt %d/30 for book ID %s", attempt + 1, book_id)

            if attempt < 5:
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(10)

            if command_id and _check_search_failed(command_id):
                log.info("Search failed for book ID %s - no sources found", book_id)
                await ctx.bot.send_message(chat_id, "😕 Sorry, this book isn't available right now")
                await ctx.bot.send_message(chat_id, "The book exists but no one is sharing it at the moment. This happens with older, rare, or very new books.")
                return

            file_paths = _get_book_file_paths(book_id)
            existing_files = [fp for fp in file_paths if os.path.isfile(fp)]
            if existing_files:
                log.info("Download completed! Found %d files for book ID %s", len(existing_files), book_id)
                success = await _send_multiple_files(chat_id, existing_files, ctx, f"book {book_id}")
                if success:
                    log.info("Successfully delivered %d files for book ID %s", len(existing_files), book_id)
                    return

            log.info("No files ready yet for book ID %s, continuing to wait...", book_id)

        log.error("Download wait timed out for book ID %s after 30 attempts", book_id)
        await ctx.bot.send_message(chat_id, "⏰ Timed out")

    except asyncio.CancelledError:
        log.info("Waiting task cancelled for book ID %s in chat %s", book_id, chat_id)
        await ctx.bot.send_message(chat_id, "🚫 Search cancelled - starting new request")
        raise
    except Exception as e:
        log.error("Error in waiting task for book ID %s: %s", book_id, e)
        await ctx.bot.send_message(chat_id, f"❌ Error: {e}")
    finally:
        if chat_id in waiting_tasks:
            del waiting_tasks[chat_id]
            log.info("Cleaned up waiting task for chat %s", chat_id)

async def start(update, ctx):
    await update.message.reply_text("🐕 Dingu ready – send a book title")

async def help_cmd(update, ctx):
    await update.message.reply_text("/start /help /ping /status – or just type the title you want")

async def ping(update, ctx):
    await update.message.reply_text("pong")

async def status_cmd(update, ctx):
    chat_id = update.effective_chat.id
    bid = last_request.get(chat_id)
    if not bid:
        await ctx.bot.send_message(chat_id, "No recent request")
        return
    b = _get(f"/api/v1/book/{bid}")
    txt = "imported" if b.get("hasFile") else "queued"
    await ctx.bot.send_message(chat_id, f"Latest request status: {txt}")

async def handle_title(update, ctx):
    title = update.message.text.strip()
    chat_id = update.effective_chat.id
    log.info("Processing request for title: '%s' from chat %s", title, chat_id)
    await ctx.bot.send_message(chat_id, f'🔍 Searching for "{title}"')
    try:
        existing_book_id = _find_book_id(title)
        log.info("Found existing book ID: %s for title '%s'", existing_book_id, title)
        if existing_book_id:
            existing_files = _check_already_downloaded(existing_book_id)
            if existing_files:
                log.info("Sending existing downloads for '%s': %s", title, existing_files)
                await _send_multiple_files(chat_id, existing_files, ctx, title)
                return
            else:
                log.info("Readarr found no files for '%s', trying filesystem search...", title)
                fallback_files = _fallback_filesystem_search(title)
                if fallback_files:
                    log.info("Filesystem search found %d files for '%s': %s", len(fallback_files), title, fallback_files)
                    await ctx.bot.send_message(chat_id, "📁 Found files that Readarr missed!")
                    await _send_multiple_files(chat_id, fallback_files, ctx, title)
                    return

        log.info("No existing downloads found, starting normal flow for '%s'", title)
        lookup = _get("/api/v1/book/lookup", {"term": title})
        if not lookup:
            log.info("No books found in lookup for '%s'", title)
            await ctx.bot.send_message(chat_id, "Nothing found")
            return

        book_info = lookup[0]
        author_title = book_info.get("authorTitle", "")

        author_name = author_title.split(book_info["title"])[0].strip()

        if "," in author_name:
            parts = [p.strip() for p in author_name.split(",")]
            if len(parts) == 2:
                author_name = f"{parts[1]} {parts[0]}".title()

        log.info("Extracted author name: '%s' from '%s'", author_name, author_title)

        author_lookup = _get("/api/v1/author/lookup", {"term": author_name})
        if not author_lookup:
            log.info("Author lookup failed for '%s'", author_name)
            await ctx.bot.send_message(chat_id, f"Author '{author_name}' not found")
            return

        author_info = None
        for candidate in author_lookup:
            if candidate["authorName"].lower() == author_name.lower():
                author_info = candidate
                break

        if not author_info:
            log.info("Exact author match not found for '%s' in lookup results", author_name)
            author_info = author_lookup[0]
            log.info("Using fallback author: '%s'", author_info["authorName"])

        author_id = _add_author(author_info)
        log.info("Author ID: %s for '%s'", author_id, author_name)
        await ctx.bot.send_message(chat_id, "Author added")
        _refresh_author(author_id)
        await asyncio.sleep(10)
        book_id = _find_book_id(title)
        if not book_id:
            log.error("Book not found after refresh for '%s'", title)
            await ctx.bot.send_message(chat_id, "Book not found after refresh")
            return
        last_request[chat_id] = book_id

        if chat_id in waiting_tasks:
            waiting_tasks[chat_id].cancel()
            log.info("Cancelled previous waiting task for chat %s", chat_id)

        log.info("Starting search for book ID %s ('%s')", book_id, title)
        command_id = _search_book(book_id)
        await ctx.bot.send_message(chat_id, "Search started")

        task = asyncio.create_task(_wait_and_send_file(chat_id, book_id, ctx, command_id))
        waiting_tasks[chat_id] = task
    except Exception as e:
        log.error("Error processing %s: %s", title, e)
        await ctx.bot.send_message(chat_id, f"Error: {e}")

def _fallback_filesystem_search(title):
    """Fallback: search filesystem directly when Readarr doesn't know about files"""
    log.info("Searching filesystem directly for title: '%s'", title)
    found_files = []

    try:
        import subprocess
        result = subprocess.run(['find', '/downloads', '-type', 'd', '-iname', f'*{title}*'],
                              capture_output=True, text=True, timeout=30)
        directories = result.stdout.strip().split('\n') if result.stdout.strip() else []

        for directory in directories:
            if os.path.isdir(directory):
                log.info("Found potential directory: %s", directory)
                for file in os.listdir(directory):
                    if file.endswith(('.epub', '.mobi', '.azw3', '.pdf')):
                        full_path = os.path.join(directory, file)
                        if os.path.isfile(full_path):
                            log.info("Found file in directory: %s", full_path)
                            found_files.append(full_path)

        result = subprocess.run(['find', '/downloads', '-type', 'f', '-iname', f'*{title}*'],
                              capture_output=True, text=True, timeout=30)
        files = result.stdout.strip().split('\n') if result.stdout.strip() else []

        for file_path in files:
            if file_path.endswith(('.epub', '.mobi', '.azw3', '.pdf')) and os.path.isfile(file_path):
                if file_path not in found_files:
                    log.info("Found direct file: %s", file_path)
                    found_files.append(file_path)

    except Exception as e:
        log.error("Error in filesystem search for '%s': %s", title, e)

    log.info("Filesystem search found %d files for '%s': %s", len(found_files), title, found_files)
    return found_files

def main():
    if not TOKEN:
        log.error("Missing token")
        return
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title))
    log.info("Diinguu running")

    with open("/tmp/dingu-started.txt", "w") as f:
        f.write("Dingu bot started successfully\n")

    app.run_polling()

if __name__ == "__main__":
    main()

