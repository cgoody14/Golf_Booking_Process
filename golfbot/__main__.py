"""CLI: python -m golfbot {login|search|book} [--config config.yaml]"""
import argparse
import json

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
        with session(cfg["browser"]["profile_dir"]) as (ctx, _page):
            slots = teetimes.fetch(ctx, cfg)
            print(f"{len(slots)} total slots; matching your window:")
            print(json.dumps(teetimes.matching(slots, cfg), indent=2))


if __name__ == "__main__":
    main()
