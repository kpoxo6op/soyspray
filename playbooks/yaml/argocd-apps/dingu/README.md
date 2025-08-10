# Dingu Bot - Async Telegram Bot for Readarr

## Overview

Dingu is a fully async Telegram bot that integrates with Readarr to search and download books on demand. The bot has been refactored into a clean, modular, and testable architecture.

## New Architecture (v2.0)

### Directory Structure

```
playbooks/yaml/argocd-apps/dingu/
├── src/                      # Python source code
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Module entry point
│   ├── main.py             # Application bootstrap with lifecycle management
│   ├── config.py           # Immutable configuration from environment
│   ├── readarr.py          # Async Readarr API client
│   ├── storage.py          # Filesystem operations with pathlib
│   ├── telegram_bot.py     # Clean, testable Telegram handlers
│   └── requirements.txt    # Dependencies (aiohttp, python-telegram-bot)
├── deployment.yaml          # Kubernetes Deployment
├── kustomization.yaml       # Kustomize configuration
├── dingu-application.yaml   # ArgoCD Application
├── bot_legacy.py           # Original monolithic bot (backup)
└── README.md              # This file
```

### Key Improvements

- **Fully Async**: Uses `aiohttp` for non-blocking I/O instead of `requests`
- **Modular Design**: Clean separation of concerns across focused modules
- **Testable**: Each handler is pure and dependency-injected
- **Graceful Shutdown**: Proper asyncio lifecycle with signal handling
- **Type Hints**: Full type annotations for better development experience
- **Error Handling**: Comprehensive error handling and logging
- **Resource Management**: Explicit session management and cleanup

### Running the Bot

**As a module (recommended):**
```bash
python -m dingu
```

**Direct execution:**
```bash
python main.py
```

### Environment Variables

Required:
- `DINGU_TELEGRAM_BOT_TOKEN` - Telegram bot token
- `READARR_KEY` - Readarr API key

Optional:
- `READARR_URL` - Readarr base URL (default: http://192.168.50.212:8787)

### Kubernetes Deployment

The bot runs as a Kubernetes Deployment with:

- **Command**: `python -m dingu`
- **Dependencies**: Installed from `requirements.txt`
- **Volumes**: Access to downloads PVC for file delivery
- **Secrets**: Bot tokens from Kubernetes secrets
- **Health Checks**: Readiness/liveness probes via `/tmp/dingu-started.txt`

### Features

- **Multi-format Support**: Delivers all available formats (.epub, .mobi, .azw3, .pdf)
- **Smart Search**: Checks Readarr first, falls back to filesystem search
- **Download Management**: Tracks download progress and handles failures
- **Task Cancellation**: Properly cancels overlapping requests
- **File Size Validation**: Respects Telegram's 50MB file limit
- **User-friendly Messages**: Clear status updates and error handling

### Legacy Version

The original monolithic bot is preserved as `bot_legacy.py` for reference.

## Commands

- `/start` - Initialize the bot
- `/help` - Show available commands
- `/ping` - Test bot responsiveness
- `/status` - Check latest request status
- Send any text - Search for a book by title

## Development

### Testing Locally

1. Set environment variables:
   ```bash
   export DINGU_TELEGRAM_BOT_TOKEN="your_token"
   export READARR_KEY="your_key"
   ```

 2. Install dependencies:
    ```bash
    pip install -r src/requirements.txt
    ```

 3. Run the bot:
    ```bash
    cd src && python -m dingu
    ```

### Deployment

The bot is deployed via ArgoCD as part of the GitOps workflow. Changes to this directory are automatically deployed to the cluster.
