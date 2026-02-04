"""YouTube Data API v3 wrapper."""

from googleapiclient.discovery import build
from rich.console import Console

from ytm.auth.oauth import require_auth
from ytm.models import Playlist, PlaylistItem, Video

console = Console()


def get_youtube_service():
    """Get authenticated YouTube API service."""
    creds = require_auth()
    return build("youtube", "v3", credentials=creds)


def get_my_playlists() -> list[Playlist]:
    """Fetch all playlists owned by the authenticated user."""
    youtube = get_youtube_service()
    playlists = []

    request = youtube.playlists().list(
        part="snippet,contentDetails,status",
        mine=True,
        maxResults=50,
    )

    while request is not None:
        response = request.execute()

        for item in response.get("items", []):
            playlists.append(Playlist.from_api_response(item))

        request = youtube.playlists().list_next(request, response)

    return playlists


def get_playlist_items_api(playlist_id: str) -> tuple[list[Video], list[PlaylistItem]]:
    """Fetch all items in a playlist via YouTube API.

    Returns tuple of (videos, playlist_items).
    Note: Does NOT work for Watch Later (WL) - use yt-dlp instead.
    """
    youtube = get_youtube_service()
    videos = []
    items = []

    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults=50,
    )

    while request is not None:
        response = request.execute()

        for item in response.get("items", []):
            video = Video.from_api_response(item)
            playlist_item = PlaylistItem.from_api_response(item, playlist_id)

            videos.append(video)
            items.append(playlist_item)

        request = youtube.playlistItems().list_next(request, response)

    return videos, items


def delete_playlist(playlist_id: str) -> bool:
    """Delete a playlist from YouTube."""
    youtube = get_youtube_service()
    try:
        youtube.playlists().delete(id=playlist_id).execute()
        return True
    except Exception as e:
        console.print(f"[red]Error deleting playlist: {e}[/red]")
        return False


def delete_playlist_item(item_id: str) -> bool:
    """Delete a single item from a playlist."""
    youtube = get_youtube_service()
    try:
        youtube.playlistItems().delete(id=item_id).execute()
        return True
    except Exception as e:
        console.print(f"[red]Error deleting item: {e}[/red]")
        return False


def add_to_playlist(playlist_id: str, video_id: str) -> str | None:
    """Add a video to a playlist. Returns the new item ID or None on failure."""
    youtube = get_youtube_service()
    try:
        response = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                }
            },
        ).execute()
        return response.get("id")
    except Exception as e:
        console.print(f"[red]Error adding video to playlist: {e}[/red]")
        return None


def create_playlist(title: str, description: str = "", privacy: str = "private") -> str | None:
    """Create a new playlist. Returns playlist ID or None on failure."""
    youtube = get_youtube_service()
    try:
        response = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                },
                "status": {
                    "privacyStatus": privacy,
                },
            },
        ).execute()
        return response.get("id")
    except Exception as e:
        console.print(f"[red]Error creating playlist: {e}[/red]")
        return None
