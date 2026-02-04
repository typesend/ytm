"""DuckLake database operations for time-travel storage."""

from datetime import datetime
from pathlib import Path

import duckdb
from rich.console import Console

from ytm.config import DUCKLAKE_DATA_PATH, DUCKLAKE_METADATA
from ytm.models import Playlist, PlaylistItem, Video

console = Console()

# Global connection
_conn: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get or create DuckDB connection with DuckLake attached."""
    global _conn

    if _conn is not None:
        return _conn

    _conn = duckdb.connect()

    # Install and load DuckLake
    _conn.execute("INSTALL ducklake; LOAD ducklake;")

    # Ensure data directory exists
    DUCKLAKE_DATA_PATH.mkdir(parents=True, exist_ok=True)

    # Attach DuckLake database
    _conn.execute(f"""
        ATTACH 'ducklake:{DUCKLAKE_METADATA}' AS ytm (DATA_PATH '{DUCKLAKE_DATA_PATH}/');
    """)

    # Initialize schema if needed
    _init_schema(_conn)

    return _conn


def _init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize database schema.

    Note: DuckLake doesn't support PRIMARY KEY constraints, so we handle
    uniqueness in application code via upsert logic.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ytm.playlists (
            playlist_id VARCHAR NOT NULL,
            title VARCHAR NOT NULL,
            description TEXT,
            channel_id VARCHAR,
            privacy_status VARCHAR,
            item_count INTEGER,
            published_at TIMESTAMP,
            first_seen_at TIMESTAMP NOT NULL,
            last_seen_at TIMESTAMP NOT NULL,
            deleted_from_youtube_at TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ytm.videos (
            video_id VARCHAR NOT NULL,
            title VARCHAR,
            description TEXT,
            channel_id VARCHAR,
            channel_title VARCHAR,
            duration_seconds INTEGER,
            thumbnail_url VARCHAR,
            published_at TIMESTAMP,
            first_seen_at TIMESTAMP NOT NULL,
            last_updated_at TIMESTAMP NOT NULL,
            is_available BOOLEAN
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ytm.playlist_items (
            item_id VARCHAR NOT NULL,
            playlist_id VARCHAR NOT NULL,
            video_id VARCHAR NOT NULL,
            position INTEGER NOT NULL,
            added_at TIMESTAMP,
            first_seen_at TIMESTAMP NOT NULL,
            last_seen_at TIMESTAMP NOT NULL,
            removed_from_youtube_at TIMESTAMP
        );
    """)


def upsert_playlist(playlist: Playlist) -> None:
    """Insert or update a playlist."""
    conn = get_connection()
    now = datetime.now()

    # Check if exists
    result = conn.execute(
        "SELECT first_seen_at FROM ytm.playlists WHERE playlist_id = ?",
        [playlist.playlist_id],
    ).fetchone()

    if result:
        # Update existing
        conn.execute(
            """
            UPDATE ytm.playlists SET
                title = ?,
                description = ?,
                channel_id = ?,
                privacy_status = ?,
                item_count = ?,
                published_at = ?,
                last_seen_at = ?,
                deleted_from_youtube_at = NULL
            WHERE playlist_id = ?
            """,
            [
                playlist.title,
                playlist.description,
                playlist.channel_id,
                playlist.privacy_status,
                playlist.item_count,
                playlist.published_at,
                now,
                playlist.playlist_id,
            ],
        )
    else:
        # Insert new
        conn.execute(
            """
            INSERT INTO ytm.playlists (
                playlist_id, title, description, channel_id, privacy_status,
                item_count, published_at, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                playlist.playlist_id,
                playlist.title,
                playlist.description,
                playlist.channel_id,
                playlist.privacy_status,
                playlist.item_count,
                playlist.published_at,
                now,
                now,
            ],
        )


def upsert_video(video: Video) -> None:
    """Insert or update a video."""
    conn = get_connection()
    now = datetime.now()

    result = conn.execute(
        "SELECT first_seen_at FROM ytm.videos WHERE video_id = ?",
        [video.video_id],
    ).fetchone()

    if result:
        conn.execute(
            """
            UPDATE ytm.videos SET
                title = COALESCE(?, title),
                description = COALESCE(?, description),
                channel_id = COALESCE(?, channel_id),
                channel_title = COALESCE(?, channel_title),
                duration_seconds = COALESCE(?, duration_seconds),
                thumbnail_url = COALESCE(?, thumbnail_url),
                published_at = COALESCE(?, published_at),
                last_updated_at = ?,
                is_available = ?
            WHERE video_id = ?
            """,
            [
                video.title,
                video.description,
                video.channel_id,
                video.channel_title,
                video.duration_seconds,
                video.thumbnail_url,
                video.published_at,
                now,
                video.is_available,
                video.video_id,
            ],
        )
    else:
        conn.execute(
            """
            INSERT INTO ytm.videos (
                video_id, title, description, channel_id, channel_title,
                duration_seconds, thumbnail_url, published_at,
                first_seen_at, last_updated_at, is_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                video.video_id,
                video.title,
                video.description,
                video.channel_id,
                video.channel_title,
                video.duration_seconds,
                video.thumbnail_url,
                video.published_at,
                now,
                now,
                video.is_available,
            ],
        )


def upsert_playlist_item(item: PlaylistItem) -> None:
    """Insert or update a playlist item."""
    conn = get_connection()
    now = datetime.now()

    result = conn.execute(
        "SELECT first_seen_at FROM ytm.playlist_items WHERE item_id = ?",
        [item.item_id],
    ).fetchone()

    if result:
        conn.execute(
            """
            UPDATE ytm.playlist_items SET
                position = ?,
                last_seen_at = ?,
                removed_from_youtube_at = NULL
            WHERE item_id = ?
            """,
            [item.position, now, item.item_id],
        )
    else:
        conn.execute(
            """
            INSERT INTO ytm.playlist_items (
                item_id, playlist_id, video_id, position,
                added_at, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                item.item_id,
                item.playlist_id,
                item.video_id,
                item.position,
                item.added_at,
                now,
                now,
            ],
        )


def mark_removed_items(playlist_id: str, current_item_ids: set[str]) -> None:
    """Mark items no longer in playlist as removed."""
    conn = get_connection()
    now = datetime.now()

    # Get all items for this playlist that aren't marked as removed
    result = conn.execute(
        """
        SELECT item_id FROM ytm.playlist_items
        WHERE playlist_id = ? AND removed_from_youtube_at IS NULL
        """,
        [playlist_id],
    ).fetchall()

    for (item_id,) in result:
        if item_id not in current_item_ids:
            conn.execute(
                """
                UPDATE ytm.playlist_items
                SET removed_from_youtube_at = ?
                WHERE item_id = ?
                """,
                [now, item_id],
            )


def _rows_to_dicts(cursor) -> list[dict]:
    """Convert cursor results to list of dicts."""
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def get_playlists(at_version: int | None = None, at_time: str | None = None) -> list[dict]:
    """Get all playlists, optionally at a specific version or time."""
    conn = get_connection()

    time_travel = ""
    if at_version is not None:
        time_travel = f" AT (VERSION => {at_version})"
    elif at_time:
        time_travel = f" AT (TIMESTAMP => '{at_time}')"

    cursor = conn.execute(f"""
        SELECT * FROM ytm.playlists{time_travel}
        WHERE deleted_from_youtube_at IS NULL
        ORDER BY title
    """)

    return _rows_to_dicts(cursor)


def get_playlist_items(
    playlist_id: str,
    at_version: int | None = None,
    at_time: str | None = None,
    include_removed: bool = False,
) -> list[dict]:
    """Get items in a playlist with video details."""
    conn = get_connection()

    time_travel = ""
    if at_version is not None:
        time_travel = f" AT (VERSION => {at_version})"
    elif at_time:
        time_travel = f" AT (TIMESTAMP => '{at_time}')"

    removed_filter = "" if include_removed else "AND pi.removed_from_youtube_at IS NULL"

    cursor = conn.execute(f"""
        SELECT
            pi.item_id,
            pi.playlist_id,
            pi.video_id,
            pi.position,
            pi.added_at,
            pi.first_seen_at,
            pi.last_seen_at,
            pi.removed_from_youtube_at,
            v.title,
            v.channel_title,
            v.duration_seconds,
            v.is_available
        FROM ytm.playlist_items{time_travel} pi
        LEFT JOIN ytm.videos{time_travel} v ON pi.video_id = v.video_id
        WHERE pi.playlist_id = ? {removed_filter}
        ORDER BY pi.position
    """, [playlist_id])

    return _rows_to_dicts(cursor)


def get_snapshots() -> list[dict]:
    """Get list of DuckLake snapshots."""
    conn = get_connection()

    cursor = conn.execute("""
        SELECT * FROM ducklake_snapshots('ytm')
        ORDER BY snapshot_time DESC
    """)

    return _rows_to_dicts(cursor)


def get_snapshot_changes(version1: int, version2: int) -> dict:
    """Compare two snapshots and return differences."""
    conn = get_connection()

    changes = {
        "playlists_added": [],
        "playlists_removed": [],
        "items_added": [],
        "items_removed": [],
    }

    # Compare playlists
    playlists_v1 = set(
        r[0]
        for r in conn.execute(
            f"SELECT playlist_id FROM ytm.playlists AT (VERSION => {version1})"
        ).fetchall()
    )
    playlists_v2 = set(
        r[0]
        for r in conn.execute(
            f"SELECT playlist_id FROM ytm.playlists AT (VERSION => {version2})"
        ).fetchall()
    )

    changes["playlists_added"] = list(playlists_v2 - playlists_v1)
    changes["playlists_removed"] = list(playlists_v1 - playlists_v2)

    # Compare playlist items
    items_v1 = set(
        r[0]
        for r in conn.execute(
            f"SELECT item_id FROM ytm.playlist_items AT (VERSION => {version1})"
        ).fetchall()
    )
    items_v2 = set(
        r[0]
        for r in conn.execute(
            f"SELECT item_id FROM ytm.playlist_items AT (VERSION => {version2})"
        ).fetchall()
    )

    changes["items_added"] = list(items_v2 - items_v1)
    changes["items_removed"] = list(items_v1 - items_v2)

    return changes


def close_connection() -> None:
    """Close the database connection."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def begin_transaction() -> None:
    """Begin a transaction for batched writes."""
    conn = get_connection()
    conn.execute("BEGIN TRANSACTION")


def commit_transaction() -> None:
    """Commit the current transaction."""
    conn = get_connection()
    conn.execute("COMMIT")


def rollback_transaction() -> None:
    """Rollback the current transaction."""
    conn = get_connection()
    conn.execute("ROLLBACK")
