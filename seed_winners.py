#!/usr/bin/env python3
"""
Seed initial winners into the database
"""
from database_clean import DatabaseManager
from datetime import datetime, timedelta

db = DatabaseManager()

# Seed @noobysol (yesterday)
db.record_winner(
    'noobysol',
    4,
    '2025-10-30',
    total_eligible=907,
    random_seed=12345,
    selection_hash='abc123def456'
)

# Seed @doomercorp (today) - set as current
db.record_winner(
    'doomercorp',
    5,
    '2025-10-31',
    total_eligible=920,
    random_seed=32920,
    selection_hash='83696afc7c711bd0'
)

print("Winners seeded successfully!")
print("   @noobysol - 2025-10-30")
print("   @doomercorp - 2025-10-31 (current)")

