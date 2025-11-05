#!/usr/bin/env python3
"""Restore winners from backup JSON"""
import json
from database import DatabaseManager

db = DatabaseManager()

with open('winners_backup.json', 'r') as f:
    backup_winners = json.load(f)

print(f"Restoring {len(backup_winners)} winners from backup...\n")

restored = 0
skipped = 0

for winner in backup_winners:
    date = winner.get('drawing_date')
    username = winner.get('username')
    points = winner.get('points', 0)
    
    # Check if exists
    existing = db.get_winner_for_date(date)
    if existing:
        print(f"SKIP: {date}: @{username} (already exists: @{existing['username']})")
        skipped += 1
        continue
    
    # Restore
    success = db.record_daily_winner(
        username,
        points,
        date,
        total_eligible=winner.get('total_eligible'),
        random_seed=winner.get('random_seed'),
        selection_hash=winner.get('selection_hash')
    )
    
    if success:
        print(f"RESTORED: {date}: @{username} ({points} pts)")
        restored += 1
    else:
        print(f"FAILED: {date}: @{username}")
        skipped += 1

print(f"\nDone: Restored {restored}, Skipped {skipped}")

