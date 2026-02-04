# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run CLI
uv run ytm --help
uv run ytm backup --watch-later
uv run ytm list playlists
uv run ytm list items WL --at-version 1

# Run tests
uv run pytest
uv run pytest tests/test_specific.py -k "test_name"

# Install Playwright browsers (required for Watch Later pruning)
uv run playwright install chromium
```

## Architecture

This is a CLI tool (`ytm`) for backing up YouTube playlists with time-travel capabilities via DuckLake.

### Data Flow

1. **YouTube API** (`core/youtube_api.py`) - Fetches regular playlists via OAuth2
2. **yt-dlp** (`core/youtube_ytdlp.py`) - Reads Watch Later playlist using browser cookies (YouTube API blocked WL access since 2016)
3. **Playwright** (`core/browser.py`) - Deletes Watch Later items via browser automation (only way to modify WL)
4. **DuckLake** (`core/database.py`) - Stores all data with automatic snapshots for time-travel queries

### Key Design Decisions

- **Watch Later is special**: Can be read via yt-dlp and pruned via Playwright, but never restored TO (API limitation)
- **DuckLake limitations**: No PRIMARY KEY or DEFAULT constraints - uniqueness handled in application code via upsert logic
- **Time-travel queries**: Use `AT (VERSION => N)` or `AT (TIMESTAMP => 'YYYY-MM-DD')` syntax
- **XDG-compliant storage**: Config in `~/.config/ytm/`, data in `~/.local/share/ytm/`

### CLI Structure

Commands are organized in `commands/` with each file exporting a function registered in `cli.py`:
- Top-level: `backup`, `delete`, `empty`, `prune`, `restore`
- Subcommands: `auth login/logout`, `list playlists/items`, `history snapshots/diff`

### Models

Pydantic models in `models/` have factory methods for both API responses and yt-dlp entries:
- `Playlist.from_api_response()` / `Video.from_ytdlp_entry()`
- `PlaylistItem` uses composite IDs: `{playlist_id}_{video_id}` for yt-dlp items

### Database Schema

Three tables in DuckLake (`ytm` schema): `playlists`, `videos`, `playlist_items`. Videos are deduplicated across playlists. Removed items are soft-deleted via `removed_from_youtube_at` timestamp.

### DuckLake Maintenance

Backups are wrapped in a transaction to create one snapshot per backup. To compact and clean up old snapshots:

```sql
CALL ducklake_set_option('ytm', 'expire_older_than', INTERVAL '7 days');
CHECKPOINT ytm;
```
