#!/usr/bin/env python3
"""Export all winners to JSON backup file"""
import json
from database import DatabaseManager

db = DatabaseManager()
winners = db.get_all_winners()

# Convert to JSON-serializable format
winners_data = []
for winner in winners:
    winners_data.append({
        'username': winner['username'],
        'points': winner['points'],
        'drawing_date': winner['drawing_date'],
        'total_eligible': winner.get('total_eligible'),
        'random_seed': winner.get('random_seed'),
        'selection_hash': winner.get('selection_hash')
    })

# Write to backup file
with open('winners_backup.json', 'w') as f:
    json.dump(winners_data, f, indent=2, ensure_ascii=False)

print(f"✅ Exported {len(winners_data)} winners to winners_backup.json")
for w in winners_data:
    print(f"  - @{w['username']} ({w['points']} pts) - {w['drawing_date']}")

