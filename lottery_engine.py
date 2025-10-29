import random
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import DatabaseManager
from config import Config

class LotteryEngine:
    def __init__(self):
        self.db = DatabaseManager()
        self.config = Config()
        self.is_running = False
    
    def run_lottery(self) -> Dict:
        """Run the lottery for all active keywords"""
        print(f"Running lottery at {datetime.now()}")
        
        active_keywords = self.db.get_active_keywords()
        results = []
        
        for keyword in active_keywords:
            keyword_id = keyword['id']
            keyword_text = keyword['keyword']
            
            # Get eligible users for this keyword
            eligible_users = self.db.get_eligible_users_for_lottery(keyword_id)
            
            if not eligible_users:
                print(f"No eligible users for keyword: {keyword_text}")
                continue
            
            # Select winner
            winner = self._select_winner(eligible_users)
            
            if winner:
                # Calculate points to award (based on engagement count)
                points_won = self._calculate_points(winner['engagement_count'])
                
                # Record winner
                success = self.db.record_lottery_winner(keyword_id, winner['id'], points_won)
                
                if success:
                    result = {
                        'keyword': keyword_text,
                        'winner': {
                            'username': winner['username'],
                            'display_name': winner['display_name'],
                            'twitter_id': winner['twitter_id']
                        },
                        'points_won': points_won,
                        'total_participants': len(eligible_users),
                        'timestamp': datetime.now()
                    }
                    results.append(result)
                    
                    print(f"Winner for '{keyword_text}': @{winner['username']} ({points_won} points)")
                else:
                    print(f"Failed to record winner for keyword: {keyword_text}")
            else:
                print(f"No winner selected for keyword: {keyword_text}")
        
        return {
            'lottery_run_at': datetime.now(),
            'total_keywords': len(active_keywords),
            'winners': results
        }
    
    def _select_winner(self, eligible_users: List[Dict]) -> Optional[Dict]:
        """Select a winner from eligible users using weighted random selection"""
        if not eligible_users:
            return None
        
        # Weight users by their engagement count (more engagement = higher chance)
        weights = []
        for user in eligible_users:
            # Base weight of 1 + engagement count
            weight = 1 + user['engagement_count']
            weights.append(weight)
        
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(eligible_users)
        
        random_value = random.uniform(0, total_weight)
        current_weight = 0
        
        for i, weight in enumerate(weights):
            current_weight += weight
            if random_value <= current_weight:
                return eligible_users[i]
        
        # Fallback to random selection
        return random.choice(eligible_users)
    
    def _calculate_points(self, engagement_count: int) -> int:
        """Calculate points to award based on engagement count"""
        base_points = self.config.POINTS_PER_ENGAGEMENT
        # Award more points for higher engagement
        multiplier = min(engagement_count, 5)  # Cap at 5x multiplier
        return base_points * multiplier
    
    def start_scheduler(self):
        """Start the lottery scheduler"""
        print("Starting lottery scheduler...")
        
        # Schedule lottery to run every 6 hours
        schedule.every(self.config.LOTTERY_INTERVAL_HOURS).hours.do(self.run_lottery)
        
        # Also run lottery at specific times (optional)
        schedule.every().day.at("12:00").do(self.run_lottery)  # Noon
        schedule.every().day.at("18:00").do(self.run_lottery)  # 6 PM
        schedule.every().day.at("00:00").do(self.run_lottery)  # Midnight
        schedule.every().day.at("06:00").do(self.run_lottery)  # 6 AM
        
        self.is_running = True
        
        # Run initial lottery if there are active keywords
        active_keywords = self.db.get_active_keywords()
        if active_keywords:
            print("Running initial lottery...")
            self.run_lottery()
        
        # Keep scheduler running
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop_scheduler(self):
        """Stop the lottery scheduler"""
        self.is_running = False
        print("Lottery scheduler stopped")
    
    def get_lottery_stats(self) -> Dict:
        """Get lottery statistics"""
        history = self.db.get_lottery_history(limit=50)
        
        total_winners = len(history)
        total_points_awarded = sum(result['points_won'] for result in history)
        
        # Get unique winners
        unique_winners = set(result['winner_username'] for result in history)
        
        # Get most active keywords
        keyword_counts = {}
        for result in history:
            keyword = result['keyword']
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        most_active_keyword = max(keyword_counts.items(), key=lambda x: x[1]) if keyword_counts else None
        
        return {
            'total_lotteries_run': total_winners,
            'total_points_awarded': total_points_awarded,
            'unique_winners': len(unique_winners),
            'most_active_keyword': most_active_keyword,
            'recent_winners': history[:5]  # Last 5 winners
        }
    
    def manual_lottery_run(self) -> Dict:
        """Manually trigger a lottery run"""
        print("Manual lottery run triggered")
        return self.run_lottery()
    
    def get_next_lottery_time(self) -> Optional[datetime]:
        """Get the next scheduled lottery time"""
        jobs = schedule.get_jobs()
        if jobs:
            # Get the next job time
            next_run = min(job.next_run for job in jobs)
            return next_run
        return None


