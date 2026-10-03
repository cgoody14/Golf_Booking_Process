"""Load config.yaml + credentials from .env."""
import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    raw: dict
    email: str
    password: str

    def __getitem__(self, key):
        return self.raw[key]


def load(path: str = "config.yaml") -> Config:
    load_dotenv()
    email = os.environ.get("CHRONOGOLF_EMAIL", "")
    password = os.environ.get("CHRONOGOLF_PASSWORD", "")
    if not email or not password:
        raise SystemExit("Set CHRONOGOLF_EMAIL and CHRONOGOLF_PASSWORD in .env")
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise SystemExit(f"{path} not found — copy config.example.yaml to {path}")
    return Config(raw=yaml.safe_load(cfg_path.read_text()), email=email, password=password)
