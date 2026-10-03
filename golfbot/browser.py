"""Run a normal Google Chrome with the bot's own profile, then attach to it.

Chrome is started by us (not by Playwright) so it uses the real macOS
Keychain — that's what lets it read the session you saved during `login`.
Playwright then connects over Chrome's debugging port to drive it.
"""
import json
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import BrowserContext, sync_playwright

BASE = "https://www.chronogolf.com"
SHOTS = Path("screenshots")


def chrome_path() -> str:
    if sys.platform == "darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if sys.platform.startswith("win"):
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    return "google-chrome"


def _keep_session_cookies(profile_dir: str) -> None:
    """Set "Continue where you left off" so Chrome keeps login cookies after quitting.

    Chronogolf's login cookie expires "at end of session", so without this
    setting Chrome deletes it the moment you press Cmd + Q.
    """
    prefs_path = Path(profile_dir) / "Default" / "Preferences"
    prefs_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        prefs = json.loads(prefs_path.read_text())
    except (OSError, ValueError):
        prefs = {}
    if prefs.get("session", {}).get("restore_on_startup") == 1:
        return
    prefs.setdefault("session", {})["restore_on_startup"] = 1
    prefs_path.write_text(json.dumps(prefs))


def launch_chrome(profile_dir: str, *extra: str) -> subprocess.Popen:
    """Start Chrome with the bot profile. Chrome's log noise is hidden."""
    _keep_session_cookies(profile_dir)
    return subprocess.Popen(
        [
            chrome_path(),
            f"--user-data-dir={Path(profile_dir).resolve()}",
            "--no-first-run",
            "--no-default-browser-check",
            *extra,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 20) -> None:
    # Bypass any system proxy — this is a localhost check.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            opener.open(f"http://127.0.0.1:{port}/json/version", timeout=1)
            return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError("Chrome didn't start — is another bot Chrome window still open? Quit it and retry.")


@contextmanager
def open_context(profile_dir: str, headless: bool = False):
    """Start Chrome with a debugging port and attach Playwright to it."""
    port = _free_port()
    args = [f"--remote-debugging-port={port}", "--window-size=1280,900"]
    if headless:
        args.append("--headless=new")
    proc = launch_chrome(profile_dir, *args, BASE)
    try:
        _wait_for_port(port)
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            ctx: BrowserContext = browser.contexts[0]
            try:
                yield ctx
            finally:
                # Graceful quit so Chrome flushes cookies to disk.
                try:
                    browser.new_browser_cdp_session().send("Browser.close")
                except Exception:
                    pass
        proc.wait(timeout=15)
    finally:
        if proc.poll() is None:
            proc.terminate()


@contextmanager
def session(profile_dir: str):
    """Open one visible Chrome window and make sure it's logged in.

    If it isn't, you log in by hand in that same window (passing Cloudflare
    yourself) and press Enter in Terminal. The bot then keeps using that
    window, so nothing depends on the login surviving a restart.
    """
    with open_context(profile_dir) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for attempt in range(3):
            if is_logged_in(page, verbose=True):
                break
            print("\n>>> Not logged in. In the Chrome window that just opened:")
            print(">>>   1. Click Log In, enter your email + password")
            print(">>>   2. Let the Cloudflare box finish (green check)")
            print(">>>   3. Click Log in and wait for the page to load")
            print(">>>   DON'T close Chrome.")
            input(">>> Then come back here and press Enter... ")
        else:
            raise SystemExit("Still not logged in — see screenshots/session-check.png")
        print("Logged in.")
        yield ctx, page


def is_challenge_page(page) -> bool:
    """True if Cloudflare is showing a challenge instead of the site."""
    title = (page.title() or "").lower()
    return "just a moment" in title or page.locator("iframe[src*='challenges.cloudflare.com']").count() > 0


def is_logged_in(page, verbose: bool = False) -> bool:
    """Load the Chronogolf home page and look for signs of being logged out."""
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    challenged = is_challenge_page(page)
    login_link = page.get_by_role("link", name="Log In", exact=True).count() > 0
    login_form = page.locator("input[type=password]").count() > 0
    if verbose:
        SHOTS.mkdir(exist_ok=True)
        page.screenshot(path=str(SHOTS / "session-check.png"))
        print(f"  url={page.url}  cloudflare={challenged}  login_link={login_link}  login_form={login_form}")
    return not (challenged or login_link or login_form)
