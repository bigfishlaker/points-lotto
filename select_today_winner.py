#!/usr/bin/env python3
"""Manually select winner for today if missing - standalone script"""
import sys
import os
import time
import random
import hashlib
from datetime import datetime, timezone, timedelta

from database import DatabaseManager
from pointsmarket_scraper import PointsMarketScraper

def get_est_now():
    """Get current time in EST/EDT"""
    est = timezone(timedelta(hours=-5))
    edt = timezone(timedelta(hours=-4))
    now_utc = datetime.now(timezone.utc)
    is_dst = now_utc.month >= 3 and now_utc.month < 11
    return now_utc.astimezone(edt if is_dst else est)

def select_winner_for_date(drawing_date: str):
    """Select winner for a specific date"""
    db = DatabaseManager()
    points_scraper = PointsMarketScraper()
    
    # Check if winner already exists
    existing = db.get_winner_for_date(drawing_date)
    if existing:
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
        print(f"Winner for {drawing_date}: @{winner['username']} (lottery points: {lottery_points})")
        return {
            'username': winner['username'],
            'points': lottery_points,
            'drawing_date': drawing_date,
            'total_eligible': len(qualified),
            'random_seed': random_seed,
            'selection_hash': selection_hash
        }
    return None

def select_winner():
    """Select winner for today"""
    now_est = get_est_now()
    today_str = now_est.date().isoformat()
    return select_winner_for_date(today_str)

if __name__ == '__main__':
    db = DatabaseManager()
    now_est = get_est_now()
    today_str = now_est.date().isoformat()
    
    print(f"Current EST time: {now_est}")
    print(f"Today's date: {today_str}")
    print()
    
    # Check if winner already exists
    existing = db.get_winner_for_date(today_str)
    if existing:
        print(f"✅ Winner already exists for today:")
        print(f"   Username: @{existing['username']}")
        print(f"   Points: {existing['points']}")
        print(f"   Drawing Date: {existing['drawing_date']}")
        sys.exit(0)
    
    print(f"⚠️  No winner found for today ({today_str})")
    print("Attempting to select winner now...")
    print()
    
    result = select_winner()
    if result:
        print()
        print("✅ Successfully selected winner!")
        print(f"   Username: @{result['username']}")
        print(f"   Points: {result['points']}")
        print(f"   Drawing Date: {result['drawing_date']}")
        print(f"   Total Eligible: {result.get('total_eligible', 'N/A')}")
        print(f"   Random Seed: {result.get('random_seed', 'N/A')}")
        print(f"   Selection Hash: {result.get('selection_hash', 'N/A')}")
    else:
        print()
        print("❌ Failed to select winner")
        print("Possible reasons:")
        print("  - PointsMarket API is unavailable")
        print("  - No qualified users found")
        print("  - Database error")
        sys.exit(1)
