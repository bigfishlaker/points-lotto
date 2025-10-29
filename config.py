import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Twitter API Configuration
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
    
    # Main Twitter Account to Monitor
    MAIN_TWITTER_ACCOUNT = os.getenv('MAIN_TWITTER_ACCOUNT', '@yourmainaccount')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///lottery.db')
    
    # Lottery Configuration
    LOTTERY_INTERVAL_HOURS = 6
    POINTS_PER_ENGAGEMENT = 1
    
    # Web Dashboard Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

