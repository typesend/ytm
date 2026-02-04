"""OAuth2 authentication for YouTube API."""

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from rich.console import Console

from ytm.config import CLIENT_SECRETS_FILE, SCOPES, TOKEN_FILE

console = Console()


def get_credentials() -> Credentials | None:
    """Get valid credentials, refreshing if necessary."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds)
        except Exception:
            creds = None

    return creds


def authenticate() -> Credentials:
    """Run OAuth2 flow to get credentials."""
    creds = get_credentials()

    if creds and creds.valid:
        console.print("[dim]Using existing valid credentials.[/dim]")
        return creds

    # Find client_secrets.json
    secrets_path = _find_client_secrets()
    if not secrets_path:
        console.print(
            "[red]Error: client_secrets.json not found.[/red]\n"
            "Please download OAuth2 credentials from Google Cloud Console\n"
            "and save as 'client_secrets.json' in the current directory."
        )
        raise typer.Exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds)

    return creds


def _find_client_secrets() -> Path | None:
    """Find client_secrets.json in current dir or config dir."""
    locations = [
        Path.cwd() / CLIENT_SECRETS_FILE,
        TOKEN_FILE.parent / CLIENT_SECRETS_FILE,
    ]
    for loc in locations:
        if loc.exists():
            return loc
    return None


def _save_credentials(creds: Credentials) -> None:
    """Save credentials to token file with secure permissions."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)

    # Set secure permissions (owner read/write only)
    os.chmod(TOKEN_FILE, 0o600)


def logout() -> None:
    """Remove stored credentials."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def require_auth() -> Credentials:
    """Get credentials or exit with error."""
    import typer

    creds = get_credentials()
    if not creds or not creds.valid:
        console.print(
            "[red]Not authenticated. Run 'ytm auth login' first.[/red]"
        )
        raise typer.Exit(1)
    return creds


# Import typer here to avoid circular import
import typer
