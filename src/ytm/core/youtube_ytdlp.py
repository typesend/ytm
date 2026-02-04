"""yt-dlp wrapper for reading Watch Later playlist."""

import yt_dlp
from rich.console import Console

from ytm.config import WATCH_LATER_PLAYLIST_ID
from ytm.models import Playlist, PlaylistItem, Video

console = Console()


class QuietLogger:
    """Quiet logger for yt-dlp."""

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        console.print(f"[red]yt-dlp error: {msg}[/red]")


def get_watch_later(browser: str = "chrome") -> tuple[Playlist, list[Video], list[PlaylistItem]]:
    """Fetch Watch Later playlist using yt-dlp with browser cookies.

    Args:
        browser: Browser to extract cookies from ('chrome', 'firefox', 'safari', etc.)

    Returns:
        Tuple of (playlist, videos, playlist_items)
    """
    ydl_opts = {
        "cookiesfrombrowser": (browser,),
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "logger": QuietLogger(),
    }

    watch_later_url = f"https://www.youtube.com/playlist?list={WATCH_LATER_PLAYLIST_ID}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(watch_later_url, download=False)

    if not info:
        raise RuntimeError("Failed to fetch Watch Later playlist")

    # Create playlist object
    playlist = Playlist(
        playlist_id=WATCH_LATER_PLAYLIST_ID,
        title="Watch Later",
        description="Your Watch Later playlist",
        item_count=len(info.get("entries", [])),
    )

    videos = []
    items = []

    for position, entry in enumerate(info.get("entries", []) or []):
        if entry is None:
            continue

        video = Video.from_ytdlp_entry(entry)
        playlist_item = PlaylistItem.from_ytdlp_entry(
            entry, WATCH_LATER_PLAYLIST_ID, position
        )

        videos.append(video)
        items.append(playlist_item)

    return playlist, videos, items


def get_playlist_ytdlp(
    playlist_id: str, browser: str = "chrome"
) -> tuple[Playlist, list[Video], list[PlaylistItem]]:
    """Fetch any playlist using yt-dlp (useful for private playlists).

    Args:
        playlist_id: YouTube playlist ID
        browser: Browser to extract cookies from

    Returns:
        Tuple of (playlist, videos, playlist_items)
    """
    ydl_opts = {
        "cookiesfrombrowser": (browser,),
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "logger": QuietLogger(),
    }

    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    if not info:
        raise RuntimeError(f"Failed to fetch playlist {playlist_id}")

    playlist = Playlist(
        playlist_id=playlist_id,
        title=info.get("title", "Unknown Playlist"),
        description=info.get("description", ""),
        item_count=len(info.get("entries", [])),
    )

    videos = []
    items = []

    for position, entry in enumerate(info.get("entries", []) or []):
        if entry is None:
            continue

        video = Video.from_ytdlp_entry(entry)
        playlist_item = PlaylistItem.from_ytdlp_entry(entry, playlist_id, position)

        videos.append(video)
        items.append(playlist_item)

    return playlist, videos, items
