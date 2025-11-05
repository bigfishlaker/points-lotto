#!/usr/bin/env python3
"""Select winners for missing dates"""
import sys
import time
import random
import hashlib
from database import DatabaseManager

try:
    from pointsmarket_scraper import PointsMarketScraper
    POINTSMARKET_ENABLED = True
except ImportError:
    print("ERROR: PointsMarket scraper not available")
    sys.exit(1)

db = DatabaseManager()
points_scraper = PointsMarketScraper()

def select_winner_for_date(drawing_date: str):
    """Select winner for a specific date"""
    # CRITICAL: Check if winner already exists - NEVER reselect
    existing = db.get_winner_for_date(drawing_date)
    if existing:
        print(f"SKIP: Winner already exists for {drawing_date}: @{existing['username']} - skipping selection")
        return existing
    
    print(f"Fetching leaderboard for {drawing_date}...")
    users = None
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            users = points_scraper.get_leaderboard(limit=None)
            if users and len(users) > 0:
                break
        except Exception as e:
            print(f"Error fetching leaderboard (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return None
    
    if not users:
        print("No users returned from API")
        return None
    
    # Baseline: all users with 1+ point qualify
    qualified = [u for u in users if u.get('total_points', 0) >= 1]
    
    if not qualified:
        print("No eligible users after filtering")
        return None
    
    print(f"{len(qualified)} qualified users")
    
    # Select winner using date-specific seed
    seed_string = f"{drawing_date}00:05:00{len(qualified)}"
    random_seed = int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16) % 1000000
    random.seed(random_seed)
    winner = random.choice(qualified)
    random.seed()
    
    # Calculate lottery points
    all_winners = db.get_all_winners()
    lottery_points = len(all_winners) + 1
    
    selection_hash = hashlib.sha256(
        f"{drawing_date}{winner['username']}{lottery_points}{random_seed}".encode()
    ).hexdigest()[:16]
    
    # Save winner
    success = db.record_daily_winner(
        winner['username'],
        lottery_points,
        drawing_date,
        total_eligible=len(qualified),
        random_seed=random_seed,
        selection_hash=selection_hash
    )
    
    if success:
        print(f"SUCCESS: Winner for {drawing_date}: @{winner['username']} (lottery points: {lottery_points})")
        return {
            'username': winner['username'],
            'points': lottery_points,
            'drawing_date': drawing_date,
            'total_eligible': len(qualified),
            'random_seed': random_seed,
            'selection_hash': selection_hash
        }
    return None

print("\n" + "="*60)
print("SELECTING WINNERS FOR MISSING DATES")
print("="*60 + "\n")

# Dates to fill - update this list as needed
dates_to_fill = ['2025-11-04', '2025-11-05']

results = []

for date in dates_to_fill:
    print(f"\nProcessing {date}...")
    print("-" * 60)
    
    result = select_winner_for_date(date)
    if result:
        results.append(result)
    else:
        print(f"FAILED: Could not select winner for {date}")

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60 + "\n")

if results:
    for r in results:
        print(f"  {r.get('drawing_date', 'N/A')}: @{r.get('username', 'N/A')} ({r.get('points', 0)} pts)")
    
    # Update backup file
    try:
        import json
        all_winners = db.get_all_winners()
        backup_data = []
        for w in all_winners:
            backup_data.append({
                'username': w.get('username'),
                'points': w.get('points'),
                'drawing_date': w.get('drawing_date'),
                'total_eligible': w.get('total_eligible'),
                'random_seed': w.get('random_seed'),
                'selection_hash': w.get('selection_hash')
            })
        with open('winners_backup.json', 'w') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        print(f"\nBackup updated with {len(backup_data)} winners")
    except Exception as e:
        print(f"\nWarning: Could not update backup: {e}")
else:
    print("No winners were selected")

print("\n" + "="*60 + "\n")
