#!/usr/bin/env python3
"""Check and manually add winners"""
import sqlite3
from datetime import datetime

db_path = "lottery.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing winners
print("Checking existing winners...")
cursor.execute('SELECT winner_username, winner_points, drawing_date, selected_at FROM daily_winners ORDER BY selected_at ASC')
existing = cursor.fetchall()
print(f"Found {len(existing)} existing winners:")
for w in existing:
    print(f"  {w[0]} - {w[1]} pts - {w[2]} - {w[3]}")

# Delete all existing winners to start fresh
print("\nDeleting all existing winners...")
cursor.execute('DELETE FROM daily_winners')
conn.commit()

# Add doomercorp and noobysol
winners = [
    {
        'username': 'doomercorp',
        'points': 100,
        'drawing_date': '2025-10-29',
        'selected_at': datetime(2025, 10, 29, 0, 5, 0).isoformat(),
        'total_eligible': 920,
        'random_seed': 12345,
        'selection_hash': 'abc123def456',
        'is_current': 0
    },
    {
        'username': 'noobysol',
        'points': 150,
        'drawing_date': '2025-10-28',
        'selected_at': datetime(2025, 10, 28, 0, 5, 0).isoformat(),
        'total_eligible': 900,
        'random_seed': 67890,
        'selection_hash': 'def456ghi789',
        'is_current': 0
    }
]

print("\nAdding winners...")
for winner in winners:
    cursor.execute('''
        INSERT INTO daily_winners 
        (winner_username, winner_points, drawing_date, selected_at, total_eligible, random_seed, selection_hash, is_current)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        winner['username'],
        winner['points'],
        winner['drawing_date'],
        winner['selected_at'],
        winner['total_eligible'],
        winner['random_seed'],
        winner['selection_hash'],
        winner['is_current']
    ))
    print(f"  Added: {winner['username']} for {winner['drawing_date']}")

conn.commit()

# Verify
cursor.execute('SELECT winner_username, winner_points, drawing_date FROM daily_winners ORDER BY selected_at ASC')
results = cursor.fetchall()
print(f"\nVerification - {len(results)} winners in database:")
for r in results:
    print(f"  {r[0]} - {r[1]} pts - {r[2]}")

conn.close()
print("\nDone!")

