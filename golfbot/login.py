"""Log in once in the bot's Chrome window (you pass Cloudflare yourself)."""
from .browser import session


def run(cfg) -> None:
    with session(cfg["browser"]["profile_dir"]):
        input("Session saved. Press Enter to close Chrome... ")
