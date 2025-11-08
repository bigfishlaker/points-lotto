"""
Health monitoring utility for the Points Lotto bot.

This script helps diagnose where the automation might be failing
to retrieve winners or update the Render-hosted site by running
three checks:

1. PointsMarket leaderboard fetch (via PointsMarketScraper)
2. Local database state (via DatabaseManager)
3. Render deployment health (via /api/current_winner and /api/all_winners)

Usage examples:
--------------
Run a single health check:
    python monitor_bot_health.py --render-url https://your-app.onrender.com

Run forever (every 10 minutes) writing to monitor.log:
    python monitor_bot_health.py --render-url https://your-app.onrender.com --loop --interval 600

Notes:
------
- The script writes structured logs to stdout and to monitor.log
  in the project root by default (override with --log-file).
- If PointsMarketScraper cannot be imported (e.g. missing deps),
  the script will record a warning but continue with DB / Render checks.
"""

import argparse
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import sys

import sqlite3

import requests

from database import DatabaseManager

try:
    from pointsmarket_scraper import PointsMarketScraper
    POINTSMARKET_AVAILABLE = True
except ImportError:  # pragma: no cover - handled gracefully at runtime
    PointsMarketScraper = None
    POINTSMARKET_AVAILABLE = False

# Ensure stdout/stderr can emit Unicode (PowerShell defaults to cp1252)
try:  # pragma: no cover - environment specific
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def setup_logging(log_file: Path, verbose: bool = False) -> None:
    """Configure logging to both stdout and a rotating log file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        handlers=handlers,
    )


def est_today() -> str:
    """Return today's date string in US Eastern time."""
    now_utc = datetime.now(timezone.utc)
    # Basic DST detection: Mar-Nov -> EDT (-4), otherwise EST (-5)
    is_dst = 3 <= now_utc.month < 11
    offset = -4 if is_dst else -5
    est_now = now_utc.astimezone(timezone(timedelta(hours=offset)))
    return est_now.date().isoformat()


def check_pointsmarket(scraper: Optional[PointsMarketScraper]) -> Dict[str, Any]:
    """Check PointsMarket leaderboard availability."""
    start = time.perf_counter()
    if scraper is None:
        return {
            "status": "skipped",
            "message": "PointsMarketScraper not available (import failed)",
            "duration_s": 0.0,
        }

    try:
        users = scraper.get_leaderboard(limit=None)
        duration = time.perf_counter() - start

        if not users:
            return {
                "status": "error",
                "message": "Leaderboard returned 0 users",
                "duration_s": duration,
            }

        qualified = [u for u in users if u.get("total_points", 0) >= 1]
        return {
            "status": "ok",
            "message": f"Fetched {len(users)} users ({len(qualified)} qualified)",
            "duration_s": duration,
            "sample_user": users[0] if users else None,
        }
    except Exception as exc:  # pragma: no cover - network/runtime specific
        duration = time.perf_counter() - start
        logging.exception("PointsMarket check failed")
        return {
            "status": "error",
            "message": f"Exception fetching leaderboard: {exc}",
            "duration_s": duration,
        }


def check_database(db: DatabaseManager) -> Dict[str, Any]:
    """Inspect local database for winner consistency."""
    start = time.perf_counter()
    today = est_today()

    try:
        today_winner = db.get_winner_for_date(today)
        current_winner = db.get_current_daily_winner()
        all_winners = db.get_all_winners()
        duration = time.perf_counter() - start

        status = "ok"
        issues = []

        if not today_winner:
            status = "warn"
            issues.append(f"No winner recorded for {today}")

        if not current_winner:
            status = "warn"
            issues.append("No winner flagged as current (is_current=1)")

        message = ", ".join(issues) if issues else "Database winners look healthy"
        return {
            "status": status,
            "message": message,
            "duration_s": duration,
            "today_winner": today_winner,
            "current_winner": current_winner,
            "total_winners": len(all_winners),
            "latest_winners": all_winners[-5:] if len(all_winners) >= 5 else all_winners,
        }
    except sqlite3.Error as exc:
        duration = time.perf_counter() - start
        logging.exception("Database check failed")
        return {
            "status": "error",
            "message": f"SQLite error: {exc}",
            "duration_s": duration,
        }


def check_render(render_url: Optional[str]) -> Dict[str, Any]:
    """Call Render deployment APIs to ensure winners are exposed."""
    if not render_url:
        return {
            "status": "skipped",
            "message": "No Render base URL supplied",
            "duration_s": 0.0,
        }

    start = time.perf_counter()
    base = render_url.rstrip("/")

    def _fetch(path: str) -> Dict[str, Any]:
        url = f"{base}{path}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()

    try:
        current_payload = _fetch("/api/current_winner")
        winners_payload = _fetch("/api/all_winners")
        duration = time.perf_counter() - start

        if not current_payload.get("success"):
            return {
                "status": "warn",
                "message": f"/api/current_winner returned success={current_payload.get('success')}",
                "duration_s": duration,
                "current_payload": current_payload,
                "winners_payload": winners_payload,
            }

        winners = winners_payload.get("winners", [])
        message = (
            f"Current winner: @{current_payload['winner'].get('username', 'unknown')}; "
            f"{len(winners)} total winners returned"
        )
        return {
            "status": "ok",
            "message": message,
            "duration_s": duration,
            "current_payload": current_payload,
            "winners_payload": winners_payload,
        }
    except requests.RequestException as exc:
        duration = time.perf_counter() - start
        logging.exception("Render health check failed")
        return {
            "status": "error",
            "message": f"HTTP error calling Render endpoints: {exc}",
            "duration_s": duration,
        }
    except Exception as exc:  # pragma: no cover - JSON, runtime
        duration = time.perf_counter() - start
        logging.exception("Unexpected error during Render check")
        return {
            "status": "error",
            "message": f"Unexpected error: {exc}",
            "duration_s": duration,
        }


def summarise(results: Dict[str, Dict[str, Any]]) -> str:
    """Generate a human-readable summary for logging."""
    lines = []
    for name, result in results.items():
        status = result.get("status", "unknown").upper()
        message = result.get("message", "")
        duration = result.get("duration_s", 0.0)
        lines.append(f"{name:<16} | {status:<7} | {message} ({duration:.2f}s)")
    return "\n".join(lines)


def run_checks(render_url: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Run all health checks and return aggregated results."""
    scraper = PointsMarketScraper() if POINTSMARKET_AVAILABLE else None
    db = DatabaseManager()

    results = {
        "pointsmarket": check_pointsmarket(scraper),
        "database": check_database(db),
        "render": check_render(render_url),
    }

    return results


def output_results(results: Dict[str, Dict[str, Any]], as_json: bool) -> None:
    """Log results and optionally print JSON to stdout."""
    summary = summarise(results)
    logging.info("Health check summary:\n%s", summary)

    worst_status = "ok"
    priority = {"error": 3, "warn": 2, "skipped": 1, "ok": 0}

    for result in results.values():
        status = result.get("status", "unknown").lower()
        if status not in priority:
            continue
        if priority[status] > priority.get(worst_status, -1):
            worst_status = status

    if worst_status in ("error", "warn"):
        logging.warning("Overall status: %s", worst_status.upper())
    else:
        logging.info("Overall status: OK")

    if as_json:
        print(json.dumps(results, indent=2, default=str))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor Points Lotto bot health.")
    parser.add_argument(
        "--render-url",
        dest="render_url",
        help="Base URL of the Render deployment (e.g. https://app.onrender.com)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=600,
        help="Interval in seconds between checks when --loop is set (default: 600s)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously at the specified interval",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("monitor.log"),
        help="File to append structured logs (default: monitor.log in project root)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print machine-readable JSON for each run",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_file, verbose=args.verbose)

    logging.info("Starting Points Lotto health monitor")
    logging.info(
        "Render URL: %s | Interval: %ss | Loop: %s | PointsMarket available: %s",
        args.render_url or "<not provided>",
        args.interval,
        args.loop,
        POINTSMARKET_AVAILABLE,
    )

    try:
        while True:
            results = run_checks(args.render_url)
            output_results(results, as_json=args.json)

            if not args.loop:
                break

            logging.info("Sleeping for %s seconds before next check...", args.interval)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logging.info("Health monitor interrupted by user.")


if __name__ == "__main__":
    main()

