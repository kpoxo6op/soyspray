"""Configuration management for Dingu bot"""

from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Settings:
    """Immutable configuration settings from environment variables"""
    readarr_url: str = os.getenv("READARR_URL", "http://192.168.1.131:8787")
    readarr_key: str = os.getenv("READARR_KEY", "a85bb8f2ab19425f9c8c0bbc6f0aa29c")
    root_id: int = 1
    root_path: Path = Path("/downloads/BooksLibrary")
    quality_profile_id: int = 1
    metadata_profile_id: int = 1
    telegram_token: str = os.getenv("DINGU_TELEGRAM_BOT_TOKEN", "")

    def __post_init__(self):
        """Validate critical settings on initialization"""
        if not self.telegram_token:
            raise ValueError("DINGU_TELEGRAM_BOT_TOKEN environment variable is required")
        if not self.readarr_key:
            raise ValueError("READARR_KEY environment variable is required")

# Global settings instance
settings = Settings()
