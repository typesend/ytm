"""Browser automation for Watch Later management using undetected-chromedriver."""

import time
from datetime import datetime, timedelta

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ytm.config import get_data_dir

console = Console()


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

    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException

    deleted_ids = []
    items_to_process = items_to_delete[:batch_size]

    console.print(f"[cyan]Opening browser to delete {len(items_to_process)} items...[/cyan]")

    # Use a dedicated profile for ytm to avoid conflicts with main Chrome
    ytm_profile = get_data_dir() / "chrome-profile"
    ytm_profile.mkdir(parents=True, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={ytm_profile}")

    driver = None
    try:
        # Get Chrome version
        import subprocess
        result = subprocess.run(
            ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"],
            capture_output=True, text=True
        )
        chrome_version = int(result.stdout.strip().split()[-1].split('.')[0])
        console.print(f"[dim]Detected Chrome version {chrome_version}[/dim]")

        console.print("[dim]Launching Chrome...[/dim]")
        driver = uc.Chrome(options=options, version_main=chrome_version)
        console.print("[dim]Chrome launched.[/dim]")

        # Navigate to Watch Later
        console.print("[dim]Navigating to Watch Later...[/dim]")
        driver.get("https://www.youtube.com/playlist?list=WL")
        time.sleep(3)

        # Check if we need to log in (Watch Later requires authentication)
        if "Sign in" in driver.page_source or "Playlist doesn't exist" in driver.page_source:
            console.print("\n[yellow]Please log in to YouTube in the browser window.[/yellow]")
            console.print("[yellow]Press Enter after you've logged in...[/yellow]")
            input()
            # Navigate again after login
            driver.get("https://www.youtube.com/playlist?list=WL")
            time.sleep(3)

        # Verify Watch Later page loaded correctly
        page_source = driver.page_source
        if "Playlist doesn't exist" in page_source:
            console.print("[red]Error: Watch Later playlist not accessible. Are you logged into the correct account?[/red]")
            return []

        if "Watch later" not in page_source and "Watch Later" not in page_source:
            console.print("[red]Error: Watch Later page did not load correctly.[/red]")
            console.print("[yellow]Current URL: " + driver.current_url + "[/yellow]")
            return []

        # Sort by oldest first so we can find the items we want to delete
        console.print("[dim]Sorting by oldest first...[/dim]")
        try:
            # Click the sort dropdown
            sort_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'yt-sort-filter-sub-menu-renderer yt-dropdown-menu'))
            )
            sort_button.click()
            time.sleep(0.5)

            # Click "Date added (oldest)"
            oldest_option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//tp-yt-paper-listbox//a[contains(., "Date added (oldest)")]'))
            )
            oldest_option.click()
            time.sleep(2)  # Wait for re-sort
            console.print("[dim]Sorted by oldest.[/dim]")
        except Exception as e:
            console.print(f"[yellow]Could not change sort order: {e}[/yellow]")
            console.print("[yellow]Continuing with current order...[/yellow]")

        console.print("[dim]Starting deletion...[/dim]")

        # Delete items directly from the page (already sorted oldest first)
        deleted_count = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Deleting items...", total=batch_size)

            while deleted_count < batch_size:
                try:
                    # Always get the first video in the list (oldest, since we sorted)
                    video_elements = driver.find_elements(By.CSS_SELECTOR, 'ytd-playlist-video-renderer')

                    if not video_elements:
                        console.print("[yellow]No more videos found on page.[/yellow]")
                        break

                    video_element = video_elements[0]

                    # Get video title for display
                    try:
                        title_el = video_element.find_element(By.CSS_SELECTOR, '#video-title')
                        title = title_el.text[:40] if title_el.text else "Unknown"
                    except:
                        title = "Unknown"

                    progress.update(task, description=f"Deleting: {title}...")

                    # Scroll into view and hover
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", video_element)
                    time.sleep(0.3)

                    ActionChains(driver).move_to_element(video_element).perform()
                    time.sleep(0.5)

                    # Click the 3-dot menu button
                    menu_button = video_element.find_element(By.CSS_SELECTOR, 'button[aria-label="Action menu"]')
                    menu_button.click()
                    time.sleep(0.5)

                    # Click "Remove from Watch Later"
                    remove_option = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//ytd-menu-service-item-renderer[contains(., "Remove from")]'))
                    )
                    remove_option.click()

                    deleted_count += 1
                    deleted_ids.append(title)  # Track by title since we don't have IDs
                    time.sleep(delay)

                except TimeoutException:
                    console.print(f"[yellow]Timeout, retrying...[/yellow]")
                    time.sleep(1)
                except NoSuchElementException:
                    console.print(f"[yellow]Element not found, retrying...[/yellow]")
                    time.sleep(1)
                except Exception as e:
                    console.print(f"[yellow]Error: {e}[/yellow]")
                    break

                progress.update(task, completed=deleted_count)

    except Exception as e:
        console.print(f"[red]Browser automation error: {e}[/red]")
    finally:
        if driver:
            driver.quit()

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
