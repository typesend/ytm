"""Typer CLI entry point for YouTube Playlist Manager."""

import typer
from rich.console import Console

from ytm.commands import backup, delete, empty, history, list_cmd, prune, restore

app = typer.Typer(
    name="ytm",
    help="YouTube Playlist Manager with time-travel capabilities.",
    no_args_is_help=True,
)
console = Console()

# Auth subcommands
auth_app = typer.Typer(help="Authentication commands.")
app.add_typer(auth_app, name="auth")


@auth_app.command("login")
def auth_login() -> None:
    """Authenticate with YouTube via OAuth2."""
    from ytm.auth.oauth import authenticate

    authenticate()
    console.print("[green]Successfully authenticated with YouTube![/green]")


@auth_app.command("logout")
def auth_logout() -> None:
    """Clear stored credentials."""
    from ytm.auth.oauth import logout

    logout()
    console.print("[yellow]Credentials cleared.[/yellow]")


# Register command modules
app.command("backup")(backup.backup)

# List subcommands
list_app = typer.Typer(help="List playlists and items.")
app.add_typer(list_app, name="list")
list_app.command("playlists")(list_cmd.list_playlists)
list_app.command("items")(list_cmd.list_items)

# History subcommands
history_app = typer.Typer(help="View backup history and snapshots.")
app.add_typer(history_app, name="history")
history_app.command("snapshots")(history.list_snapshots)
history_app.command("diff")(history.diff_versions)

# Playlist management commands
app.command("delete")(delete.delete_playlist)
app.command("empty")(empty.empty_playlist)
app.command("prune")(prune.prune_watch_later)
app.command("restore")(restore.restore_playlist)


if __name__ == "__main__":
    app()
