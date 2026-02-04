"""List commands for playlists and items."""

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from ytm.core import database

console = Console()


def list_playlists(
    at_version: Annotated[
        Optional[int],
        typer.Option("--at-version", "-v", help="View at specific snapshot version"),
    ] = None,
    at_time: Annotated[
        Optional[str],
        typer.Option("--at-time", "-t", help="View at specific timestamp (YYYY-MM-DD HH:MM:SS)"),
    ] = None,
) -> None:
    """List all backed-up playlists."""
    playlists = database.get_playlists(at_version=at_version, at_time=at_time)

    if not playlists:
        console.print("[yellow]No playlists found in database.[/yellow]")
        console.print("Run 'ytm backup' to backup your playlists.")
        return

    table = Table(title="Backed-up Playlists")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="green")
    table.add_column("Items", justify="right")
    table.add_column("Privacy")
    table.add_column("Last Seen")

    for pl in playlists:
        last_seen = pl.get("last_seen_at")
        if last_seen:
            last_seen = str(last_seen)[:19]
        else:
            last_seen = "-"

        table.add_row(
            pl["playlist_id"],
            pl["title"][:40],
            str(pl.get("item_count", 0)),
            pl.get("privacy_status", "-"),
            last_seen,
        )

    console.print(table)

    if at_version:
        console.print(f"[dim]Showing data at version {at_version}[/dim]")
    elif at_time:
        console.print(f"[dim]Showing data at {at_time}[/dim]")


def list_items(
    playlist_id: Annotated[str, typer.Argument(help="Playlist ID to list items from")],
    at_version: Annotated[
        Optional[int],
        typer.Option("--at-version", "-v", help="View at specific snapshot version"),
    ] = None,
    at_time: Annotated[
        Optional[str],
        typer.Option("--at-time", "-t", help="View at specific timestamp"),
    ] = None,
    include_removed: Annotated[
        bool,
        typer.Option("--include-removed", "-r", help="Include removed items"),
    ] = False,
) -> None:
    """List items in a playlist."""
    items = database.get_playlist_items(
        playlist_id,
        at_version=at_version,
        at_time=at_time,
        include_removed=include_removed,
    )

    if not items:
        console.print(f"[yellow]No items found for playlist {playlist_id}.[/yellow]")
        return

    table = Table(title=f"Items in {playlist_id}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Video ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="green")
    table.add_column("Channel")
    table.add_column("Duration", justify="right")
    table.add_column("Status")

    for item in items:
        # Format duration
        duration = item.get("duration_seconds")
        if duration:
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes}:{seconds:02d}"
        else:
            duration_str = "-"

        # Determine status
        if item.get("removed_from_youtube_at"):
            status = "[red]Removed[/red]"
        elif not item.get("is_available", True):
            status = "[yellow]Unavailable[/yellow]"
        else:
            status = "[green]OK[/green]"

        table.add_row(
            str(item.get("position", 0)),
            item["video_id"],
            (item.get("title") or "Unknown")[:35],
            (item.get("channel_title") or "-")[:20],
            duration_str,
            status,
        )

    console.print(table)
    console.print(f"[dim]Total: {len(items)} items[/dim]")

    if at_version:
        console.print(f"[dim]Showing data at version {at_version}[/dim]")
    elif at_time:
        console.print(f"[dim]Showing data at {at_time}[/dim]")
