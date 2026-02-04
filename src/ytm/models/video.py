"""Video and PlaylistItem data models."""

from datetime import datetime

from pydantic import BaseModel


class Video(BaseModel):
    """Represents a YouTube video."""

    video_id: str
    title: str | None = None
    description: str | None = None
    channel_id: str | None = None
    channel_title: str | None = None
    duration_seconds: int | None = None
    thumbnail_url: str | None = None
    published_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_updated_at: datetime | None = None
    is_available: bool = True

    @classmethod
    def from_api_response(cls, item: dict) -> "Video":
        """Create Video from YouTube API playlistItems response."""
        snippet = item.get("snippet", {})
        resource_id = snippet.get("resourceId", {})
        thumbnails = snippet.get("thumbnails", {})

        # Get best available thumbnail
        thumbnail_url = None
        for quality in ["maxres", "high", "medium", "default"]:
            if quality in thumbnails:
                thumbnail_url = thumbnails[quality].get("url")
                break

        published_at = None
        if snippet.get("videoPublishedAt"):
            published_at = datetime.fromisoformat(
                snippet["videoPublishedAt"].replace("Z", "+00:00")
            )

        now = datetime.now()
        return cls(
            video_id=resource_id.get("videoId", ""),
            title=snippet.get("title"),
            description=snippet.get("description"),
            channel_id=snippet.get("videoOwnerChannelId"),
            channel_title=snippet.get("videoOwnerChannelTitle"),
            thumbnail_url=thumbnail_url,
            published_at=published_at,
            first_seen_at=now,
            last_updated_at=now,
            is_available=snippet.get("title") != "Private video"
            and snippet.get("title") != "Deleted video",
        )

    @classmethod
    def from_ytdlp_entry(cls, entry: dict) -> "Video":
        """Create Video from yt-dlp flat playlist entry."""
        now = datetime.now()

        # Duration might be in seconds or None
        duration = entry.get("duration")
        if duration is not None:
            duration = int(duration)

        return cls(
            video_id=entry.get("id", ""),
            title=entry.get("title"),
            channel_id=entry.get("channel_id"),
            channel_title=entry.get("channel") or entry.get("uploader"),
            duration_seconds=duration,
            thumbnail_url=entry.get("thumbnail"),
            first_seen_at=now,
            last_updated_at=now,
            is_available=entry.get("title") not in ["[Private video]", "[Deleted video]"],
        )


class PlaylistItem(BaseModel):
    """Represents a video's membership in a playlist."""

    item_id: str
    playlist_id: str
    video_id: str
    position: int
    added_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    removed_from_youtube_at: datetime | None = None

    @classmethod
    def from_api_response(cls, item: dict, playlist_id: str) -> "PlaylistItem":
        """Create PlaylistItem from YouTube API response."""
        snippet = item.get("snippet", {})
        resource_id = snippet.get("resourceId", {})

        added_at = None
        if snippet.get("publishedAt"):
            added_at = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )

        now = datetime.now()
        return cls(
            item_id=item["id"],
            playlist_id=playlist_id,
            video_id=resource_id.get("videoId", ""),
            position=snippet.get("position", 0),
            added_at=added_at,
            first_seen_at=now,
            last_seen_at=now,
        )

    @classmethod
    def from_ytdlp_entry(
        cls, entry: dict, playlist_id: str, position: int
    ) -> "PlaylistItem":
        """Create PlaylistItem from yt-dlp flat playlist entry."""
        now = datetime.now()
        video_id = entry.get("id", "")

        return cls(
            item_id=f"{playlist_id}_{video_id}",
            playlist_id=playlist_id,
            video_id=video_id,
            position=position,
            first_seen_at=now,
            last_seen_at=now,
        )
