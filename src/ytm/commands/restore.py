"""Restore playlist command."""

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from ytm.config import WATCH_LATER_PLAYLIST_ID
from ytm.core import database
from ytm.core.youtube_api import add_to_playlist, create_playlist

console = Console()


def restore_playlist(
    playlist_id: Annotated[str, typer.Argument(help="Source playlist ID to restore from")],
    to_playlist: Annotated[
        Optional[str],
        typer.Option("--to-playlist", "-t", help="Target playlist ID (creates new if not exists)"),
    ] = None,
    from_version: Annotated[
        Optional[int],
        typer.Option("--from-version", "-v", help="Restore from specific snapshot version"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be restored"),
    ] = False,
    create_new: Annotated[
        Optional[str],
        typer.Option("--create-new", "-c", help="Create new playlist with this name"),
    ] = None,
) -> None:
    """Restore items from local backup to YouTube playlist."""
    # Validate target
    if not to_playlist and not create_new:
        console.print("[red]Error: Must specify --to-playlist or --create-new[/red]")
        raise typer.Exit(1)

    if to_playlist and to_playlist.upper() == "WL":
        console.print("[red]Error: Cannot restore TO Watch Later.[/red]")
        console.print("YouTube API does not allow adding items to Watch Later.")
        console.print("Restore to a different playlist instead.")
        raise typer.Exit(1)

    # Get items from backup
    console.print(f"[cyan]Loading backup of {playlist_id}...[/cyan]")

    items = database.get_playlist_items(
        playlist_id,
        at_version=from_version,
        include_removed=False,
    )

    if not items:
        console.print(f"[yellow]No items found for playlist {playlist_id}.[/yellow]")
        if from_version:
            console.print(f"[dim]Try a different version or check 'ytm history snapshots'[/dim]")
        raise typer.Exit(1)

    console.print(f"Found {len(items)} items to restore.")

    if dry_run:
        console.print("\n[yellow]Dry run - preview of items to restore:[/yellow]")
        for item in items[:10]:
            console.print(f"  + {item.get('title', 'Unknown')[:50]}")
        if len(items) > 10:
            console.print(f"  ... and {len(items) - 10} more")
        return

    # Create new playlist if requested
    target_id = to_playlist
    if create_new:
        console.print(f"[cyan]Creating playlist '{create_new}'...[/cyan]")
        target_id = create_playlist(create_new, description=f"Restored from {playlist_id}")
        if not target_id:
            console.print("[red]Failed to create playlist.[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Created playlist: {target_id}[/green]")

    # Confirm
    if not typer.confirm(f"\nRestore {len(items)} items to playlist {target_id}?"):
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)

    # Restore items
    added_count = 0
    failed_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Restoring items...", total=len(items))

        for item in items:
            title = item.get("title", "Unknown")[:30]
            progress.update(task, description=f"Adding: {title}...")

            result = add_to_playlist(target_id, item["video_id"])
            if result:
                added_count += 1
            else:
                failed_count += 1

            progress.advance(task)

    console.print(f"\n[green]Restored {added_count} items.[/green]")
    if failed_count:
        console.print(f"[yellow]Failed to restore {failed_count} items (may be unavailable).[/yellow]")

    console.print(f"\n[dim]View at: https://www.youtube.com/playlist?list={target_id}[/dim]")
