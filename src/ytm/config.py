"""Configuration for YouTube Playlist Manager."""

import os
from pathlib import Path


def get_config_dir() -> Path:
    """Get XDG-compliant config directory."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        config_dir = Path(xdg_config) / "ytm"
    else:
        config_dir = Path.home() / ".config" / "ytm"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get XDG-compliant data directory."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        data_dir = Path(xdg_data) / "ytm"
    else:
        data_dir = Path.home() / ".local" / "share" / "ytm"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# OAuth2 configuration
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = get_config_dir() / "token.json"

# DuckLake configuration
DUCKLAKE_METADATA = get_data_dir() / "metadata.ducklake"
DUCKLAKE_DATA_PATH = get_data_dir() / "data"

# Watch Later playlist ID
WATCH_LATER_PLAYLIST_ID = "WL"

# API quota costs
QUOTA_COSTS = {
    "playlistItems.list": 1,
    "playlistItems.insert": 50,
    "playlistItems.delete": 50,
    "playlists.list": 1,
    "playlists.insert": 50,
    "playlists.delete": 50,
}

# Browser settings for Playwright
CHROME_PATH_MACOS = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_USER_DATA_MACOS = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
