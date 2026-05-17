"""
speed_engine.py

Pure-Python speed test using Cloudflare's speed.cloudflare.com endpoints.
No external binary required — works on Mac, Linux, Windows, and Docker
with zero extra setup beyond `pip install requests`.

Methodology (mirrors what speed.cloudflare.com does in the browser):
  • Ping    — median latency of 5 lightweight HEAD requests
  • Download — streaming download of a 25 MB payload; bytes counted as they arrive
  • Upload   — POST of a 10 MB zero-byte payload; time measured end-to-end
"""

from __future__ import annotations

import statistics
import time
import logging
from dataclasses import dataclass

import requests

# ── Cloudflare speed-test endpoints ──────────────────────────────────────────
_BASE         = "https://speed.cloudflare.com"
_PING_URL     = f"{_BASE}/__down?bytes=1"          # tiny payload for latency
_DOWNLOAD_URL = f"{_BASE}/__down?bytes={{size}}"   # size injected at call time
_UPLOAD_URL   = f"{_BASE}/__up"

# How many bytes to transfer per test
_DOWNLOAD_SIZE = 25_000_000   # 25 MB  (enough to saturate most connections)
_UPLOAD_SIZE   = 10_000_000   # 10 MB

_TIMEOUT      = 60            # seconds before giving up on a single request
_CHUNK        = 65_536        # 64 KB streaming chunk size
_PING_ROUNDS  = 5             # number of pings to median-average


@dataclass
class SpeedResult:
    download_mbps: float
    upload_mbps: float
    ping_ms: float


# ── Internal helpers ──────────────────────────────────────────────────────────
def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "speedtest-monitor/1.0",
        "Accept-Encoding": "identity",   # disable gzip so byte counts are raw
    })
    return s


def _ping(session: requests.Session) -> float:
    """Return median RTT in milliseconds over _PING_ROUNDS requests."""
    latencies: list[float] = []
    for _ in range(_PING_ROUNDS):
        try:
            t0 = time.perf_counter()
            session.get(_PING_URL, timeout=10)
            latencies.append((time.perf_counter() - t0) * 1_000)
            time.sleep(0.05)    # small gap — don't hammer the endpoint
        except requests.RequestException:
            pass
    if not latencies:
        raise RuntimeError("All ping requests failed")
    return round(statistics.median(latencies), 2)


def _download(session: requests.Session) -> float:
    """Return download speed in Mbps."""
    url = _DOWNLOAD_URL.format(size=_DOWNLOAD_SIZE)
    t0 = time.perf_counter()
    received = 0
    with session.get(url, stream=True, timeout=_TIMEOUT) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_content(chunk_size=_CHUNK):
            received += len(chunk)
    elapsed = time.perf_counter() - t0
    if elapsed == 0:
        raise RuntimeError("Download completed instantly — something is wrong")
    mbps = (received * 8) / (elapsed * 1_000_000)
    return round(mbps, 2)


def _upload(session: requests.Session) -> float:
    """Return upload speed in Mbps."""
    payload = bytes(_UPLOAD_SIZE)    # zero-filled bytes
    t0 = time.perf_counter()
    resp = session.post(_UPLOAD_URL, data=payload, timeout=_TIMEOUT)
    resp.raise_for_status()
    elapsed = time.perf_counter() - t0
    if elapsed == 0:
        raise RuntimeError("Upload completed instantly — something is wrong")
    mbps = (_UPLOAD_SIZE * 8) / (elapsed * 1_000_000)
    return round(mbps, 2)


# ── Public API ────────────────────────────────────────────────────────────────
def run() -> SpeedResult:
    """
    Run a full speed test and return a SpeedResult.
    Raises RuntimeError (or requests.RequestException) on failure.
    """
    session = _session()

    logging.info("  ↪ measuring ping …")
    ping = _ping(session)
    logging.info(f"    ping: {ping} ms")

    logging.info("  ↪ measuring download …")
    download = _download(session)
    logging.info(f"    download: {download} Mbps")

    logging.info("  ↪ measuring upload …")
    upload = _upload(session)
    logging.info(f"    upload: {upload} Mbps")

    return SpeedResult(download_mbps=download, upload_mbps=upload, ping_ms=ping)


# ── Stand-alone smoke test ────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = run()
    print(f"\nDownload : {result.download_mbps} Mbps")
    print(f"Upload   : {result.upload_mbps} Mbps")
    print(f"Ping     : {result.ping_ms} ms")