#!/usr/bin/env python3
"""
Script to manually force winner selection for today (EST date)
Use this if the automatic scheduler missed a day
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import select_daily_winner_with_fresh_data, db
from datetime import datetime, timezone, timedelta

def force_select_winner():
    """Force select a winner for today's EST date"""
    
    # Get current EST date
    est = timezone(timedelta(hours=-5))
    edt = timezone(timedelta(hours=-4))
    now_utc = datetime.now(timezone.utc)
    is_dst = now_utc.month >= 3 and now_utc.month < 11
    est_offset = edt if is_dst else est
    now_est = now_utc.astimezone(est_offset)
    today_str = now_est.date().isoformat()
    
    print(f"🎯 Force selecting winner for EST date: {today_str}")
    print(f"   Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   Current EST time: {now_est.strftime('%Y-%m-%d %H:%M:%S EST')}")
    print("-" * 60)
    
    # Check if winner already exists
    existing = db.get_winner_for_date(today_str)
    if existing:
        print(f"✅ Winner already exists for {today_str}:")
        print(f"   Username: @{existing['username']}")
        print(f"   Points: {existing['points']}")
        print(f"   Drawing Date: {existing['drawing_date']}")
        print(f"   Selected At: {existing.get('selected_at', 'N/A')}")
        return existing
    
    print("📊 No winner found for today. Selecting winner now...")
    print("-" * 60)
    
    # Select winner
    result = select_daily_winner_with_fresh_data()
    
    if result:
        print("=" * 60)
        print("🏆 WINNER SELECTED SUCCESSFULLY!")
        print("=" * 60)
        print(f"   Username: @{result['username']}")
        print(f"   Points: {result['points']}")
        print(f"   Drawing Date: {result['drawing_date']}")
        print(f"   Total Eligible: {result.get('total_eligible', 'N/A')}")
        print(f"   Random Seed: {result.get('random_seed', 'N/A')}")
        print(f"   Selection Hash: {result.get('selection_hash', 'N/A')}")
        print("=" * 60)
        return result
    else:
        print("=" * 60)
        print("❌ FAILED TO SELECT WINNER")
        print("=" * 60)
        print("Possible reasons:")
        print("  - No eligible users found")
        print("  - PointsMarket integration not available")
        print("  - Error fetching data")
        print("=" * 60)
        return None

if __name__ == '__main__':
    try:
        result = force_select_winner()
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

