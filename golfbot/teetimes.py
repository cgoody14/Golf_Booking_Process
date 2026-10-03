"""Find open tee times via Chronogolf's marketplace v2 API.

The request runs inside the logged-in Chrome tab (same cookies, same
Cloudflare clearance), exactly like the site's own tee sheet does.

    GET /marketplace/v2/teetimes?start_date=YYYY-MM-DD&course_ids=<uuid>&holes=9,18&page=N
    -> {"status": "open", "teetimes": [{uuid, start_time "7:00", max_player_size,
        course{bookable_holes}, default_price{green_fee}, frozen, ...}]}
"""
import json
from datetime import time

from .browser import BASE

MAX_PAGES = 10

_FETCH_JS = """async (url) => {
  const r = await fetch(url, {headers: {Accept: "application/json"}, credentials: "include"});
  return {status: r.status, body: await r.text()};
}"""


def _hhmm(s: str) -> time:
    h, m = s.split(":")[:2]
    return time(int(h), int(m))


def fetch(page, cfg) -> list[dict]:
    club, bk = cfg["club"], cfg["booking"]
    if not page.url.startswith(BASE):
        page.goto(BASE, wait_until="domcontentloaded")
    slots = []
    for n in range(1, MAX_PAGES + 1):
        url = (f"{BASE}/marketplace/v2/teetimes?start_date={bk['date']}"
               f"&course_ids={club['course_uuid']}&holes=9%2C18&page={n}")
        res = page.evaluate(_FETCH_JS, url)
        if res["status"] in (401, 403):
            raise RuntimeError(f"Tee time API returned {res['status']} — session expired. Run login again.")
        if res["status"] != 200:
            raise RuntimeError(f"Tee time API returned {res['status']}: {res['body'][:200]}")
        data = json.loads(res["body"])
        batch = data.get("teetimes") or []
        if data.get("status") not in (None, "open"):
            print(f"Tee sheet status: {data.get('status')}")
        slots.extend(batch)
        if not batch:
            break
        # Stop once a page adds nothing new (API may ignore page past the end).
        if n > 1 and batch[0]["uuid"] in {s["uuid"] for s in slots[:-len(batch)]}:
            slots = slots[:-len(batch)]
            break
    return slots


def matching(slots: list[dict], cfg) -> list[dict]:
    bk = cfg["booking"]
    lo, hi = _hhmm(bk["earliest"]), _hhmm(bk["latest"])
    out = []
    for s in slots:
        if s.get("frozen"):
            continue
        if (s.get("max_player_size") or 0) < bk["players"]:
            continue
        if bk["holes"] not in (s.get("course", {}).get("bookable_holes") or [bk["holes"]]):
            continue
        if lo <= _hhmm(s["start_time"]) <= hi:
            out.append(s)
    return sorted(out, key=lambda s: _hhmm(s["start_time"]))


def describe(s: dict) -> str:
    price = (s.get("default_price") or {}).get("green_fee")
    return f"{s['start_time']:>5}  up to {s['max_player_size']} players  ${price}"
