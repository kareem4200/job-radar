import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"


@dataclass
class CompanyConfig:
    name: str
    ats: str  # "greenhouse" | "personio" | "lever"
    identifier: str  # board token / personio subdomain / lever slug
    region: Optional[str] = None
    enabled: bool = True


def load_companies() -> list[CompanyConfig]:
    path = CONFIG_DIR / "companies.yaml"
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    companies = []
    for entry in raw.get("companies", []):
        companies.append(
            CompanyConfig(
                name=entry["name"],
                ats=entry["ats"],
                identifier=entry["identifier"],
                region=entry.get("region"),
                enabled=entry.get("enabled", True),
            )
        )
    return companies


def load_keywords() -> dict:
    path = CONFIG_DIR / "keywords.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DB_PATH = os.getenv("JOB_RADAR_DB_PATH", str(DATA_DIR / "seen_jobs.sqlite3"))

# Minimum score required to send a Telegram alert.
# THE SINGLE SOURCE OF TRUTH - healthcheck.py reads this too, so its ALERT
# column always matches what actually fires. Override per-environment with
# JOB_RADAR_MIN_SCORE (e.g. =0 for one run to prove the Telegram path).
#
# Why 20: swept against 21 real postings from a live run. 20 kept 10/10 good
# roles with 0/11 bad ones. 25 dropped "Field Application Engineer Robotics"
# and DLR's "Ingenieur/in - Konzeption und Entwicklung von Robotik"; 15 let
# noise through. Re-sweep if you materially change keywords.yaml.
MIN_SCORE_TO_ALERT = int(os.getenv("JOB_RADAR_MIN_SCORE", "20"))
