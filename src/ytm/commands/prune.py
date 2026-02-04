"""Prune Watch Later command using browser automation."""

from typing import Annotated, Optional

import typer
from rich.console import Console

from ytm.core.browser import prune_watch_later_items

console = Console()


def prune_watch_later(
    playlist_id: Annotated[str, typer.Argument(help="Playlist ID (must be 'WL')")],
    count: Annotated[
        Optional[int],
        typer.Option("--count", "-c", help="Delete N oldest items from Watch Later"),
    ] = None,
    all_items: Annotated[
        bool,
        typer.Option("--all", "-a", help="Delete ALL items from Watch Later"),
    ] = False,
    batch_size: Annotated[
        int,
        typer.Option("--batch-size", "-b", help="Items per browser session (default: 50)"),
    ] = 50,
    delay: Annotated[
        float,
        typer.Option("--delay", "-d", help="Seconds between deletions (default: 2.0)"),
    ] = 2.0,
) -> None:
    """Prune items from Watch Later using browser automation.

    YouTube's API doesn't allow modifying Watch Later, so this command opens
    a real Chrome browser to delete items directly from the page.

    \b
    How it works:
      1. Opens Chrome with a dedicated profile (persists your YouTube login)
      2. Navigates to youtube.com/playlist?list=WL
      3. Sorts by "Date added (oldest)" so oldest items appear first
      4. Deletes items from the top of the list one by one

    \b
    Examples:
      ytm prune WL --count 100      Delete the 100 oldest items
      ytm prune WL --all            Delete everything
      ytm prune WL -c 50 -b 25      Delete 50 items, 25 per browser session

    \b
    Notes:
      - First run will prompt you to log in to YouTube
      - Your login persists in ~/.local/share/ytm/chrome-profile/
      - Local backup is NOT modified (use 'ytm backup' to sync after pruning)
      - Uses undetected-chromedriver to avoid Google's bot detection
    """
    if playlist_id.upper() != "WL":
        console.print("[red]Error: Prune command only works with Watch Later (WL).[/red]")
        console.print("Use 'ytm empty PLAYLIST_ID' for other playlists.")
        raise typer.Exit(1)

    if not count and not all_items:
        console.print("[red]Error: Specify --count N or --all[/red]")
        raise typer.Exit(1)

    if count and all_items:
        console.print("[red]Error: Use either --count or --all, not both[/red]")
        raise typer.Exit(1)

    # Determine how many to delete
    if all_items:
        # Use a very large number; browser will stop when no more items
        delete_count = 10000
        console.print("[cyan]Will delete ALL items from Watch Later.[/cyan]")
    else:
        delete_count = count
        console.print(f"[cyan]Will delete {count} oldest items from Watch Later.[/cyan]")

    # Respect batch_size
    items_this_run = min(delete_count, batch_size)

    if not typer.confirm(f"\nDelete up to {items_this_run} items?"):
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)

    # Perform deletion via browser
    deleted = prune_watch_later_items(
        items_to_delete=[],  # Not used anymore
        batch_size=items_this_run,
        delay=delay,
    )

    console.print(f"\n[green]Successfully deleted {len(deleted)} items.[/green]")

    if delete_count > items_this_run:
        console.print(f"[dim]Run again to delete more.[/dim]")
