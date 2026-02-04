# ytm - YouTube Playlist Manager

A CLI tool for backing up YouTube playlists with time-travel capabilities. Query your playlists as they existed at any point in time.

## Features

- **Backup all playlists** including Watch Later (which YouTube's API blocks)
- **Time-travel queries** - see what was in a playlist last week, last month, etc.
- **Prune Watch Later** - automatically remove old items via browser automation
- **Restore playlists** - recover deleted videos to a new playlist

## Installation

```bash
# Clone and install
git clone <repo>
cd youtube-playlist-manager
uv sync

# Install Playwright browsers (needed for Watch Later pruning)
uv run playwright install chromium
```

## Setup

1. Create a Google Cloud project and enable the YouTube Data API v3
2. Create OAuth 2.0 credentials (Desktop app)
3. Download as `client_secrets.json` in the project root
4. Add your email as a test user in the OAuth consent screen
5. Authenticate:

```bash
uv run ytm auth login
```

## Usage

### Backup

```bash
# Backup all playlists
uv run ytm backup

# Include Watch Later (uses yt-dlp with browser cookies)
uv run ytm backup --watch-later
```

### List & Query

```bash
# List backed-up playlists
uv run ytm list playlists

# List items in a playlist
uv run ytm list items PLAYLIST_ID

# Time-travel: see playlist at a specific snapshot
uv run ytm list items WL --at-version 5

# Time-travel: see playlist at a specific time
uv run ytm list items WL --at-time "2024-01-15 10:00:00"
```

### History

```bash
# View all snapshots
uv run ytm history snapshots

# Compare two versions
uv run ytm history diff 1 5
```

### Prune Watch Later

Remove items from Watch Later using browser automation (YouTube API doesn't allow this):

```bash
# Delete all items
uv run ytm prune WL --all

# Delete the 100 oldest items (from bottom of list)
uv run ytm prune WL --count 100

# Delete items older than 90 days
uv run ytm prune WL --older-than 90d

# Preview what would be deleted
uv run ytm prune WL --all --dry-run

# Control batch size and delay between deletions
uv run ytm prune WL --all --batch-size 50 --delay 2
```

**Notes:**
- Chrome must be completely closed before pruning
- Items are deleted from YouTube only; local backup is preserved for restore
- `--older-than` uses `first_seen_at` from local backup (when we first saw the item), not when it was added to Watch Later—YouTube doesn't expose that. For immediate cleanup, use `--all` or `--count`.

### Restore

```bash
# Restore to a new playlist
uv run ytm restore WL --create-new "Watch Later Backup"

# Restore from a specific snapshot
uv run ytm restore WL --from-version 3 --create-new "Old Watch Later"
```

## Data Storage

Data is stored in XDG-compliant directories:
- Config: `~/.config/ytm/` (OAuth tokens)
- Data: `~/.local/share/ytm/` (DuckLake database)

## Maintenance

The database uses DuckLake for time-travel snapshots. To compact the database and clean up old snapshots:

```bash
uv run python -c "
from ytm.core.database import get_connection
conn = get_connection()
conn.execute(\"CALL ducklake_set_option('ytm', 'expire_older_than', INTERVAL '7 days')\")
conn.execute('CHECKPOINT ytm')
"
```

## Tech Stack

- **Typer** + **Rich** for CLI
- **DuckDB** + **DuckLake** for time-travel storage
- **yt-dlp** for reading Watch Later (bypasses API restrictions)
- **Playwright** for Watch Later deletion (browser automation)
- **google-api-python-client** for YouTube Data API v3
