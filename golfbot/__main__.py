"""CLI: python -m golfbot {login|search|book} [--config config.yaml]"""
import argparse

from . import book, login, teetimes
from .browser import session
from .config import load


def main() -> None:
    ap = argparse.ArgumentParser(prog="golfbot")
    ap.add_argument("command", choices=["login", "search", "book"])
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = load(args.config)

    if args.command == "login":
        login.run(cfg)
    elif args.command == "book":
        book.run(cfg)
    else:
        with session(cfg["browser"]["profile_dir"]) as (_ctx, page):
            slots = teetimes.fetch(page, cfg)
            hits = teetimes.matching(slots, cfg)
            print(f"\n{len(slots)} tee times on {cfg['booking']['date']}; {len(hits)} match your settings:")
            for s in hits:
                print("  ", teetimes.describe(s))


if __name__ == "__main__":
    main()
