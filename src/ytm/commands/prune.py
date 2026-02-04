"""Prune Watch Later command using browser automation."""

import re
from typing import Annotated, Optional

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
        Optional[str],
        typer.Option("--older-than", "-o", help="Delete items older than (e.g., '30d', '2w')"),
    ] = None,
    count: Annotated[
        Optional[int],
        typer.Option("--count", "-c", help="Delete the N oldest items (by position, from bottom of list)"),
    ] = None,
    all_items: Annotated[
        bool,
        typer.Option("--all", "-a", help="Delete all items in Watch Later"),
    ] = False,
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
    """Prune items from Watch Later using browser automation.

    Select items to delete using one of: --older-than, --count, or --all.
    If none specified, defaults to --older-than 90d.
    """
    if playlist_id.upper() != "WL":
        console.print("[red]Error: Prune command only works with Watch Later (WL).[/red]")
        console.print("Use 'ytm empty PLAYLIST_ID' for other playlists.")
        raise typer.Exit(1)

    # Validate options - only one selection method allowed
    options_set = sum([older_than is not None, count is not None, all_items])
    if options_set > 1:
        console.print("[red]Error: Use only one of --older-than, --count, or --all[/red]")
        raise typer.Exit(1)

    # Default to --older-than 90d if nothing specified
    if options_set == 0:
        older_than = "90d"

    # Get items from database
    items = database.get_playlist_items(WATCH_LATER_PLAYLIST_ID)

    if not items:
        console.print("[yellow]No Watch Later items in database.[/yellow]")
        console.print("Run 'ytm backup --watch-later' first.")
        raise typer.Exit(1)

    # Select items based on the chosen method
    if all_items:
        console.print("[cyan]Selecting all items...[/cyan]")
        selected_items = items
    elif count is not None:
        console.print(f"[cyan]Selecting {count} oldest items (from bottom of list)...[/cyan]")
        # Oldest items are at the highest positions (bottom of the list)
        sorted_by_position = sorted(items, key=lambda x: x.get("position", 0), reverse=True)
        selected_items = sorted_by_position[:count]
    else:
        # --older-than
        try:
            days = parse_duration(older_than)
        except typer.BadParameter as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)
        console.print(f"[cyan]Finding items older than {days} days...[/cyan]")
        selected_items = get_items_older_than(items, days)

    if not selected_items:
        console.print("[green]No items matched the selection criteria.[/green]")
        return

    console.print(f"Found {len(selected_items)} items to prune.")

    # Show preview
    table = Table(title="Items to Prune")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Pos", justify="right", style="dim")
    table.add_column("Title", style="yellow")
    table.add_column("Channel")

    items_to_show = selected_items[:batch_size]
    for i, item in enumerate(items_to_show):
        table.add_row(
            str(i + 1),
            str(item.get("position", "?")),
            (item.get("title") or "Unknown")[:40],
            (item.get("channel_title") or "-")[:20],
        )

    if len(selected_items) > batch_size:
        table.add_row("...", "", f"and {len(selected_items) - batch_size} more", "")

    console.print(table)

    if dry_run:
        console.print(f"\n[yellow]Dry run: Would delete {min(len(selected_items), batch_size)} items[/yellow]")
        return

    # Confirm
    if not typer.confirm(f"\nDelete {min(len(selected_items), batch_size)} items?"):
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)

    # Perform deletion via browser
    deleted_ids = prune_watch_later_items(
        selected_items,
        batch_size=batch_size,
        delay=delay,
        dry_run=False,
    )

    console.print(f"\n[green]Successfully deleted {len(deleted_ids)} items.[/green]")

    if len(selected_items) > batch_size:
        remaining = len(selected_items) - len(deleted_ids)
        console.print(f"[dim]{remaining} items remaining. Run again to delete more.[/dim]")
