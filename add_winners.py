#!/usr/bin/env python3
"""Add initial winners to the database"""
import sqlite3
from datetime import datetime

db_path = "lottery.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Add doomercorp and noobysol as winners
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

for winner in winners:
    # Check if winner already exists
    cursor.execute('SELECT id FROM daily_winners WHERE winner_username = ? AND drawing_date = ?',
                   (winner['username'], winner['drawing_date']))
    if cursor.fetchone():
        print(f"Winner {winner['username']} for {winner['drawing_date']} already exists, skipping...")
        continue
    
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
    print(f"Added winner: {winner['username']} for {winner['drawing_date']}")

conn.commit()
conn.close()
print("Done!")

