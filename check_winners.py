#!/usr/bin/env python3
from database import DatabaseManager
from datetime import datetime
import sqlite3

db = DatabaseManager()

# Query all winners directly
conn = sqlite3.connect('lottery.db')
cursor = conn.cursor()
cursor.execute('SELECT winner_username, winner_points, drawing_date, selected_at FROM daily_winners ORDER BY selected_at DESC')
winners = cursor.fetchall()
conn.close()

print(f"Total winners in database: {len(winners)}")
print()
print("Recent winners:")
for w in winners[:5]:
    print(f"  {w[2]} - @{w[0]} ({w[1]} pts) - selected at {w[3]}")

print()
print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
