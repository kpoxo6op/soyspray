# Booklore

Self-hosted book library manager integrated with qBittorrent.

## Architecture

Booklore uses a two-container setup:
1. `booklore` - Main application (port 6060)
2. `booklore-mariadb` - MariaDB database

## qBittorrent Integration

The integration is filesystem-based using direct library indexing.

### Direct Library Indexing (Recommended)

qBittorrent downloads books to `/downloads/books`, Booklore indexes this folder as a Library.

| App | Mount Path | Underlying PVC |
|-----|------------|----------------|
| qBittorrent | `/downloads/books` | qbittorrent-downloads |
| Booklore | `/books` | qbittorrent-downloads (subPath: books) |

Setup in Booklore:
1. Create a Library pointing to `/books`
2. Enable monitoring for automatic detection
3. Use Re-scan Library for manual refresh

## Environment Variables

| Variable | Description |
|----------|-------------|
| APP_USER_ID | User ID (default: 1000) |
| APP_GROUP_ID | Group ID (default: 1000) |
| DATABASE_HOST | MariaDB hostname |
| DATABASE_PORT | MariaDB port (3306) |
| DATABASE_NAME | Database name |
| DATABASE_USERNAME | Database user |
| DATABASE_PASSWORD | Database password |

## Access

- URL: https://booklore.soyspray.vip
- Port: 6060

## First Run

1. Access the web interface
2. Create admin user
3. Add Library pointing to `/books`
4. Enable monitoring

## Volumes

| Mount | Purpose |
|-------|---------|
| /app/config | Application configuration |
| /app/data | Cache and processed files |
| /books | Book library (shared with qBittorrent) |
