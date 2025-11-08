#!/usr/bin/env python3
"""
Sync the local daily_winners table with a JSON snapshot (e.g. from Render).

Usage:
    python sync_winners_from_snapshot.py --snapshot render_winners_snapshot_2025-11-08_05-36-56.json

If --snapshot is omitted the script will pick the most recent file that matches
`render_winners_snapshot_*.json` in the current directory.
"""

import argparse
import glob
import json
import os
import sqlite3
from datetime import datetime

from database import DatabaseManager


def find_latest_snapshot() -> str:
    candidates = sorted(glob.glob("render_winners_snapshot_*.json"))
    return candidates[-1] if candidates else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync daily_winners from snapshot JSON.")
    parser.add_argument(
        "--snapshot",
        type=str,
        help="Path to snapshot JSON (defaults to latest render_winners_snapshot_*.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without modifying the database.",
    )
    return parser.parse_args()


def load_snapshot(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    winners = payload.get("winners")
    if not isinstance(winners, list):
        raise ValueError(f"Snapshot {path} does not contain a 'winners' list.")

    # Sort chronologically by drawing_date then selected_at
    def _sort_key(item: dict) -> tuple:
        date_str = item.get("drawing_date") or ""
        selected_at = item.get("selected_at") or ""
        return (date_str, selected_at)

    winners.sort(key=_sort_key)
    return winners


def sync_winners(snapshot_path: str, dry_run: bool = False) -> None:
    winners = load_snapshot(snapshot_path)
    if not winners:
        raise ValueError("Snapshot is empty; aborting.")

    db = DatabaseManager()

    conn = sqlite3.connect(db.db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    print(f"Loaded {len(winners)} winners from {snapshot_path}")

    if dry_run:
        print("Dry run: no database changes will be applied.")
        for winner in winners:
            print(
                f"Would insert {winner['drawing_date']}: @{winner['username']} "
                f"({winner['points']} pts)"
            )
        conn.close()
        return

    # Capture existing winners for audit before changes
    existing = db.get_all_winners()
    backup_path = f"pre_sync_backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    with open(backup_path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=2, ensure_ascii=False)
    print(f"Backed up current daily_winners to {backup_path}")

    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor.execute("DELETE FROM daily_winners")

        for winner in winners:
            cursor.execute(
                """
                INSERT INTO daily_winners (
                    winner_username,
                    winner_points,
                    drawing_date,
                    drawing_period,
                    selected_at,
                    is_current,
                    total_eligible,
                    random_seed,
                    selection_hash
                )
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    winner.get("username"),
                    winner.get("points"),
                    winner.get("drawing_date"),
                    winner.get("drawing_date"),  # use date as period key
                    winner.get("selected_at"),
                    winner.get("total_eligible"),
                    winner.get("random_seed"),
                    winner.get("selection_hash"),
                ),
            )
            print(
                f"Inserted {winner.get('drawing_date')}: "
                f"@{winner.get('username')} ({winner.get('points')} pts)"
            )

        # Flag the most recent winner as current
        cursor.execute("UPDATE daily_winners SET is_current = 0")
        cursor.execute(
            """
            UPDATE daily_winners
            SET is_current = 1
            WHERE id = (
                SELECT id
                FROM daily_winners
                ORDER BY
                    COALESCE(selected_at, drawing_date) DESC,
                    drawing_date DESC,
                    id DESC
                LIMIT 1
            )
            """
        )

        conn.commit()
        print("Database sync complete.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Refresh backup artefacts
    db.refresh_backup_file()
    print("Regenerated winners_backup.json and daily snapshots.")


def main() -> None:
    args = parse_args()
    snapshot_path = args.snapshot or find_latest_snapshot()

    if not snapshot_path:
        raise SystemExit(
            "No snapshot file provided and none found via render_winners_snapshot_*.json"
        )

    if not os.path.exists(snapshot_path):
        raise SystemExit(f"Snapshot file not found: {snapshot_path}")

    sync_winners(snapshot_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

