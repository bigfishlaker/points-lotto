#!/usr/bin/env python3
"""
Initialize winner on startup - run once on first deployment
"""
from database import DatabaseManager
from datetime import date
import os

def init_winner():
    """Initialize the winner if it doesn't exist"""
    db = DatabaseManager()
    
    today = date.today().isoformat()
    
    # Check if winner already exists
    existing = db.get_winner_for_date(today)
    if existing:
        print(f"✅ Winner already exists: @{existing['username']}")
        return False
    
    # Insert winner
    success = db.record_daily_winner(
        username="noobysol",
        points=4,
        drawing_date=today,
        total_eligible=907,
        random_seed=12345,
        selection_hash="abc123def456",
        snapshot_date="2025-10-30"
    )
    
    if success:
        print(f"✅ Winner initialized: @noobysol")
        return True
    else:
        print("❌ Failed to initialize winner")
        return False

if __name__ == '__main__':
    # Only run if INIT_WINNER env var is set
    if os.getenv('INIT_WINNER') == 'true':
        init_winner()

