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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            # Don't request compression - let requests handle it automatically
            'Referer': 'https://www.pointsmarket.io/',
            'Origin': 'https://www.pointsmarket.io',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
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
        # Retry logic for rate limiting
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Access the leaderboard API - try with pagination parameters
                url = f"{self.base_url}/api/leaderboard"
                # Try with limit parameter to get all users
                params = {'limit': 1000, 'offset': 0}  # Request large limit
                print(f"  📡 Calling PointsMarket API: {url} (attempt {attempt + 1}/{max_retries})")
                
                # Don't limit API call - fetch all available users
                response = self.session.get(url, params=params, timeout=15)
                
                print(f"  📊 API Response Status: {response.status_code}")
                
                # Handle rate limiting
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                        print(f"  ⚠️  Rate limited (429), waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ❌ Rate limited after {max_retries} attempts, trying fallback...")
                        return self._fallback_scrape_leaderboard()
                
                # Handle forbidden errors
                if response.status_code == 403:
                    print(f"  ⚠️  Forbidden (403) - may need different approach")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return self._fallback_scrape_leaderboard()
                
                # Process successful response
                if response.status_code == 200:
                    try:
                        # Check Content-Type header
                        content_type = response.headers.get('Content-Type', '').lower()
                        print(f"  📋 Content-Type: {content_type}")
                        
                        # Try to parse JSON - requests should handle gzip automatically
                        try:
                            data = response.json()
                        except json.JSONDecodeError as json_error:
                            # If JSON decode fails, check if it's compressed
                            print(f"  ⚠️  JSON decode failed: {json_error}")
                            
                            # Check if response.content looks like compressed data
                            content_encoding = response.headers.get('Content-Encoding', '').lower()
                            content_preview = response.content[:100] if len(response.content) > 100 else response.content
                            
                            # Check if content starts with gzip magic bytes (1f 8b)
                            is_gzipped = len(response.content) > 2 and response.content[:2] == b'\x1f\x8b'
                            
                            if is_gzipped or content_encoding == 'gzip':
                                print(f"  🔄 Detected gzip compression (magic bytes: {is_gzipped}, header: {content_encoding})")
                                # Try decompressing manually as fallback
                                import gzip
                                try:
                                    decompressed = gzip.decompress(response.content)
                                    data = json.loads(decompressed.decode('utf-8'))
                                    print(f"  ✅ Successfully decompressed gzip response")
                                except Exception as decompress_error:
                                    print(f"  ❌ Failed to decompress: {decompress_error}")
                                    # Try accessing raw content
                                    print(f"  📄 Raw content preview: {content_preview[:200]}")
                                    raise json_error
                            else:
                                # Not compressed, but still can't parse - show what we got
                                print(f"  📄 Response text preview: {response.text[:200] if hasattr(response, 'text') else 'N/A'}")
                                print(f"  📄 Response content preview: {content_preview[:200]}")
                                raise json_error
                        
                        print(f"  📦 Response data type: {type(data)}")
                        if isinstance(data, dict):
                            print(f"  📦 Response data keys: {list(data.keys())}")
                        elif isinstance(data, list):
                            print(f"  📦 Response is a list with {len(data)} items")
                        
                        # Extract leaderboard data from the API response
                        # Try multiple possible keys
                        leaderboard_data = None
                        if isinstance(data, list):
                            leaderboard_data = data
                            print(f"  ✅ Response is a list with {len(leaderboard_data)} items")
                        elif isinstance(data, dict):
                            leaderboard_data = data.get('leaderboard') or data.get('users') or data.get('data')
                            print(f"  ✅ Found leaderboard_data: {type(leaderboard_data)}, length: {len(leaderboard_data) if leaderboard_data else 0}")
                        else:
                            print(f"  ⚠️  Unexpected response type: {type(data)}")
                        
                        if not leaderboard_data:
                            print(f"  ⚠️  No leaderboard data found in response. Full response: {str(data)[:500]}")
                            # Try fallback scraping
                            return self._fallback_scrape_leaderboard()
                        
                        users = []
                        # Limit slicing only if limit is specified
                        data_to_process = leaderboard_data if limit is None else leaderboard_data[:limit]
                        
                        print(f"  🔄 Processing {len(data_to_process)} users...")
                        
                        for i, user in enumerate(data_to_process):
                            # Extract relevant user data
                            if not isinstance(user, dict):
                                print(f"  ⚠️  User {i} is not a dict: {type(user)}")
                                continue
                            
                            community_score = user.get('community_score', {})
                            # Try multiple field names for points
                            total_points = user.get('points') or user.get('total_points') or user.get('score', 0)
                            
                            username = user.get('username') or user.get('handle') or user.get('name', '')
                            if not username:
                                print(f"  ⚠️  User {i} has no username: {user}")
                                continue
                            
                            user_info = {
                                'username': username,
                                'total_points': int(total_points) if total_points else 0,
                                'upvotes': community_score.get('upvotes', 0) if isinstance(community_score, dict) else 0,
                                'downvotes': community_score.get('downvotes', 0) if isinstance(community_score, dict) else 0,
                                'rank': user.get('rank', i + 1),
                                'transactions': user.get('transactions', 0),
                                'badges': [b.get('badge_name', '') if isinstance(b, dict) else str(b) for b in user.get('badges', [])]
                            }
                            users.append(user_info)
                        
                        print(f"  ✅ Processed {len(users)} users successfully")
                        if users:
                            print(f"  📋 Sample user: {users[0]}")
                        
                        return users
                    except json.JSONDecodeError as e:
                        print(f"  ❌ JSON decode error: {e}")
                        print(f"  📄 Response text (first 500 chars): {response.text[:500]}")
                        return self._fallback_scrape_leaderboard()
                
                # If we get here, we didn't handle the status code above, break out of retry loop
                break
                
            except requests.exceptions.RequestException as e:
                print(f"  ❌ Request error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"  ❌ All attempts failed, trying fallback...")
                    return self._fallback_scrape_leaderboard()
            except Exception as e:
                print(f"  ❌ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return []
        
        # If we get here after retries, try fallback
        print(f"  ⚠️  All retry attempts failed, trying fallback scraping...")
        return self._fallback_scrape_leaderboard()
    
    def _fallback_scrape_leaderboard(self) -> List[Dict]:
        """Fallback method to scrape leaderboard from HTML"""
        try:
            url = f"{self.base_url}/leaderboard"
            print(f"  🔄 Fallback: Scraping {url}")
            
            # Try with a fresh session for fallback
            fallback_session = requests.Session()
            fallback_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.pointsmarket.io/'
            })
            
            response = fallback_session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, BEAUTIFULSOUP_PARSER)
                users = self._parse_leaderboard(soup)
                print(f"  ✅ Scraped {len(users)} users from HTML")
                return users
            elif response.status_code == 403:
                print(f"  ❌ Fallback scraping blocked (403) - may need different headers or IP")
            else:
                print(f"  ❌ Fallback scraping failed with status {response.status_code}")
        except Exception as e:
            print(f"  ❌ Fallback scraping error: {e}")
        
        print(f"  ⚠️  All methods failed - returning empty list")
        return []
    
    def _parse_leaderboard(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse leaderboard data from HTML"""
        users = []
        try:
            # Look for table rows or list items with user data
            rows = soup.find_all('tr') or soup.find_all('div', class_='user-item')
            
            for row in rows:  # Process all users (no limit)
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

