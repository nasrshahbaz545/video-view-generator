from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

APP_NAME = "Three-Window Video Viewer"
APP_VERSION = "2.2"
BASE_DIR = Path(__file__).resolve().parent
MIN_WINDOWS = 1
MAX_WINDOWS = 50
MAX_CYCLES = 100
FOCUS_SECONDS = 3


@dataclass
class Settings:
    url: str
    browser: str
    watch_seconds: int
    window_count: int
    cycles: int


def prompt_int(message: str, default: int, minimum: int, maximum: int) -> int:
    while True:
        raw = input(f"{message} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if minimum <= value <= maximum:
            return value
        print(f"Please enter a number from {minimum} to {maximum}.")


def choose_browser() -> str:
    print("\nChoose browser:")
    print("  1. Playwright Chromium")
    print("  2. Google Chrome (installed)")
    print("  3. Microsoft Edge (installed)")
    print("  4. Playwright Firefox")

    choices = {
        "1": "chromium",
        "2": "chrome",
        "3": "msedge",
        "4": "firefox",
    }

    while True:
        choice = input("Selection [1]: ").strip() or "1"
        if choice in choices:
            return choices[choice]
        print("Please choose 1, 2, 3, or 4.")


def choose_cycles() -> int:
    print("\nRestart loop:")
    print("  1. Play once, then close")
    print("  2. Play once, close browser, then restart one final time")

    while True:
        choice = input("Selection [1]: ").strip() or "1"
        if choice in {"1", "2", "3","4","5","6","7","8","9","10","11","12","13"}:
            return int(choice)
        print("Please choose 1 or 2.")


def validate_url(raw: str) -> str:
    value = raw.strip().strip('"')
    if not value:
        raise ValueError("No URL or file path was entered.")

    local_file = Path(value)
    if local_file.exists() and local_file.is_file():
        return local_file.resolve().as_uri()

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https", "file"}:
        raise ValueError(
            "Enter a complete HTTP/HTTPS URL or an existing local video file."
        )
    if parsed.scheme in {"http", "https"} and not parsed.hostname:
        raise ValueError("The URL does not contain a valid hostname.")
    return value


def collect_settings() -> Settings:
    print(f"\n{APP_NAME} v{APP_VERSION}")
    print(
        f"Hard limits: {MAX_WINDOWS} browser windows and "
        f"{MAX_CYCLES} cycles.\n"
    )

    while True:
        try:
            url = validate_url(
                input("Paste the Telegram/video URL or local path: ")
            )
            break
        except ValueError as exc:
            print(f"[INVALID] {exc}\n")

    browser = choose_browser()
    watch_seconds = prompt_int(
        "Watch time per cycle in seconds",
        60,
        5,
        86400,
    )
    window_count = prompt_int(
        f"Number of separate browser windows (maximum {MAX_WINDOWS})",
        3,
        MIN_WINDOWS,
        MAX_WINDOWS,
    )
    cycles = choose_cycles()

    return Settings(
        url=url,
        browser=browser,
        watch_seconds=watch_seconds,
        window_count=window_count,
        cycles=cycles,
    )


async def try_play_html5_video(page: Page) -> int:
    script = """
    () => {
        const videos = Array.from(document.querySelectorAll('video'));

        for (const video of videos) {
            video.muted = true;
            video.autoplay = true;
            video.playsInline = true;
            video.play().catch(() => {});
        }

        return videos.length;
    }
    """

    total = 0
    for frame in page.frames:
        try:
            total += int(await frame.evaluate(script))
        except Exception:
            pass
    return total


async def playback_keeper(
    pages: list[Page],
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        for number, page in enumerate(pages, start=1):
            if page.is_closed():
                continue

            try:
                count = await try_play_html5_video(page)
                if count:
                    print(
                        f"\n[Window {number}] Playback check: "
                        f"{count} video element(s)."
                    )
            except Exception:
                pass

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=10,
            )
        except asyncio.TimeoutError:
            pass


async def focus_rotator(
    pages: list[Page],
    stop_event: asyncio.Event,
    focus_seconds: int = FOCUS_SECONDS,
) -> None:
    """Bring each Playwright-managed page/window to the front in sequence."""

    while not stop_event.is_set():
        open_pages = [page for page in pages if not page.is_closed()]
        if not open_pages:
            return

        for number, page in enumerate(open_pages, start=1):
            if stop_event.is_set():
                return

            try:
                await page.bring_to_front()
                await try_play_html5_video(page)
                print(
                    f"\n[Focus] Window {number} brought to the foreground."
                )
            except Exception as exc:
                print(
                    f"\n[Focus] Window {number} skipped: "
                    f"{type(exc).__name__}"
                )

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=focus_seconds,
                )
                return
            except asyncio.TimeoutError:
                pass


async def launch_context(
    playwright: Playwright,
    browser_name: str,
) -> BrowserContext:
    profile_dir = BASE_DIR / f"viewer_profile_{browser_name}"

    chromium_args = [
        "--autoplay-policy=no-user-gesture-required",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--start-maximized",
    ]

    if browser_name == "firefox":
        return await playwright.firefox.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            no_viewport=True,
            firefox_user_prefs={
                "media.autoplay.default": 0,
                "media.autoplay.blocking_policy": 0,
                "media.block-autoplay-until-in-foreground": False,
                "media.suspend-bkgnd-video.enabled": False,
            },
        )

    kwargs = {
        "user_data_dir": str(profile_dir),
        "headless": False,
        "no_viewport": True,
        "args": chromium_args,
    }

    if browser_name == "chrome":
        kwargs["channel"] = "chrome"
    elif browser_name == "msedge":
        kwargs["channel"] = "msedge"

    return await playwright.chromium.launch_persistent_context(**kwargs)


async def close_extra_startup_pages(
    context: BrowserContext,
    keep: Page,
) -> None:
    for page in list(context.pages):
        if page != keep and not page.is_closed():
            try:
                await page.close()
            except Exception:
                pass


async def open_new_browser_window(
    context: BrowserContext,
    opener_page: Page,
    url: str,
    window_number: int,
) -> Page:
    width = 850
    height = 700
    left = 20 + ((window_number - 1) * 80)
    top = 20 + ((window_number - 1) * 50)

    async with context.expect_page(timeout=15000) as page_info:
        await opener_page.evaluate(
            """
            ({url, width, height, left, top}) => {
                window.open(
                    url,
                    "_blank",
                    `popup=yes,width=${width},height=${height},left=${left},top=${top}`
                );
            }
            """,
            {
                "url": url,
                "width": width,
                "height": height,
                "left": left,
                "top": top,
            },
        )

    new_page = await page_info.value
    await new_page.wait_for_load_state(
        "domcontentloaded",
        timeout=60000,
    )
    return new_page


async def run_one_cycle(
    playwright: Playwright,
    settings: Settings,
    cycle_number: int,
) -> None:
    context = await launch_context(
        playwright,
        settings.browser,
    )

    pages: list[Page] = []
    stop_event = asyncio.Event()
    keeper_task: asyncio.Task | None = None
    focus_task: asyncio.Task | None = None

    try:
        print(
            f"\n[CYCLE {cycle_number}/{settings.cycles}] "
            f"Opening {settings.window_count} separate browser window(s)..."
        )

        first_page = (
            context.pages[0]
            if context.pages
            else await context.new_page()
        )

        await close_extra_startup_pages(
            context,
            first_page,
        )

        for window_number in range(1, settings.window_count + 1):
            try:
                if window_number == 1:
                    page = first_page
                    await page.goto(
                        settings.url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )
                else:
                    page = await open_new_browser_window(
                        context=context,
                        opener_page=first_page,
                        url=settings.url,
                        window_number=window_number,
                    )

                pages.append(page)
                found = await try_play_html5_video(page)

                print(
                    f"[Window {window_number}] Opened. "
                    f"HTML5 videos found: {found}"
                )

            except Exception as exc:
                print(
                    f"[Window {window_number}] Warning: "
                    f"{type(exc).__name__}: {exc}"
                )

        if not pages:
            print("[ERROR] No browser windows were opened successfully.")
            return

        print(
            "\nIf required, log in and press Play manually once "
            "in each browser window."
        )
        print(
            f"Keeping {len(pages)} browser window(s) open for "
            f"{settings.watch_seconds} seconds."
        )

        # These are two independent tasks. Do not nest one inside the other.
        keeper_task = asyncio.create_task(
            playback_keeper(
                pages,
                stop_event,
            )
        )

        focus_task = asyncio.create_task(
            focus_rotator(
                pages=pages,
                stop_event=stop_event,
                focus_seconds=FOCUS_SECONDS,
            )
        )

        for remaining in range(settings.watch_seconds, 0, -1):
            open_pages = [page for page in pages if not page.is_closed()]

            if not open_pages:
                print(
                    "\n[NOTICE] All browser windows were closed manually; "
                    "ending this cycle."
                )
                break

            print(
                f"\rCycle {cycle_number}: "
                f"{remaining:5d} second(s) remaining | "
                f"Open windows: {len(open_pages)} ",
                end="",
                flush=True,
            )

            await asyncio.sleep(1)

        print()

    finally:
        stop_event.set()

        tasks = [
            task
            for task in (keeper_task, focus_task)
            if task is not None
        ]

        if tasks:
            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

        try:
            await context.close()
        except Exception:
            pass

    print(
        f"[CYCLE {cycle_number}] "
        "Browser windows closed cleanly."
    )


async def run() -> int:
    settings = collect_settings()

    # Defensive limits, even if prompt-related code is edited accidentally.
    settings.window_count = max(
        MIN_WINDOWS,
        min(settings.window_count, MAX_WINDOWS),
    )
    settings.cycles = max(
        1,
        min(settings.cycles, MAX_CYCLES),
    )

    print("\nSelected settings:")
    print(f"  Browser: {settings.browser}")
    print(f"  Watch time: {settings.watch_seconds} seconds")
    print(f"  Browser windows: {settings.window_count}")
    print(f"  Cycles: {settings.cycles}")
    print(f"  Focus rotation interval: {FOCUS_SECONDS} seconds")

    async with async_playwright() as playwright:
        for cycle_number in range(1, settings.cycles + 1):
            try:
                await run_one_cycle(
                    playwright,
                    settings,
                    cycle_number,
                )
            except Exception as exc:
                print(
                    f"\n[ERROR] Cycle {cycle_number} failed: "
                    f"{type(exc).__name__}: {exc}"
                )

                if settings.browser == "firefox":
                    print("Run: python -m playwright install firefox")
                elif settings.browser == "chromium":
                    print("Run: python -m playwright install chromium")
                else:
                    print(
                        "Confirm that the selected browser is installed "
                        "and is not already using the viewer profile folder."
                    )
                return 1

            if cycle_number < settings.cycles:
                print(
                    "Restarting the browser one final time "
                    "after 3 seconds..."
                )
                await asyncio.sleep(3)

    print("\n[DONE] All selected cycles finished.")
    return 0


def main() -> int:
    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        print("\n[STOPPED] Ctrl+C received.")
        return 130
    except Exception as exc:
        print(f"\n[FATAL] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
