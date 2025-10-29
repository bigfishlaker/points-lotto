import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Optional
import json

# Use html.parser to avoid lxml dependency issues on Windows
BEAUTIFULSOUP_PARSER = 'html.parser'

class PointsMarketScraper:
    """Scraper for pointsmarket.io to get user points data"""
    
    def __init__(self):
        self.base_url = "https://www.pointsmarket.io"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_user_points(self, username: str) -> Optional[Dict]:
        """
        Get points data for a specific user from pointsmarket.io
        
        Args:
            username: Twitter username (without @)
            
        Returns:
            Dict with user points data or None if not found
        """
        username = username.replace('@', '')
        
        try:
            # Try to get user profile page
            url = f"{self.base_url}/user/{username}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try to extract data from the page
                user_data = self._parse_user_page(soup)
                return user_data
            
            # Try alternative approach - fetch from their API if it exists
            api_url = f"{self.base_url}/api/user/{username}"
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
                
        except Exception as e:
            print(f"Error fetching user data for {username}: {e}")
        
        return None
    
    def _parse_user_page(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Parse user data from HTML page"""
        try:
            # Look for user data in the page
            user_data = {}
            
            # Try to find username
            username_elem = soup.find('span', class_='username') or soup.find('h1')
            if username_elem:
                user_data['username'] = username_elem.get_text().strip()
            
            # Try to find total points
            points_elem = soup.find('div', class_='total-points') or soup.find('span', class_='points')
            if points_elem:
                points_text = points_elem.get_text()
                points = re.search(r'\d+', points_text)
                if points:
                    user_data['total_points'] = int(points.group())
            
            # Try to find rank
            rank_elem = soup.find('div', class_='rank') or soup.find('span', class_='rank')
            if rank_elem:
                rank_text = rank_elem.get_text()
                rank = re.search(r'\d+', rank_text)
                if rank:
                    user_data['rank'] = int(rank.group())
            
            # Try to find transactions count
            transactions_elem = soup.find('div', class_='transactions')
            if transactions_elem:
                trans_text = transactions_elem.get_text()
                trans = re.search(r'\d+', trans_text)
                if trans:
                    user_data['transactions'] = int(trans.group())
            
            return user_data if user_data else None
            
        except Exception as e:
            print(f"Error parsing user page: {e}")
            return None
    
    def check_user_qualification(self, username: str, min_points: int = 0) -> bool:
        """
        Check if a user qualifies based on their points
        
        Args:
            username: Twitter username
            min_points: Minimum points required to qualify
            
        Returns:
            True if user qualifies, False otherwise
        """
        user_data = self.get_user_points(username)
        
        if not user_data:
            return False
        
        return user_data.get('total_points', 0) >= min_points
    
    def get_leaderboard(self, limit: int = None) -> List[Dict]:
        """
        Get top users from the leaderboard
        
        Args:
            limit: Number of users to fetch
            
        Returns:
            List of user data dictionaries
        """
        try:
            # Access the leaderboard API
            url = f"{self.base_url}/api/leaderboard"
            # Don't limit API call - fetch all available users
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract leaderboard data from the API response
                leaderboard_data = data.get('leaderboard', [])
                
                users = []
                # Limit slicing only if limit is specified
                data_to_process = leaderboard_data if limit is None else leaderboard_data[:limit]
                
                for i, user in enumerate(data_to_process):
                    # Extract relevant user data
                    community_score = user.get('community_score', {})
                    # Use the 'points' field which is the actual total points
                    total_points = user.get('points', 0)
                    
                    user_info = {
                        'username': user.get('username', ''),
                        'total_points': total_points,
                        'upvotes': community_score.get('upvotes', 0),
                        'downvotes': community_score.get('downvotes', 0),
                        'rank': user.get('rank', i + 1),
                        'transactions': user.get('transactions', 0),
                        'badges': [b.get('badge_name', '') for b in user.get('badges', [])]
                    }
                    users.append(user_info)
                
                return users
            
            # Fallback: scrape the leaderboard page
            url = f"{self.base_url}/leaderboard"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, BEAUTIFULSOUP_PARSER)
                return self._parse_leaderboard(soup)
                
        except Exception as e:
            print(f"Error fetching leaderboard: {e}")
        
        return []
    
    def _parse_leaderboard(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse leaderboard data from HTML"""
        users = []
        try:
            # Look for table rows or list items with user data
            rows = soup.find_all('tr') or soup.find_all('div', class_='user-item')
            
            for row in rows[:100]:  # Limit to 100 users
                user_data = {}
                
                # Extract username
                username_elem = row.find('span', class_='username') or row.find('a')
                if username_elem:
                    user_data['username'] = username_elem.get_text().strip()
                
                # Extract points
                points_elem = row.find('span', class_='points') or row.find('td')
                if points_elem:
                    points_text = points_elem.get_text()
                    points = re.search(r'\d+', points_text)
                    if points:
                        user_data['total_points'] = int(points.group())
                
                if user_data.get('username') and user_data.get('total_points'):
                    users.append(user_data)
                    
        except Exception as e:
            print(f"Error parsing leaderboard: {e}")
        
        return users
    
    def get_recent_distributors(self, limit: int = 50) -> List[Dict]:
        """Get recent trusted distributors"""
        try:
            url = f"{self.base_url}/api/distributors"
            response = self.session.get(url, params={'limit': limit}, timeout=10)
            
            if response.status_code == 200:
                return response.json().get('distributors', [])
                
        except Exception as e:
            print(f"Error fetching distributors: {e}")
        
        return []
    
    def check_multiple_users(self, usernames: List[str]) -> List[Dict]:
        """
        Check multiple users and return their qualification status
        
        Args:
            usernames: List of Twitter usernames
            
        Returns:
            List of user data with qualification status
        """
        results = []
        
        for username in usernames:
            user_data = self.get_user_points(username)
            
            if user_data:
                results.append({
                    'username': username,
                    'qualifies': True,
                    'data': user_data
                })
            else:
                results.append({
                    'username': username,
                    'qualifies': False,
                    'data': None
                })
            
            # Be respectful - add delay between requests
            time.sleep(1)
        
        return results
    
    def search_user_by_twitter_id(self, twitter_id: str) -> Optional[Dict]:
        """Search for a user by their Twitter ID"""
        try:
            # This might require API access
            url = f"{self.base_url}/api/user/id/{twitter_id}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
                
        except Exception as e:
            print(f"Error searching user by ID {twitter_id}: {e}")
        
        return None
    
    def get_user_transactions(self, username: str) -> List[Dict]:
        """Get transaction history for a user"""
        try:
            url = f"{self.base_url}/api/user/{username}/transactions"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json().get('transactions', [])
                
        except Exception as e:
            print(f"Error fetching transactions for {username}: {e}")
        
        return []

