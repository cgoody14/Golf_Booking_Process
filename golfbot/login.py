"""One-time manual login.

Opens a normal Google Chrome window (NOT controlled by the bot) using the
bot's profile folder. You log in and pass the Cloudflare check yourself like
any regular visit; the session cookies are saved in that profile and reused
by later bot runs.
"""
import subprocess
import sys
from pathlib import Path

from .browser import BASE, is_logged_in, open_context

LOGIN_URL = f"{BASE}/login"
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def _chrome_path() -> str:
    if sys.platform == "darwin":
        return MAC_CHROME
    if sys.platform.startswith("win"):
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    return "google-chrome"


def run(cfg) -> None:
    profile = str(Path(cfg["browser"]["profile_dir"]).resolve())
    proc = subprocess.Popen([
        _chrome_path(),
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        LOGIN_URL,
    ])

    print("\n>>> A Chrome window opened. In it:")
    print(">>>   1. Enter your email + password")
    print(">>>   2. Complete the Cloudflare check if shown")
    print(">>>   3. Click Log in and wait until you're on your account page")
    print(">>>   4. Quit that Chrome window with Cmd + Q")
    print(">>> Waiting for Chrome to close...\n")
    proc.wait()

    print("Checking the saved session...")
    with open_context(cfg["browser"]["profile_dir"], headless=False) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if is_logged_in(page):
            print("Logged in. Session saved to", cfg["browser"]["profile_dir"])
        else:
            raise SystemExit("Session not detected — run login again and make sure you finish logging in.")
