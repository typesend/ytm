"""Delete playlist command."""

from typing import Annotated

import typer
from rich.console import Console

from ytm.core.youtube_api import delete_playlist as api_delete_playlist

console = Console()


def delete_playlist(
    playlist_id: Annotated[str, typer.Argument(help="Playlist ID to delete from YouTube")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Delete a playlist from YouTube (keeps local backup)."""
    if playlist_id == "WL":
        console.print("[red]Error: Cannot delete Watch Later playlist.[/red]")
        console.print("Use 'ytm prune WL' to remove old items instead.")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(
            f"Delete playlist {playlist_id} from YouTube? (Local backup will be kept)"
        )
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    console.print(f"[cyan]Deleting playlist {playlist_id}...[/cyan]")

    if api_delete_playlist(playlist_id):
        console.print("[green]Playlist deleted from YouTube.[/green]")
        console.print("[dim]Local backup has been preserved.[/dim]")
    else:
        console.print("[red]Failed to delete playlist.[/red]")
        raise typer.Exit(1)
