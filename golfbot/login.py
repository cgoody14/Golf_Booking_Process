"""One-time interactive login.

Opens a real (headed) browser, pre-fills your credentials, and waits for YOU
to complete the Cloudflare check and submit. Cookies are saved in the
persistent profile so later booking runs reuse the session.
"""
from .browser import BASE, is_logged_in, open_context

LOGIN_URL = f"{BASE}/login"


def run(cfg) -> None:
    b = cfg["browser"]
    with open_context(b["profile_dir"], headless=False) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if is_logged_in(page):
            print("Already logged in — session is still valid.")
            return

        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        try:
            page.get_by_label("Email", exact=False).first.fill(cfg.email, timeout=10_000)
            page.get_by_label("Password", exact=False).first.fill(cfg.password, timeout=10_000)
            print("Credentials filled.")
        except Exception:
            print("Couldn't auto-fill the form — type your email/password in the browser.")

        print("\n>>> In the browser window: complete the Cloudflare check, then click Log in.")
        print(">>> Waiting up to 5 minutes...\n")
        page.wait_for_url(lambda url: "/login" not in url, timeout=300_000)
        page.wait_for_timeout(2000)

        if is_logged_in(page):
            print("Logged in. Session saved to", b["profile_dir"])
        else:
            raise SystemExit("Login didn't stick — try again.")
