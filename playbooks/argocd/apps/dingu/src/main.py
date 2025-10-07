"""Main entry point for Dingu bot with structured concurrency"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from .config import settings
from .readarr import Readarr
from .telegram_bot import Handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
log = logging.getLogger("dingu.main")

class DinguBot:
    """Main bot application with proper lifecycle management"""

    def __init__(self) -> None:
        self.readarr: Optional[Readarr] = None
        self.handlers: Optional[Handlers] = None
        self.app: Optional[object] = None
        self._shutdown_event = asyncio.Event()

    async def startup(self) -> None:
        """Initialize all components"""
        log.info("Starting Dingu bot...")

        # Validate configuration
        if not settings.telegram_token:
            raise SystemExit("DINGU_TELEGRAM_BOT_TOKEN environment variable is required")
        if not settings.readarr_key:
            raise SystemExit("READARR_KEY environment variable is required")

        # Initialize Readarr client
        self.readarr = Readarr()
        await self.readarr.open()
        log.info("Readarr client initialized")

        # Initialize handlers
        self.handlers = Handlers(self.readarr)
        log.info("Bot handlers initialized")

        # Build Telegram application
        self.app = (
            ApplicationBuilder()
            .token(settings.telegram_token)
            .build()
        )

        # Register handlers
        self.app.add_handler(CommandHandler("start", self.handlers.start))
        self.app.add_handler(CommandHandler("help", self.handlers.help_cmd))
        self.app.add_handler(CommandHandler("ping", self.handlers.ping))
        self.app.add_handler(CommandHandler("status", self.handlers.status))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_title))

        # Initialize Telegram application
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        log.info("🐕 Dingu bot is running and ready!")

        # Write startup indicator for K8s readiness probe
        startup_file = Path("/tmp/dingu-started.txt")
        startup_file.write_text("Dingu bot started successfully\n")

    async def shutdown(self) -> None:
        """Gracefully shutdown all components"""
        log.info("Shutting down Dingu bot...")

        # Stop Telegram updater and app
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            log.info("Telegram application stopped")

        # Close Readarr client
        if self.readarr:
            await self.readarr.close()
            log.info("Readarr client closed")

        log.info("Dingu bot shutdown complete")

    def handle_signal(self, signum: int) -> None:
        """Handle shutdown signals"""
        log.info("Received signal %s, initiating shutdown...", signum)
        self._shutdown_event.set()

    async def run(self) -> None:
        """Main application loop with signal handling"""
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: self.handle_signal(s))

        try:
            # Start the bot
            await self.startup()

            # Run until shutdown signal
            await self._shutdown_event.wait()

        except Exception as e:
            log.error("Fatal error in main loop: %s", e)
            raise
        finally:
            # Always attempt graceful shutdown
            await self.shutdown()

async def main() -> None:
    """Application entry point"""
    bot = DinguBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt")
    except Exception as e:
        log.error("Application failed: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    # Check if running as a module
    if sys.argv[0].endswith("__main__.py"):
        log.info("Starting Dingu as module: python -m dingu")
    else:
        log.info("Starting Dingu directly: python main.py")

    # Run with structured concurrency
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Application interrupted by user")
    except Exception as e:
        log.error("Failed to start application: %s", e)
        sys.exit(1)
