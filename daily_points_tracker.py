"""
Daily Points Tracker - Track users who gained points in the last 24 hours
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pointsmarket_scraper import PointsMarketScraper

DAILY_DATA_DIR = "daily_snapshots"

class DailyPointsTracker:
    """Track and compare daily points for users"""
    
    def __init__(self):
        self.scraper = PointsMarketScraper()
        os.makedirs(DAILY_DATA_DIR, exist_ok=True)
    
    def get_snapshot_filename(self, date_str: str = None) -> str:
        """Get filename for today's snapshot"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        return os.path.join(DAILY_DATA_DIR, f"snapshot_{date_str}.json")
    
    def save_snapshot(self, users: List[Dict]) -> str:
        """Save today's snapshot and return filename"""
        today_str = datetime.now().strftime('%Y-%m-%d')
        filename = self.get_snapshot_filename(today_str)
        
        snapshot = {
            'date': today_str,
            'timestamp': datetime.now().isoformat(),
            'total_users': len(users),
            'users': {user['username']: user for user in users}
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2)
        
        return filename
    
    def load_snapshot(self, date_str: str = None) -> Optional[Dict]:
        """Load a snapshot for a specific date"""
        filename = self.get_snapshot_filename(date_str)
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_daily_gains(self, min_gain: int = 1) -> Dict:
        """Compare today's data with yesterday's to find users who gained points"""
        today_str = datetime.now().strftime('%Y-%m-%d')
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Get today's snapshot
        today_snapshot = self.load_snapshot(today_str)
        if not today_snapshot:
            print(f"No snapshot for today ({today_str}). Fetching current data...")
            current_users = self.scraper.get_leaderboard(limit=1000)
            self.save_snapshot(current_users)
            today_snapshot = self.load_snapshot(today_str)
        
        # Get yesterday's snapshot
        yesterday_snapshot = self.load_snapshot(yesterday_str)
        
        if not yesterday_snapshot:
            print(f"No snapshot for yesterday ({yesterday_str})")
            print("Creating baseline with today's data...")
            return {
                'date': today_str,
                'baseline_created': True,
                'total_users': len(today_snapshot['users']) if today_snapshot else 0,
                'gains': []
            }
        
        # Compare and find gains
        today_users = today_snapshot.get('users', {})
        yesterday_users = yesterday_snapshot.get('users', {})
        
        gains = []
        total_plus_one = 0
        total_plus_many = 0
        
        for username in today_users:
            today_user = today_users[username]
            today_points = today_user.get('total_points', 0)
            
            if username in yesterday_users:
                yesterday_user = yesterday_users[username]
                yesterday_points = yesterday_user.get('total_points', 0)
                gain = today_points - yesterday_points
                
                if gain >= min_gain:
                    gains.append({
                        'username': username,
                        'yesterday_points': yesterday_points,
                        'today_points': today_points,
                        'gain': gain,
                        'rank_change': today_user.get('rank', 0) - yesterday_user.get('rank', 0)
                    })
                    
                    if gain == 1:
                        total_plus_one += 1
                    elif gain > 1:
                        total_plus_many += 1
        
        # Find new users
        new_users = []
        for username in today_users:
            if username not in yesterday_users:
                new_users.append({
                    'username': username,
                    'points': today_users[username].get('total_points', 0)
                })
        
        return {
            'date': today_str,
            'total_users_gained_points': len(gains),
            'users_with_1_point': total_plus_one,
            'users_with_many_points': total_plus_many,
            'new_users': len(new_users),
            'gains': gains,
            'new_users_list': new_users
        }
    
    def create_daily_report(self, min_gain: int = 1) -> str:
        """Create a full daily report"""
        gains_data = self.get_daily_gains(min_gain)
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"Daily Points Report - {gains_data.get('date', 'N/A')}")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        if gains_data.get('baseline_created'):
            report_lines.append("📊 Baseline Created - No previous data to compare")
            report_lines.append(f"Total Users Today: {gains_data.get('total_users', 0)}")
        else:
            report_lines.append(f"✅ Users who gained {min_gain}+ points: {gains_data.get('total_users_gained_points', 0)}")
            report_lines.append(f"   • +1 point: {gains_data.get('users_with_1_point', 0)}")
            report_lines.append(f"   • +2+ points: {gains_data.get('users_with_many_points', 0)}")
            
            if gains_data.get('new_users'):
                report_lines.append(f"🆕 New users today: {gains_data.get('new_users', 0)}")
            
            report_lines.append("")
            
            # Show top gainers
            gains = gains_data.get('gains', [])
            if gains:
                # Sort by gain amount
                gains.sort(key=lambda x: x['gain'], reverse=True)
                
                report_lines.append("📈 Top 20 Point Gainers:")
                report_lines.append("-" * 80)
                report_lines.append(f"{'Username':<30} {'Yesterday':<12} {'Today':<12} {'Gain':<10} {'Rank Δ':<10}")
                report_lines.append("-" * 80)
                
                for user in gains[:20]:
                    rank_change = user['rank_change']
                    rank_symbol = "📈" if rank_change < 0 else "📉" if rank_change > 0 else "➡️"
                    rank_display = f"{rank_symbol} {abs(rank_change)}" if rank_change != 0 else "➡️ 0"
                    
                    report_lines.append(f"@{user['username']:<29} {user['yesterday_points']:<12} "
                                      f"{user['today_points']:<12} +{user['gain']:<9} {rank_display}")
                
                # Show users with exactly 1 point
                one_pointers = [u for u in gains if u['gain'] == 1]
                if one_pointers:
                    report_lines.append("")
                    report_lines.append(f"🎯 Users who gained exactly 1 point ({len(one_pointers)}):")
                    report_lines.append("-" * 80)
                    
                    for user in one_pointers[:30]:  # Show first 30
                        rank_change = user['rank_change']
                        rank_symbol = "📈" if rank_change < 0 else "📉" if rank_change > 0 else "➡️"
                        rank_display = f"{rank_symbol} {abs(rank_change)}" if rank_change != 0 else "➡️ 0"
                        
                        report_lines.append(f"@{user['username']:<29} {user['today_points']:<12} "
                                          f"Rank change: {rank_display}")
                    
                    if len(one_pointers) > 30:
                        report_lines.append(f"... and {len(one_pointers) - 30} more")
                
                # Show new users
                new_users = gains_data.get('new_users_list', [])
                if new_users:
                    report_lines.append("")
                    report_lines.append(f"🆕 New users this report:")
                    report_lines.append("-" * 80)
                    for user in new_users[:20]:
                        report_lines.append(f"@{user['username']:<29} {user['points']} points")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        # Save to file
        today_str = datetime.now().strftime('%Y-%m-%d')
        report_filename = f"daily_report_{today_str}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        return report_text


def main():
    """Main function to create daily report"""
    tracker = DailyPointsTracker()
    
    print("Creating daily points report...")
    print("=" * 80)
    
    # Fetch current snapshot
    print("Fetching current leaderboard...")
    current_users = tracker.scraper.get_leaderboard(limit=1000)
    print(f"✓ Fetched {len(current_users)} users")
    
    # Save snapshot
    print("Saving snapshot...")
    tracker.save_snapshot(current_users)
    print("✓ Snapshot saved")
    
    # Generate report
    print("\nGenerating report...")
    report = tracker.create_daily_report(min_gain=1)
    print(report)
    
    print("\n" + "=" * 80)
    print("✅ Daily report complete!")


if __name__ == '__main__':
    main()

