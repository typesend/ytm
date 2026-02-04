"""Prune Watch Later command using browser automation."""

import re
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ytm.config import WATCH_LATER_PLAYLIST_ID
from ytm.core import database
from ytm.core.browser import get_items_older_than, prune_watch_later_items

console = Console()


def parse_duration(duration_str: str) -> int:
    """Parse duration string like '30d', '2w', '90d' into days."""
    match = re.match(r"^(\d+)([dwm])$", duration_str.lower())
    if not match:
        raise typer.BadParameter(
            f"Invalid duration format: {duration_str}. Use format like '30d', '2w', or '3m'"
        )

    value = int(match.group(1))
    unit = match.group(2)

    if unit == "d":
        return value
    elif unit == "w":
        return value * 7
    elif unit == "m":
        return value * 30
    else:
        raise typer.BadParameter(f"Unknown duration unit: {unit}")


def prune_watch_later(
    playlist_id: Annotated[str, typer.Argument(help="Playlist ID (must be 'WL')")],
    older_than: Annotated[
        str,
        typer.Option("--older-than", "-o", help="Delete items older than (e.g., '30d', '2w')"),
    ] = "90d",
    batch_size: Annotated[
        int,
        typer.Option("--batch-size", "-b", help="Number of items to delete per run"),
    ] = 50,
    delay: Annotated[
        float,
        typer.Option("--delay", "-d", help="Seconds between deletions"),
    ] = 2.0,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be deleted"),
    ] = False,
) -> None:
    """Prune old items from Watch Later using browser automation."""
    if playlist_id.upper() != "WL":
        console.print("[red]Error: Prune command only works with Watch Later (WL).[/red]")
        console.print("Use 'ytm empty PLAYLIST_ID' for other playlists.")
        raise typer.Exit(1)

    # Parse duration
    try:
        days = parse_duration(older_than)
    except typer.BadParameter as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Finding items older than {days} days...[/cyan]")

    # Get items from database
    items = database.get_playlist_items(WATCH_LATER_PLAYLIST_ID)

    if not items:
        console.print("[yellow]No Watch Later items in database.[/yellow]")
        console.print("Run 'ytm backup --watch-later' first.")
        raise typer.Exit(1)

    # Filter to old items
    old_items = get_items_older_than(items, days)

    if not old_items:
        console.print(f"[green]No items older than {days} days found.[/green]")
        return

    console.print(f"Found {len(old_items)} items older than {days} days.")

    # Show preview
    table = Table(title="Items to Prune")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Title", style="yellow")
    table.add_column("Channel")
    table.add_column("Added")

    for i, item in enumerate(old_items[:batch_size]):
        added = item.get("added_at") or item.get("first_seen_at")
        if added:
            added_str = str(added)[:10]
        else:
            added_str = "-"

        table.add_row(
            str(i + 1),
            (item.get("title") or "Unknown")[:40],
            (item.get("channel_title") or "-")[:20],
            added_str,
        )

    if len(old_items) > batch_size:
        table.add_row("...", f"and {len(old_items) - batch_size} more", "", "")

    console.print(table)

    if dry_run:
        console.print(f"\n[yellow]Dry run: Would delete {min(len(old_items), batch_size)} items[/yellow]")
        return

    # Confirm
    if not typer.confirm(f"\nDelete {min(len(old_items), batch_size)} items?"):
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)

    # Perform deletion via browser
    deleted_ids = prune_watch_later_items(
        old_items,
        batch_size=batch_size,
        delay=delay,
        dry_run=False,
    )

    console.print(f"\n[green]Successfully deleted {len(deleted_ids)} items.[/green]")

    if len(old_items) > batch_size:
        remaining = len(old_items) - len(deleted_ids)
        console.print(f"[dim]{remaining} old items remaining. Run again to delete more.[/dim]")
