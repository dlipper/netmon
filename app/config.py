import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "netmon.db"
SPEEDTEST_BIN = BASE_DIR / "bin" / "speedtest-ookla"

# Monitoring targets (Cloudflare and Google DNS)
PING_TARGETS = ["1.1.1.1", "8.8.8.8"]
PING_INTERVAL_SECONDS = 30

# Web server settings
HOST = "0.0.0.0"
PORT = 80
