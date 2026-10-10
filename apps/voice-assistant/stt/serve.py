"""Run the official Wyoming server without logging users' transcripts."""

import asyncio
import logging

from wyoming_faster_whisper.__main__ import main

if __name__ == "__main__":
    # Upstream logs each transcript at INFO. Keep warnings/errors, not utterances.
    logging.disable(logging.INFO)
    asyncio.run(main())
