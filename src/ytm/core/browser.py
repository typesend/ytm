"""Playwright browser automation for Watch Later management."""

import subprocess
import sys
import time
from datetime import datetime, timedelta

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ytm.config import CHROME_PATH_MACOS, CHROME_USER_DATA_MACOS

console = Console()


def is_chrome_running() -> bool:
    """Check if Chrome is currently running."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "Google Chrome"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def prune_watch_later_items(
    items_to_delete: list[dict],
    batch_size: int = 50,
    delay: float = 2.0,
    dry_run: bool = False,
) -> list[str]:
    """Delete items from Watch Later using browser automation.

    Args:
        items_to_delete: List of items with video_id and title keys
        batch_size: Number of items to delete before stopping
        delay: Seconds to wait between deletions
        dry_run: If True, just return what would be deleted

    Returns:
        List of video IDs that were successfully deleted
    """
    if dry_run:
        console.print("[yellow]Dry run - no items will be deleted[/yellow]")
        return [item["video_id"] for item in items_to_delete[:batch_size]]

    if is_chrome_running():
        console.print(
            "[red]Error: Google Chrome must be completely closed before pruning.[/red]\n"
            "Please close Chrome and try again."
        )
        return []

    # Import playwright here to avoid startup cost when not needed
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    deleted_ids = []
    items_to_process = items_to_delete[:batch_size]

    console.print(f"[cyan]Opening browser to delete {len(items_to_process)} items...[/cyan]")

    with sync_playwright() as p:
        try:
            # Launch Chrome with existing user profile
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(CHROME_USER_DATA_MACOS),
                executable_path=str(CHROME_PATH_MACOS),
                headless=False,
                channel="chrome",
            )
        except Exception as e:
            console.print(f"[red]Failed to launch Chrome: {e}[/red]")
            console.print(
                "[yellow]Make sure Chrome is completely closed and try again.[/yellow]"
            )
            return []

        page = browser.new_page()

        try:
            # Navigate to Watch Later
            page.goto("https://www.youtube.com/playlist?list=WL")
            page.wait_for_load_state("networkidle")
            time.sleep(2)  # Extra wait for dynamic content

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Deleting items...", total=len(items_to_process))

                for item in items_to_process:
                    video_id = item["video_id"]
                    title = item.get("title", "Unknown")

                    progress.update(task, description=f"Deleting: {title[:40]}...")

                    try:
                        # Find the video row by video ID
                        video_selector = f'ytd-playlist-video-renderer:has(a[href*="{video_id}"])'
                        video_element = page.locator(video_selector).first

                        if not video_element.is_visible():
                            console.print(f"[yellow]Video not found: {title}[/yellow]")
                            progress.advance(task)
                            continue

                        # Hover to reveal menu button
                        video_element.hover()
                        time.sleep(0.5)

                        # Click the 3-dot menu button
                        menu_button = video_element.locator(
                            'button[aria-label="Action menu"]'
                        ).first
                        menu_button.click()
                        time.sleep(0.5)

                        # Click "Remove from Watch Later"
                        remove_button = page.locator(
                            'ytd-menu-service-item-renderer:has-text("Remove from")'
                        ).first
                        remove_button.click()

                        deleted_ids.append(video_id)
                        time.sleep(delay)

                    except PlaywrightTimeout:
                        console.print(f"[yellow]Timeout for: {title}[/yellow]")
                    except Exception as e:
                        console.print(f"[yellow]Error deleting {title}: {e}[/yellow]")

                    progress.advance(task)

        except Exception as e:
            console.print(f"[red]Browser automation error: {e}[/red]")
        finally:
            browser.close()

    return deleted_ids


def get_items_older_than(
    items: list[dict], days: int
) -> list[dict]:
    """Filter items to those added more than N days ago.

    Args:
        items: List of playlist items with added_at or first_seen_at
        days: Number of days threshold

    Returns:
        Items older than the threshold
    """
    cutoff = datetime.now() - timedelta(days=days)
    old_items = []

    for item in items:
        # Use added_at if available, fall back to first_seen_at
        added_at = item.get("added_at") or item.get("first_seen_at")

        if added_at is None:
            continue

        # Handle both datetime objects and strings
        if isinstance(added_at, str):
            try:
                added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))
            except ValueError:
                continue

        # Make cutoff timezone-aware if added_at is
        if added_at.tzinfo is not None:
            from datetime import timezone
            cutoff = cutoff.replace(tzinfo=timezone.utc)

        if added_at < cutoff:
            old_items.append(item)

    return old_items
