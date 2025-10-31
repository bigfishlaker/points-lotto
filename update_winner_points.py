#!/usr/bin/env python3
"""Update existing winners to have sequential points (1, 2, 3, ...)"""
from database import DatabaseManager
from datetime import datetime

db = DatabaseManager()

# Get all winners ordered chronologically
all_winners = db.get_all_winners()

if not all_winners:
    print("No winners found in database")
    exit(0)

print(f"Found {len(all_winners)} winners")
print("Updating points to be sequential...")

# Sort by date/selected_at to ensure chronological order
def sort_key(w):
    selected = w.get('selected_at') or ''
    drawing = w.get('drawing_date') or ''
    return selected if selected else drawing

sorted_winners = sorted(all_winners, key=sort_key)

# Update each winner with sequential points
conn = db.__dict__.get('db_path', 'lottery.db')
import sqlite3
db_conn = sqlite3.connect(conn)
cursor = db_conn.cursor()

for idx, winner in enumerate(sorted_winners, 1):
    username = winner.get('username')
    drawing_date = winner.get('drawing_date', '')
    points = idx  # Sequential points: 1, 2, 3, ...
    
    # Update the winner
    cursor.execute('''
        UPDATE daily_winners 
        SET winner_points = ?
        WHERE winner_username = ? AND drawing_date = ?
    ''', (points, username, drawing_date))
    
    print(f"  Updated @{username} ({drawing_date}): {points} point(s)")

db_conn.commit()
db_conn.close()

print(f"\n✅ Updated {len(sorted_winners)} winners with sequential points")
print("Next winner will get", len(sorted_winners) + 1, "points")

