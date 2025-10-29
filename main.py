#!/usr/bin/env python3
"""
Twitter Points Lottery System - Main Runner

This script starts the complete lottery system including:
- Twitter monitoring
- Lottery scheduler
- Web dashboard
"""

import threading
import time
from config import Config
# Twitter monitor is optional - import only if available
try:
    from twitter_monitor import TwitterMonitor
    TWITTER_MONITOR_AVAILABLE = True
except ImportError:
    TwitterMonitor = None
    TWITTER_MONITOR_AVAILABLE = False
from lottery_engine import LotteryEngine
from app import app

def main():
    """Main function to start all components"""
    config = Config()
    
    print("🎰 Starting Twitter Points Lottery System...")
    print(f"📱 Monitoring account: @{config.MAIN_TWITTER_ACCOUNT}")
    print(f"⏰ Lottery runs every {config.LOTTERY_INTERVAL_HOURS} hours")
    print("🌐 Web dashboard: http://localhost:5000")
    print("-" * 50)
    
    # Initialize components
    lottery_engine = LotteryEngine()
    
    # Start Twitter monitoring only if available
    if TWITTER_MONITOR_AVAILABLE and TwitterMonitor:
        print("🔍 Starting Twitter monitoring...")
        twitter_monitor = TwitterMonitor()
        monitor_thread = threading.Thread(
            target=twitter_monitor.monitor_account,
            args=(config.MAIN_TWITTER_ACCOUNT,),
            daemon=True
        )
        monitor_thread.start()
    else:
        print("⚠️  Twitter monitoring not available (tweepy not installed or Python 3.13+ compatibility issue)")
    
    # Start lottery scheduler in background thread
    print("🎲 Starting lottery scheduler...")
    lottery_thread = threading.Thread(
        target=lottery_engine.start_scheduler,
        daemon=True
    )
    lottery_thread.start()
    
    # Start web dashboard
    print("🚀 Starting web dashboard...")
    try:
        app.run(debug=config.DEBUG, host='0.0.0.0', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        lottery_engine.stop_scheduler()
        print("✅ Shutdown complete")

if __name__ == "__main__":
    main()


