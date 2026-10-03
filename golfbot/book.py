"""Book a tee time: wait for release, find a slot, click through checkout.

UI selectors are text-based best guesses — run with headless: false and
dry_run: true first, check screenshots/, and tweak as needed.
"""
import time as _time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import teetimes
from .browser import BASE, is_challenge_page, is_logged_in, open_context

SHOTS = Path("screenshots")


def _shot(page, name: str) -> None:
    SHOTS.mkdir(exist_ok=True)
    page.screenshot(path=str(SHOTS / f"{datetime.now():%H%M%S}-{name}.png"), full_page=True)


def _wait_for_release(cfg) -> None:
    rel = cfg["release"]
    if not rel.get("at"):
        return
    tz = ZoneInfo(rel.get("timezone", "America/New_York"))
    target = datetime.fromisoformat(rel["at"]).replace(tzinfo=tz)
    while (left := (target - datetime.now(tz)).total_seconds()) > 0:
        print(f"Waiting for release at {target:%Y-%m-%d %H:%M %Z} — {int(left)}s left", end="\r")
        _time.sleep(min(left, 30))
    print("\nRelease time reached.")


def _find_slot(ctx, cfg) -> dict | None:
    rel = cfg["release"]
    deadline = _time.monotonic() + rel.get("give_up_after_seconds", 300)
    while True:
        slots = teetimes.matching(teetimes.fetch(ctx, cfg), cfg)
        if slots:
            return slots[0]
        if _time.monotonic() > deadline:
            return None
        _time.sleep(rel.get("poll_seconds", 2))


def _checkout(page, slot: dict, cfg) -> None:
    club, bk = cfg["club"], cfg["booking"]
    start = slot.get("start_time") or slot.get("time")
    url = f"{BASE}/club/{club['slug']}/booking/?date={bk['date']}&nb_holes={bk['holes']}"
    page.goto(url, wait_until="domcontentloaded")
    if is_challenge_page(page):
        raise RuntimeError("Cloudflare challenge on booking page — re-run `login`.")
    page.wait_for_load_state("networkidle")
    _shot(page, "teesheet")

    # Tee times show as e.g. "7:30 AM" — match the slot's time.
    h, m = (int(x) for x in start.split(":")[:2])
    label = f"{(h % 12) or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"
    page.get_by_text(label, exact=True).first.click()

    # Player count — usually a button group or select.
    btn = page.get_by_role("button", name=str(bk["players"]), exact=True)
    if btn.count():
        btn.first.click()
    else:
        page.locator("select").first.select_option(str(bk["players"]))
    _shot(page, "players")

    page.get_by_role("button", name="Continue").first.click()
    page.wait_for_load_state("networkidle")
    _shot(page, "review")

    # Accept terms checkbox if present.
    terms = page.get_by_role("checkbox")
    for i in range(terms.count()):
        if not terms.nth(i).is_checked():
            terms.nth(i).check()

    if bk.get("dry_run", True):
        print(f"DRY RUN: stopped at review for {label}. See screenshots/.")
        return

    page.get_by_role("button", name="Confirm").first.click()
    page.wait_for_load_state("networkidle")
    _shot(page, "confirmed")
    print(f"Booked {label} on {bk['date']} for {bk['players']}.")


def run(cfg) -> None:
    b = cfg["browser"]
    with open_context(b["profile_dir"], headless=b.get("headless", False)) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if not is_logged_in(page):
            raise SystemExit("Not logged in (or Cloudflare blocked). Run: python -m golfbot login")

        _wait_for_release(cfg)
        slot = _find_slot(ctx, cfg)
        if not slot:
            raise SystemExit("No matching tee times found before give-up time.")
        print("Found slot:", slot.get("start_time") or slot.get("time"))
        try:
            _checkout(page, slot, cfg)
        except Exception:
            _shot(page, "error")
            raise
