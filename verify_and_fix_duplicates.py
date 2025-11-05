#!/usr/bin/env python3
"""Find and fix duplicate winners - ensure only one winner per date"""
from database import DatabaseManager
import sqlite3
from datetime import datetime

db = DatabaseManager()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

print("\n" + "="*60)
print("CHECKING FOR DUPLICATE WINNERS BY DATE")
print("="*60 + "\n")

# Find dates with multiple winners
cursor.execute('''
    SELECT drawing_date, COUNT(*) as count, GROUP_CONCAT(id) as ids, GROUP_CONCAT(winner_username) as usernames
    FROM daily_winners
    GROUP BY drawing_date
    HAVING COUNT(*) > 1
    ORDER BY drawing_date DESC
''')

duplicates = cursor.fetchall()

if duplicates:
    print(f"WARNING: Found {len(duplicates)} dates with multiple winners:\n")
    
    for date, count, ids_str, usernames_str in duplicates:
        print(f"Date: {date} ({count} winners)")
        print(f"  IDs: {ids_str}")
        print(f"  Usernames: {usernames_str}")
        
        # Get all entries for this date
        cursor.execute('''
            SELECT id, winner_username, winner_points, selected_at, drawing_period, is_current
            FROM daily_winners
            WHERE drawing_date = ?
            ORDER BY selected_at ASC
        ''', (date,))
        entries = cursor.fetchall()
        
        print(f"\n  All entries for {date}:")
        for entry in entries:
            print(f"    ID: {entry[0]}, Username: @{entry[1]}, Points: {entry[2]}")
            print(f"      Selected: {entry[3]}, Period: {entry[4]}, Current: {entry[5]}")
        
        # Keep the FIRST entry (earliest selected_at), remove others
        if len(entries) > 1:
            keep_id = entries[0][0]  # Keep the first one
            remove_ids = [e[0] for e in entries[1:]]  # Remove the rest
            
            print(f"\n  ACTION: Keeping ID {keep_id} (@{entries[0][1]}), removing IDs: {remove_ids}")
            
            # Ask for confirmation (but in automated mode, we'll just log)
            # For now, we'll just report - user can manually fix if needed
            print(f"  NOTE: Manual cleanup required - delete duplicate entries with IDs: {remove_ids}")
        
        print()
else:
    print("OK: No duplicate winners found by date\n")

# Verify UNIQUE constraint exists
print("="*60)
print("VERIFYING DATABASE CONSTRAINTS")
print("="*60 + "\n")

cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%daily_winners%'")
indexes = cursor.fetchall()
print("Indexes on daily_winners table:")
for idx in indexes:
    print(f"  - {idx[0]}")
    
    # Check if it's unique
    cursor.execute(f"PRAGMA index_info({idx[0]})")
    info = cursor.fetchall()
    for i in info:
        cursor.execute(f"PRAGMA index_list(daily_winners)")
        idx_list = cursor.fetchall()
        for idx_info in idx_list:
            if idx_info[1] == idx[0]:
                if idx_info[2] == 1:
                    print(f"    -> UNIQUE index")
                break

# Show all winners
print("\n" + "="*60)
print("ALL CURRENT WINNERS")
print("="*60 + "\n")

cursor.execute('''
    SELECT drawing_date, winner_username, winner_points, selected_at, id
    FROM daily_winners
    ORDER BY drawing_date ASC
''')

all_winners = cursor.fetchall()
print(f"Total winners: {len(all_winners)}\n")
for date, username, points, selected_at, wid in all_winners:
    print(f"  {date}: @{username} ({points} pts) - ID: {wid}")

conn.close()

print("\n" + "="*60)
print("RECOMMENDATION:")
print("="*60)
print("If duplicates were found, you should:")
print("1. Review the duplicates listed above")
print("2. Keep the FIRST entry (earliest selected_at) for each date")
print("3. Delete the duplicate entries manually")
print("4. Ensure UNIQUE constraint on drawing_date is in place")
print("="*60 + "\n")

