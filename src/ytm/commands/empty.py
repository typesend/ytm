"""Empty playlist command."""

from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from ytm.core.youtube_api import delete_playlist_item, get_playlist_items_api

console = Console()


def empty_playlist(
    playlist_id: Annotated[str, typer.Argument(help="Playlist ID to empty")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be deleted"),
    ] = False,
) -> None:
    """Remove all items from a playlist on YouTube."""
    if playlist_id == "WL":
        console.print("[red]Error: Cannot empty Watch Later via API.[/red]")
        console.print("Use 'ytm prune WL --older-than 0d' to empty Watch Later.")
        raise typer.Exit(1)

    console.print(f"[cyan]Fetching items from {playlist_id}...[/cyan]")

    try:
        videos, items = get_playlist_items_api(playlist_id)
    except Exception as e:
        console.print(f"[red]Error fetching playlist: {e}[/red]")
        raise typer.Exit(1)

    if not items:
        console.print("[yellow]Playlist is already empty.[/yellow]")
        return

    console.print(f"Found {len(items)} items in playlist.")

    if dry_run:
        console.print("[yellow]Dry run - no items will be deleted[/yellow]")
        for item in items[:10]:
            video = next((v for v in videos if v.video_id == item.video_id), None)
            title = video.title if video else "Unknown"
            console.print(f"  Would delete: {title}")
        if len(items) > 10:
            console.print(f"  ... and {len(items) - 10} more")
        return

    if not force:
        confirm = typer.confirm(f"Remove all {len(items)} items from playlist?")
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    deleted_count = 0
    failed_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Deleting items...", total=len(items))

        for item in items:
            video = next((v for v in videos if v.video_id == item.video_id), None)
            title = video.title if video else "Unknown"
            progress.update(task, description=f"Deleting: {title[:30]}...")

            if delete_playlist_item(item.item_id):
                deleted_count += 1
            else:
                failed_count += 1

            progress.advance(task)

    console.print(f"[green]Deleted {deleted_count} items.[/green]")
    if failed_count:
        console.print(f"[yellow]Failed to delete {failed_count} items.[/yellow]")
