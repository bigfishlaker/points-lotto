"""
Run daily tracking every 24 hours
This will compare today's leaderboard with yesterday's to find users who gained points
"""
import schedule
import time
from datetime import datetime
from daily_points_tracker import DailyPointsTracker

def run_daily_report():
    """Run the daily points tracking report"""
    print("\n" + "=" * 80)
    print(f"Running daily points report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    tracker = DailyPointsTracker()
    
    try:
        # Fetch current snapshot
        current_users = tracker.scraper.get_leaderboard(limit=1000)
        tracker.save_snapshot(current_users)
        
        # Generate report
        report = tracker.create_daily_report(min_gain=1)
        print(report)
        
        print("✅ Daily report complete!")
        
    except Exception as e:
        print(f"❌ Error running daily report: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)

def main():
    """Main scheduler"""
    print("=" * 80)
    print("Daily Points Tracker - Starting scheduler")
    print("=" * 80)
    print("Schedule:")
    print("  • Daily report at 00:00 (midnight)")
    print("  • Daily report at 12:00 (noon)")
    print("\nPress Ctrl+C to stop")
    print("=" * 80)
    
    # Schedule reports
    schedule.every().day.at("00:00").do(run_daily_report)
    schedule.every().day.at("12:00").do(run_daily_report)
    
    # Also run now for testing
    print("\nRunning initial report...")
    run_daily_report()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutting down...")

