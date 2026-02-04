"""Playlist data model."""

from datetime import datetime

from pydantic import BaseModel


class Playlist(BaseModel):
    """Represents a YouTube playlist."""

    playlist_id: str
    title: str
    description: str = ""
    channel_id: str | None = None
    privacy_status: str | None = None
    item_count: int = 0
    published_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    deleted_from_youtube_at: datetime | None = None

    @classmethod
    def from_api_response(cls, item: dict) -> "Playlist":
        """Create Playlist from YouTube API response."""
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})
        status = item.get("status", {})

        published_at = None
        if snippet.get("publishedAt"):
            published_at = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )

        now = datetime.now()
        return cls(
            playlist_id=item["id"],
            title=snippet.get("title", ""),
            description=snippet.get("description", ""),
            channel_id=snippet.get("channelId"),
            privacy_status=status.get("privacyStatus"),
            item_count=content_details.get("itemCount", 0),
            published_at=published_at,
            first_seen_at=now,
            last_seen_at=now,
        )
