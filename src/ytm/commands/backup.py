"""Backup command for YouTube playlists."""

from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from ytm.config import WATCH_LATER_PLAYLIST_ID
from ytm.core import database
from ytm.core.youtube_api import get_my_playlists, get_playlist_items_api
from ytm.core.youtube_ytdlp import get_watch_later

console = Console()


def backup(
    watch_later: Annotated[
        bool,
        typer.Option("--watch-later", "-w", help="Include Watch Later playlist (uses yt-dlp)"),
    ] = False,
    browser: Annotated[
        str,
        typer.Option("--browser", "-b", help="Browser for Watch Later cookies"),
    ] = "chrome",
) -> None:
    """Backup all playlists to local database."""
    console.print("[cyan]Starting backup...[/cyan]")

    # Fetch playlists via API
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching playlists...", total=None)
        playlists = get_my_playlists()
        progress.update(task, description=f"Found {len(playlists)} playlists")

    console.print(f"[green]Found {len(playlists)} playlists[/green]")

    # Start transaction for all database writes
    database.begin_transaction()
    try:
        # Backup each playlist
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Backing up playlists...", total=len(playlists))

            for playlist in playlists:
                progress.update(task, description=f"Backing up: {playlist.title[:30]}...")

                # Save playlist metadata
                database.upsert_playlist(playlist)

                # Fetch and save items
                try:
                    videos, items = get_playlist_items_api(playlist.playlist_id)

                    current_item_ids = set()
                    for video, item in zip(videos, items):
                        database.upsert_video(video)
                        database.upsert_playlist_item(item)
                        current_item_ids.add(item.item_id)

                    # Mark removed items
                    database.mark_removed_items(playlist.playlist_id, current_item_ids)

                except Exception as e:
                    console.print(f"[yellow]Warning: Could not backup {playlist.title}: {e}[/yellow]")

                progress.advance(task)

        # Backup Watch Later if requested
        if watch_later:
            console.print("[cyan]Backing up Watch Later (via yt-dlp)...[/cyan]")
            try:
                wl_playlist, wl_videos, wl_items = get_watch_later(browser=browser)

                database.upsert_playlist(wl_playlist)

                current_item_ids = set()
                for video, item in zip(wl_videos, wl_items):
                    database.upsert_video(video)
                    database.upsert_playlist_item(item)
                    current_item_ids.add(item.item_id)

                database.mark_removed_items(WATCH_LATER_PLAYLIST_ID, current_item_ids)

                console.print(f"[green]Backed up Watch Later ({len(wl_items)} items)[/green]")
            except Exception as e:
                console.print(f"[red]Error backing up Watch Later: {e}[/red]")

        # Commit all writes as a single snapshot
        database.commit_transaction()
        console.print("[green]Backup complete![/green]")

    except Exception as e:
        database.rollback_transaction()
        console.print(f"[red]Backup failed, rolled back: {e}[/red]")
        raise typer.Exit(1)
