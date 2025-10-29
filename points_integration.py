"""
Integration layer to sync PointsMarket.io data with lottery system
"""
import time
from typing import List, Dict, Optional
from pointsmarket_scraper import PointsMarketScraper
from database import DatabaseManager

class PointsMarketIntegration:
    """Integrate PointsMarket.io data with the lottery system"""
    
    def __init__(self):
        self.scraper = PointsMarketScraper()
        self.db = DatabaseManager()
        self.min_points_required = 0  # Configurable minimum points
    
    def sync_user_data(self, username: str) -> bool:
        """
        Sync a single user's data from PointsMarket.io
        
        Args:
            username: Twitter username to sync
            
        Returns:
            True if successful, False otherwise
        """
        # Get points data from PointsMarket
        points_data = self.scraper.get_user_points(username)
        
        if not points_data:
            print(f"No data found for user: {username}")
            return False
        
        # Get or create user in database
        user = self.db.get_user_by_twitter_id(username)
        
        if user:
            # Update existing user with external points
            return self._update_user_with_external_points(user['id'], points_data)
        else:
            # Create new user entry
            return self._add_user_with_external_points(points_data)
    
    def _update_user_with_external_points(self, user_id: int, points_data: Dict) -> bool:
        """Update existing user with external points data"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Add external points to a new column or update existing
            cursor.execute('''
                UPDATE users SET 
                    total_points = ?,
                    last_active = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (points_data.get('total_points', 0), user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    def _add_user_with_external_points(self, points_data: Dict) -> bool:
        """Add new user with external points data"""
        username = points_data.get('username')
        if not username:
            return False
        
        return self.db.add_user(
            twitter_id=username,
            username=username,
            display_name=username,
            is_verified=True  # Assume verified from PointsMarket
        ) is not None
    
    def bulk_sync_users(self, usernames: List[str], delay: float = 1.0) -> Dict:
        """
        Sync multiple users from PointsMarket.io
        
        Args:
            usernames: List of usernames to sync
            delay: Delay between requests (in seconds)
            
        Returns:
            Dict with sync results
        """
        results = {
            'successful': [],
            'failed': [],
            'total': len(usernames)
        }
        
        for username in usernames:
            try:
                success = self.sync_user_data(username)
                
                if success:
                    results['successful'].append(username)
                else:
                    results['failed'].append(username)
                
                # Rate limiting
                time.sleep(delay)
                
            except Exception as e:
                print(f"Error syncing user {username}: {e}")
                results['failed'].append(username)
        
        return results
    
    def check_user_qualification(self, username: str, min_points: int = None) -> bool:
        """
        Check if a user qualifies based on PointsMarket.io points
        
        Args:
            username: Twitter username
            min_points: Minimum points required (uses default if None)
            
        Returns:
            True if user qualifies
        """
        if min_points is None:
            min_points = self.min_points_required
        
        return self.scraper.check_user_qualification(username, min_points)
    
    def get_qualified_users(self, min_points: int = 0, limit: int = None) -> List[Dict]:
        """
        Get all users from PointsMarket leaderboard who qualify
        
        Args:
            min_points: Minimum points required
            limit: Maximum number of users to fetch (default 1000)
            
        Returns:
            List of qualified user data
        """
        # Fetch with high limit to get all users
        leaderboard = self.scraper.get_leaderboard(limit=limit)
        
        qualified = []
        for user in leaderboard:
            if user.get('total_points', 0) >= min_points:
                qualified.append(user)
        
        return qualified
    
    def sync_qualified_leaderboard(self, min_points: int = 0) -> Dict:
        """
        Sync qualified users from PointsMarket leaderboard into database
        
        Args:
            min_points: Minimum points required
            
        Returns:
            Sync results summary
        """
        print(f"Starting leaderboard sync with minimum points: {min_points}")
        
        qualified_users = self.get_qualified_users(min_points)
        print(f"Found {len(qualified_users)} qualified users")
        
        usernames = [user['username'] for user in qualified_users]
        results = self.bulk_sync_users(usernames)
        
        print(f"Sync complete: {len(results['successful'])} successful, {len(results['failed'])} failed")
        
        return {
            'qualified_users_found': len(qualified_users),
            'successful_syncs': len(results['successful']),
            'failed_syncs': len(results['failed']),
            'details': results
        }
    
    def sync_lottery_participants(self) -> Dict:
        """
        Sync users who have engaged with lottery keywords from PointsMarket
        
        Returns:
            Sync results
        """
        import sqlite3
        
        # Get all users from database who have engaged
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT username FROM users')
        users = cursor.fetchall()
        conn.close()
        
        usernames = [user[0] for user in users]
        
        print(f"Syncing {len(usernames)} existing users from PointsMarket")
        results = self.bulk_sync_users(usernames)
        
        return results
    
    def set_min_points_required(self, min_points: int):
        """Set the minimum points required for qualification"""
        self.min_points_required = min_points

