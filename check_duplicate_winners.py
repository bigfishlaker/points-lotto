#!/usr/bin/env python3
"""Check for duplicate winners by date"""
from database import DatabaseManager
import sqlite3

db = DatabaseManager()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

# Check for duplicates by drawing_date
cursor.execute('''
    SELECT drawing_date, COUNT(*) as count, GROUP_CONCAT(winner_username) as usernames
    FROM daily_winners
    GROUP BY drawing_date
    HAVING COUNT(*) > 1
    ORDER BY drawing_date DESC
''')

duplicates = cursor.fetchall()
print(f"\n{'='*60}")
print(f"DUPLICATE WINNERS CHECK")
print(f"{'='*60}\n")

if duplicates:
    print(f"WARNING: Found {len(duplicates)} dates with multiple winners:\n")
    for date, count, usernames in duplicates:
        print(f"  Date: {date}")
        print(f"  Count: {count}")
        print(f"  Usernames: {usernames}")
        print()
        
        # Get all entries for this date
        cursor.execute('''
            SELECT id, winner_username, winner_points, selected_at, drawing_period
            FROM daily_winners
            WHERE drawing_date = ?
            ORDER BY selected_at ASC
        ''', (date,))
        entries = cursor.fetchall()
        print(f"  All entries for {date}:")
        for entry in entries:
            print(f"    ID: {entry[0]}, Username: @{entry[1]}, Points: {entry[2]}, Selected: {entry[3]}, Period: {entry[4]}")
        print()
else:
    print("OK: No duplicate winners found by date\n")

# Show all winners
print(f"{'='*60}")
print(f"ALL WINNERS")
print(f"{'='*60}\n")

cursor.execute('''
    SELECT drawing_date, winner_username, winner_points, selected_at, id
    FROM daily_winners
    ORDER BY drawing_date ASC
''')

all_winners = cursor.fetchall()
print(f"Total winners: {len(all_winners)}\n")
for date, username, points, selected_at, wid in all_winners:
    print(f"  {date}: @{username} ({points} pts) - ID: {wid} - Selected: {selected_at}")

conn.close()


