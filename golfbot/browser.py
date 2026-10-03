"""Persistent browser profile so the Cloudflare check + login only happen by hand once."""
from contextlib import contextmanager

from playwright.sync_api import BrowserContext, sync_playwright

BASE = "https://www.chronogolf.com"


@contextmanager
def open_context(profile_dir: str, headless: bool):
    with sync_playwright() as p:
        ctx: BrowserContext = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
        )
        try:
            yield ctx
        finally:
            ctx.close()


def is_challenge_page(page) -> bool:
    """True if Cloudflare is showing a challenge instead of the site."""
    title = (page.title() or "").lower()
    return "just a moment" in title or page.locator("iframe[src*='challenges.cloudflare.com']").count() > 0


def is_logged_in(page) -> bool:
    page.goto(f"{BASE}/dashboard", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    return "/login" not in page.url and not is_challenge_page(page)
