"""One-time manual login.

Opens a normal Google Chrome window (NOT controlled by the bot) using the
bot's profile folder. You log in and pass the Cloudflare check yourself like
any regular visit; the session is saved in that profile and reused by later
bot runs.
"""
from .browser import BASE, is_logged_in, launch_chrome, open_context

LOGIN_URL = f"{BASE}/login"


def run(cfg) -> None:
    profile = cfg["browser"]["profile_dir"]
    proc = launch_chrome(profile, LOGIN_URL)

    print("\n>>> A Chrome window opened. In it:")
    print(">>>   1. Enter your email + password")
    print(">>>   2. Complete the Cloudflare check if shown")
    print(">>>   3. Click Log in and wait until you're on your account page")
    print(">>>   4. Quit that Chrome window with Cmd + Q")
    print(">>> Waiting for Chrome to close...\n")
    proc.wait()

    print("Checking the saved session...")
    with open_context(profile, headless=False) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if is_logged_in(page, verbose=True):
            print("Logged in. Session saved to", profile)
        else:
            raise SystemExit("Session not detected — see screenshots/session-check.png")
