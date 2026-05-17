"""
graph_generator.py
Reads all  speedtest_YYYY-MM-DD.csv  files from DATA_DIR and produces:
  • speed_history.png   — full timeline (all days combined)
  • speed_today.png     — today's data only
"""

from __future__ import annotations

import datetime
import glob
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe in Docker / headless

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd


# ── Palette ───────────────────────────────────────────────────────────────────
COLORS = {
    "download": "#2196F3",   # blue
    "upload":   "#4CAF50",   # green
    "ping":     "#FF5722",   # orange-red
}

STYLE = {
    "figure.facecolor":  "#0F1923",
    "axes.facecolor":    "#0F1923",
    "axes.edgecolor":    "#2E3D49",
    "axes.labelcolor":   "#ECEFF1",
    "xtick.color":       "#90A4AE",
    "ytick.color":       "#90A4AE",
    "grid.color":        "#1E2D38",
    "text.color":        "#ECEFF1",
    "lines.linewidth":   1.8,
}


# ── Internal helpers ──────────────────────────────────────────────────────────
def _load_all(data_dir: Path) -> pd.DataFrame | None:
    files = sorted(glob.glob(str(data_dir / "speedtest_*.csv")))
    if not files:
        logging.warning("graph_generator: no CSV files found.")
        return None

    frames: list[pd.DataFrame] = []
    for fpath in files:
        try:
            df = pd.read_csv(fpath, parse_dates=["timestamp"])
            frames.append(df)
        except Exception as exc:  # noqa: BLE001
            logging.warning(f"graph_generator: skipping {fpath} — {exc}")

    if not frames:
        return None

    combined = (
        pd.concat(frames, ignore_index=True)
        .sort_values("timestamp")
        .dropna(subset=["download_mbps", "upload_mbps", "ping_ms"])
    )
    return combined if not combined.empty else None


def _draw_chart(df: pd.DataFrame, title: str, output_path: Path) -> None:
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
        fig.suptitle(title, fontsize=15, fontweight="bold", y=0.98)

        specs = [
            ("download_mbps", "Download  (Mbps)", COLORS["download"]),
            ("upload_mbps",   "Upload  (Mbps)",   COLORS["upload"]),
            ("ping_ms",       "Ping  (ms)",        COLORS["ping"]),
        ]

        for ax, (col, ylabel, color) in zip(axes, specs):
            ts = df["timestamp"]
            vals = df[col]

            ax.plot(ts, vals, color=color, linewidth=1.8, zorder=3)
            ax.fill_between(ts, vals, alpha=0.15, color=color, zorder=2)
            ax.scatter(ts, vals, color=color, s=18, zorder=4, linewidths=0)

            # stats annotation
            mn, mx, avg = vals.min(), vals.max(), vals.mean()
            ax.axhline(avg, color=color, linewidth=0.8, linestyle="--", alpha=0.55)
            ax.annotate(
                f"avg {avg:.1f}  min {mn:.1f}  max {mx:.1f}",
                xy=(0.01, 0.93),
                xycoords="axes fraction",
                fontsize=8,
                color="#90A4AE",
                va="top",
            )

            ax.set_ylabel(ylabel, fontsize=9, labelpad=6)
            ax.xaxis.set_minor_locator(mticker.NullLocator())   # prevents MAXTICKS on shared date axis
            ax.grid(True, which="major", linewidth=0.6)
            ax.set_ylim(bottom=0)

        # x-axis formatting
        total_span = (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 3600
        if total_span <= 24:
            axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            axes[-1].xaxis.set_major_locator(mdates.HourLocator(interval=1))
        elif total_span <= 7 * 24:
            axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
            axes[-1].xaxis.set_major_locator(mdates.HourLocator(interval=6))
        else:
            axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
            axes[-1].xaxis.set_major_locator(mdates.DayLocator())

        plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)
        fig.tight_layout(rect=[0, 0, 1, 0.97])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logging.info(f"Graph saved → {output_path}")


# ── Public API ────────────────────────────────────────────────────────────────
def generate_graphs(data_dir: Path) -> None:
    """Generate combined history graph + today-only graph."""
    df = _load_all(data_dir)
    if df is None:
        return

    # Full history chart
    _draw_chart(df, "Network Speed — Full History", data_dir / "speed_history.png")

    # Today-only chart (if there is today data)
    today = datetime.date.today()
    today_df = df[df["timestamp"].dt.date == today]
    if not today_df.empty:
        _draw_chart(
            today_df,
            f"Network Speed — {today.strftime('%A, %B %d %Y')}",
            data_dir / "speed_today.png",
        )


# ── Stand-alone usage ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./data")
    generate_graphs(data_path)