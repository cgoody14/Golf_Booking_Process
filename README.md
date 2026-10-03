# Golf Booking Process

Automated tee time booking, starting with [Chronogolf](https://www.chronogolf.com/).

## How it works
1. **`login`** — opens a real browser, fills your credentials, and **you** finish the Cloudflare check and click Log in. The session is saved in `.browser-profile/`.
2. **`search`** — reuses that session to pull tee times for your date/window from Chronogolf's JSON endpoint.
3. **`book`** — optionally waits for a release time, polls for a matching slot, then clicks through checkout. `dry_run: true` stops on the review page.

Nothing here solves or bypasses the Cloudflare check — when the session expires, re-run `login`.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Uses your installed Google Chrome — no `playwright install` needed
cp .env.example .env              # add your email/password
cp config.example.yaml config.yaml  # set club, date, time window
```

## Find your club IDs
1. Open your club's Chronogolf page in Chrome → right-click → **Inspect** → **Network** tab.
2. Pick a date on the tee sheet.
3. Filter for `teetimes` — the request URL has `clubs/<club_id>/` and `course_id=<id>`.
4. Put those plus the `slug` from the page URL into `config.yaml`.

## Run
```bash
python -m golfbot login    # once (and whenever the session expires)
python -m golfbot search   # check what's available
python -m golfbot book     # dry run by default
```
Screenshots of each step land in `screenshots/`.

## Status
The API endpoint and checkout selectors are best guesses — Chronogolf wasn't reachable from the build environment, so the first runs need to be verified with `headless: false` + `dry_run: true`.
