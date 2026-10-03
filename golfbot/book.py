"""Book a tee time: wait for release, find a slot, click through checkout.

UI selectors are text-based best guesses — run with
dry_run: true first, check screenshots/, and tweak as needed.
"""
import time as _time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import teetimes
from .browser import BASE, is_challenge_page, session

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


def _find_slot(page, cfg) -> dict | None:
    rel = cfg["release"]
    deadline = _time.monotonic() + rel.get("give_up_after_seconds", 300)
    while True:
        slots = teetimes.matching(teetimes.fetch(page, cfg), cfg)
        if slots:
            return slots[0]
        if _time.monotonic() > deadline:
            return None
        _time.sleep(rel.get("poll_seconds", 2))


def _click_first(page, names: list[str], timeout: int = 8000) -> str:
    """Click the first visible button/link matching any of the names."""
    for name in names:
        loc = page.get_by_role("button", name=name, exact=False)
        if loc.count() == 0:
            loc = page.get_by_role("link", name=name, exact=False)
        if loc.count():
            loc.first.click(timeout=timeout)
            return name
    raise RuntimeError(f"Couldn't find any of {names} on {page.url} — see screenshots/")


def _checkout(page, slot: dict, cfg) -> None:
    club, bk = cfg["club"], cfg["booking"]
    # Same URL the site uses when you click a tee time.
    url = f"{BASE}/club/{club['slug']}?date={bk['date']}&step=options&teetime={slot['uuid']}"
    page.goto(url, wait_until="domcontentloaded")
    if is_challenge_page(page):
        raise RuntimeError("Cloudflare challenge on booking page — run login again.")
    page.wait_for_timeout(3000)
    _shot(page, "1-options")

    # Holes + player count are usually button groups on the options step.
    for label in (f"{bk['holes']} holes", f"{bk['holes']} Holes", str(bk["holes"])):
        loc = page.get_by_text(label, exact=True)
        if loc.count():
            loc.first.click()
            break
    players = page.get_by_role("button", name=str(bk["players"]), exact=True)
    if players.count():
        players.first.click()
    _shot(page, "2-selected")

    _click_first(page, ["Continue", "Next", "Book", "Add to cart"])
    page.wait_for_timeout(3000)
    _shot(page, "3-review")

    if bk.get("dry_run", True):
        print(f"DRY RUN: stopped before confirming {slot['start_time']}. Check screenshots/.")
        return

    terms = page.get_by_role("checkbox")
    for i in range(terms.count()):
        if not terms.nth(i).is_checked():
            terms.nth(i).check()
    _click_first(page, ["Confirm", "Complete", "Book now", "Reserve"])
    page.wait_for_timeout(4000)
    _shot(page, "4-confirmed")
    print(f"Submitted booking for {slot['start_time']} on {bk['date']} — check screenshots/ and your email.")


def run(cfg) -> None:
    with session(cfg["browser"]["profile_dir"]) as (ctx, page):
        _wait_for_release(cfg)
        slot = _find_slot(page, cfg)
        if not slot:
            raise SystemExit("No matching tee times found before give-up time.")
        print("Found slot:", teetimes.describe(slot))
        try:
            _checkout(page, slot, cfg)
        except Exception:
            _shot(page, "error")
            raise
        input("Press Enter to close Chrome... ")
