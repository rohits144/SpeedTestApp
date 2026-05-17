"""
speedtest_monitor.py

Runs a network speed test every INTERVAL_MINUTES minutes.
Uses speed_engine.py (Cloudflare endpoints, pure Python) — no external
binary or special pip package needed beyond `requests`.
"""

import csv
import datetime
import logging
import os
import time
from pathlib import Path

import schedule

import speed_engine
from graph_generator import generate_graphs

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR         = Path(os.environ.get("DATA_DIR", "./data"))
INTERVAL_MINUTES = int(os.environ.get("INTERVAL_MINUTES", 5))


# ── Logging ───────────────────────────────────────────────────────────────────
def setup_logging() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(DATA_DIR / "speedtest.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


# ── CSV helpers ───────────────────────────────────────────────────────────────
HEADERS = ["timestamp", "download_mbps", "upload_mbps", "ping_ms"]


def get_csv_path() -> Path:
    return DATA_DIR / f"speedtest_{datetime.date.today()}.csv"


def ensure_header(path: Path) -> None:
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(HEADERS)


# ── Main job ──────────────────────────────────────────────────────────────────
def run_speedtest() -> None:
    logging.info("Speed test starting …")
    try:
        result = speed_engine.run()

        csv_path = get_csv_path()
        ensure_header(csv_path)

        timestamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(csv_path, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow([
                timestamp,
                result.download_mbps,
                result.upload_mbps,
                result.ping_ms,
            ])

        logging.info(
            f"Done — Download: {result.download_mbps} Mbps | "
            f"Upload: {result.upload_mbps} Mbps | "
            f"Ping: {result.ping_ms} ms"
        )

        generate_graphs(DATA_DIR)

    except Exception as exc:          # noqa: BLE001
        logging.exception(f"Speed test failed: {exc}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    setup_logging()
    logging.info(
        f"Speed-test monitor started  "
        f"(interval: {INTERVAL_MINUTES} min | data dir: {DATA_DIR})"
    )

    run_speedtest()   # run once immediately on launch

    schedule.every(INTERVAL_MINUTES).minutes.do(run_speedtest)
    while True:
        schedule.run_pending()
        time.sleep(10)