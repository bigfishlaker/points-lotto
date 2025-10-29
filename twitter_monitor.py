import tweepy
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import Config
from database import DatabaseManager

class TwitterMonitor:
    def __init__(self):
        self.config = Config()
        self.db = DatabaseManager()
        
        # Initialize Twitter API
        self.api = self._init_twitter_api()
        self.client = self._init_twitter_client()
        
    def _init_twitter_api(self):
        """Initialize Twitter API v1.1"""
        auth = tweepy.OAuthHandler(
            self.config.TWITTER_API_KEY,
            self.config.TWITTER_API_SECRET
        )
        auth.set_access_token(
            self.config.TWITTER_ACCESS_TOKEN,
            self.config.TWITTER_ACCESS_TOKEN_SECRET
        )
        return tweepy.API(auth, wait_on_rate_limit=True)
    
    def _init_twitter_client(self):
        """Initialize Twitter API v2 client"""
        return tweepy.Client(
            bearer_token=self.config.TWITTER_BEARER_TOKEN,
            consumer_key=self.config.TWITTER_API_KEY,
            consumer_secret=self.config.TWITTER_API_SECRET,
            access_token=self.config.TWITTER_ACCESS_TOKEN,
            access_token_secret=self.config.TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Get user information including verification status"""
        try:
            # Remove @ if present
            username = username.replace('@', '')
            
            user = self.client.get_user(
                username=username,
                user_fields=['verified', 'public_metrics', 'created_at']
            )
            
            if user.data:
                return {
                    'id': user.data.id,
                    'username': user.data.username,
                    'display_name': user.data.name,
                    'is_verified': user.data.verified,
                    'followers_count': user.data.public_metrics['followers_count'],
                    'created_at': user.data.created_at
                }
        except Exception as e:
            print(f"Error getting user info for {username}: {e}")
        return None
    
    def get_recent_tweets_from_account(self, username: str, count: int = 20) -> List[Dict]:
        """Get recent tweets from a specific account"""
        try:
            username = username.replace('@', '')
            
            tweets = self.client.get_users_tweets(
                id=self._get_user_id(username),
                max_results=count,
                tweet_fields=['created_at', 'public_metrics', 'context_annotations']
            )
            
            if tweets.data:
                return [{
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at,
                    'public_metrics': tweet.public_metrics
                } for tweet in tweets.data]
        except Exception as e:
            print(f"Error getting tweets from {username}: {e}")
        return []
    
    def _get_user_id(self, username: str) -> Optional[str]:
        """Get user ID from username"""
        try:
            user = self.client.get_user(username=username)
            return user.data.id if user.data else None
        except Exception as e:
            print(f"Error getting user ID for {username}: {e}")
        return None
    
    def detect_keyword_posts(self, username: str) -> List[Dict]:
        """Detect posts that contain lottery keywords"""
        tweets = self.get_recent_tweets_from_account(username)
        keyword_patterns = [
            r'#lottery',
            r'#contest',
            r'#giveaway',
            r'#win',
            r'keyword:',
            r'comment to enter',
            r'lottery time',
            r'points lottery'
        ]
        
        keyword_tweets = []
        for tweet in tweets:
            tweet_text = tweet['text'].lower()
            for pattern in keyword_patterns:
                if re.search(pattern, tweet_text):
                    keyword_tweets.append(tweet)
                    break
        
        return keyword_tweets
    
    def get_tweet_replies(self, tweet_id: str) -> List[Dict]:
        """Get replies to a specific tweet"""
        try:
            replies = self.client.search_recent_tweets(
                query=f"conversation_id:{tweet_id}",
                max_results=100,
                tweet_fields=['created_at', 'author_id', 'public_metrics'],
                user_fields=['verified', 'username', 'name']
            )
            
            if replies.data:
                return [{
                    'id': reply.id,
                    'text': reply.text,
                    'author_id': reply.author_id,
                    'created_at': reply.created_at,
                    'public_metrics': reply.public_metrics
                } for reply in replies.data]
        except Exception as e:
            print(f"Error getting replies for tweet {tweet_id}: {e}")
        return []
    
    def get_tweet_likes(self, tweet_id: str) -> List[Dict]:
        """Get users who liked a specific tweet"""
        try:
            likes = self.client.get_liked_users(
                id=tweet_id,
                user_fields=['verified', 'username', 'name', 'public_metrics']
            )
            
            if likes.data:
                return [{
                    'id': user.id,
                    'username': user.username,
                    'display_name': user.name,
                    'is_verified': user.verified,
                    'followers_count': user.public_metrics['followers_count']
                } for user in likes.data]
        except Exception as e:
            print(f"Error getting likes for tweet {tweet_id}: {e}")
        return []
    
    def get_tweet_retweets(self, tweet_id: str) -> List[Dict]:
        """Get users who retweeted a specific tweet"""
        try:
            retweets = self.client.get_retweeters(
                id=tweet_id,
                user_fields=['verified', 'username', 'name', 'public_metrics']
            )
            
            if retweets.data:
                return [{
                    'id': user.id,
                    'username': user.username,
                    'display_name': user.name,
                    'is_verified': user.verified,
                    'followers_count': user.public_metrics['followers_count']
                } for user in retweets.data]
        except Exception as e:
            print(f"Error getting retweets for tweet {tweet_id}: {e}")
        return []
    
    def process_keyword_tweet(self, tweet: Dict) -> bool:
        """Process a keyword tweet and collect verified users"""
        tweet_id = tweet['id']
        tweet_text = tweet['text']
        
        # Extract keyword from tweet
        keyword = self._extract_keyword_from_tweet(tweet_text)
        if not keyword:
            return False
        
        # Add keyword to database
        keyword_id = self.db.add_keyword(keyword, tweet_id)
        if not keyword_id:
            return False
        
        print(f"Processing keyword tweet: {keyword} (ID: {tweet_id})")
        
        # Get all types of engagement
        replies = self.get_tweet_replies(tweet_id)
        likes = self.get_tweet_likes(tweet_id)
        retweets = self.get_tweet_retweets(tweet_id)
        
        # Process verified users from replies
        verified_users = 0
        for reply in replies:
            user_info = self.get_user_info_by_id(reply['author_id'])
            if user_info and user_info['is_verified']:
                user_id = self.db.add_user(
                    user_info['id'],
                    user_info['username'],
                    user_info['display_name'],
                    user_info['is_verified']
                )
                if user_id:
                    self.db.add_engagement(user_id, keyword_id, 'comment', reply['id'])
                    verified_users += 1
        
        # Process verified users from likes
        for like in likes:
            if like['is_verified']:
                user_id = self.db.add_user(
                    like['id'],
                    like['username'],
                    like['display_name'],
                    like['is_verified']
                )
                if user_id:
                    self.db.add_engagement(user_id, keyword_id, 'like', tweet_id)
                    verified_users += 1
        
        # Process verified users from retweets
        for retweet in retweets:
            if retweet['is_verified']:
                user_id = self.db.add_user(
                    retweet['id'],
                    retweet['username'],
                    retweet['display_name'],
                    retweet['is_verified']
                )
                if user_id:
                    self.db.add_engagement(user_id, keyword_id, 'retweet', tweet_id)
                    verified_users += 1
        
        print(f"Found {verified_users} verified users for keyword: {keyword}")
        return True
    
    def get_user_info_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user information by user ID"""
        try:
            user = self.client.get_user(
                id=user_id,
                user_fields=['verified', 'public_metrics', 'created_at']
            )
            
            if user.data:
                return {
                    'id': user.data.id,
                    'username': user.data.username,
                    'display_name': user.data.name,
                    'is_verified': user.data.verified,
                    'followers_count': user.data.public_metrics['followers_count'],
                    'created_at': user.data.created_at
                }
        except Exception as e:
            print(f"Error getting user info for ID {user_id}: {e}")
        return None
    
    def _extract_keyword_from_tweet(self, tweet_text: str) -> Optional[str]:
        """Extract the main keyword from a tweet"""
        # Look for patterns like "keyword: X" or "#X"
        patterns = [
            r'keyword:\s*([^\s]+)',
            r'#([^\s]+)',
            r'lottery:\s*([^\s]+)',
            r'contest:\s*([^\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, tweet_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def monitor_account(self, username: str) -> None:
        """Continuously monitor an account for keyword posts"""
        print(f"Starting to monitor account: {username}")
        
        while True:
            try:
                # Get recent tweets
                tweets = self.get_recent_tweets_from_account(username, count=10)
                
                # Check for new keyword posts
                for tweet in tweets:
                    # Check if this tweet is already processed
                    existing_keywords = self.db.get_active_keywords()
                    if any(kw['tweet_id'] == tweet['id'] for kw in existing_keywords):
                        continue
                    
                    # Check if it's a keyword post
                    keyword_tweets = self.detect_keyword_posts(username)
                    if any(kt['id'] == tweet['id'] for kt in keyword_tweets):
                        self.process_keyword_tweet(tweet)
                
                # Wait before next check
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute on error


