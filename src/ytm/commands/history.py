"""History commands for viewing snapshots and diffs."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ytm.core import database

console = Console()


def list_snapshots() -> None:
    """List all DuckLake snapshots."""
    snapshots = database.get_snapshots()

    if not snapshots:
        console.print("[yellow]No snapshots found.[/yellow]")
        console.print("Run 'ytm backup' to create your first snapshot.")
        return

    table = Table(title="Database Snapshots")
    table.add_column("Version", style="cyan", justify="right")
    table.add_column("Timestamp", style="green")
    table.add_column("Schema Version", justify="right")

    for snap in snapshots:
        table.add_row(
            str(snap.get("snapshot_id", "-")),
            str(snap.get("snapshot_time", "-"))[:19],
            str(snap.get("schema_version", "-")),
        )

    console.print(table)
    console.print(f"[dim]Total: {len(snapshots)} snapshots[/dim]")


def diff_versions(
    version1: Annotated[int, typer.Argument(help="First version to compare")],
    version2: Annotated[int, typer.Argument(help="Second version to compare")],
) -> None:
    """Compare two snapshot versions."""
    try:
        changes = database.get_snapshot_changes(version1, version2)
    except Exception as e:
        console.print(f"[red]Error comparing versions: {e}[/red]")
        return

    console.print(f"[cyan]Changes from version {version1} to {version2}:[/cyan]\n")

    # Playlists
    if changes["playlists_added"]:
        console.print(f"[green]Playlists added ({len(changes['playlists_added'])}):[/green]")
        for pid in changes["playlists_added"]:
            console.print(f"  + {pid}")

    if changes["playlists_removed"]:
        console.print(f"[red]Playlists removed ({len(changes['playlists_removed'])}):[/red]")
        for pid in changes["playlists_removed"]:
            console.print(f"  - {pid}")

    # Items
    if changes["items_added"]:
        console.print(f"[green]Items added ({len(changes['items_added'])}):[/green]")
        for item_id in changes["items_added"][:10]:
            console.print(f"  + {item_id}")
        if len(changes["items_added"]) > 10:
            console.print(f"  ... and {len(changes['items_added']) - 10} more")

    if changes["items_removed"]:
        console.print(f"[red]Items removed ({len(changes['items_removed'])}):[/red]")
        for item_id in changes["items_removed"][:10]:
            console.print(f"  - {item_id}")
        if len(changes["items_removed"]) > 10:
            console.print(f"  ... and {len(changes['items_removed']) - 10} more")

    if not any(changes.values()):
        console.print("[dim]No changes between these versions.[/dim]")
