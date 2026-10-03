"""Find open tee times via Chronogolf's marketplace JSON endpoint.

Requests go through the logged-in browser context (same cookies), which is
much faster than clicking through the UI at release time.

NOTE: this endpoint is undocumented. Verify the URL/params/fields in DevTools
(Network tab) for your club and adjust if they differ.
"""
from datetime import time

from .browser import BASE


def _hhmm(s: str) -> time:
    h, m = s.split(":")[:2]
    return time(int(h), int(m))


def fetch(ctx, cfg) -> list[dict]:
    club, bk = cfg["club"], cfg["booking"]
    params = {
        "date": bk["date"],
        "course_id": club["course_id"],
        "nb_holes": bk["holes"],
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    for aid in club.get("affiliation_type_ids") or []:
        query += f"&affiliation_type_ids[]={aid}"
    url = f"{BASE}/marketplace/clubs/{club['club_id']}/teetimes?{query}"

    resp = ctx.request.get(url, headers={"Accept": "application/json"})
    if resp.status == 403:
        raise RuntimeError("403 from tee time API — Cloudflare/session expired. Re-run `login`.")
    if not resp.ok:
        raise RuntimeError(f"Tee time API returned {resp.status}: {resp.text()[:200]}")
    data = resp.json()
    return data if isinstance(data, list) else data.get("teetimes", [])


def matching(slots: list[dict], cfg) -> list[dict]:
    bk = cfg["booking"]
    lo, hi = _hhmm(bk["earliest"]), _hhmm(bk["latest"])
    out = []
    for s in slots:
        start = s.get("start_time") or s.get("time")
        if not start or s.get("out_of_capacity"):
            continue
        # Field names vary; treat missing spot counts as "unknown, maybe ok".
        free = s.get("max_player_size") or s.get("available_spots") or bk["players"]
        if free < bk["players"]:
            continue
        if lo <= _hhmm(start) <= hi:
            out.append(s)
    return sorted(out, key=lambda s: s.get("start_time") or s.get("time"))
