import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path: str = "lottery.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table - stores verified users who participate
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                twitter_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                display_name TEXT,
                is_verified BOOLEAN DEFAULT 0,
                total_points INTEGER DEFAULT 0,
                external_points INTEGER DEFAULT 0,
                points_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Try to add new columns to existing table (if not exists)
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN external_points INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN points_source TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Keywords table - stores active keywords for lottery
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                tweet_id TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                lottery_run_at TIMESTAMP
            )
        ''')
        
        # Engagements table - tracks user interactions with keyword posts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engagements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                keyword_id INTEGER,
                engagement_type TEXT NOT NULL, -- 'comment', 'like', 'retweet'
                tweet_id TEXT NOT NULL,
                points_awarded INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (keyword_id) REFERENCES keywords (id)
            )
        ''')
        
        # Lottery results table - stores lottery winners
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword_id INTEGER,
                winner_user_id INTEGER,
                points_won INTEGER,
                lottery_run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (keyword_id) REFERENCES keywords (id),
                FOREIGN KEY (winner_user_id) REFERENCES users (id)
            )
        ''')
        
        # Daily 24h winners table - stores winners for the 24h drawing
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winner_username TEXT NOT NULL,
                winner_points INTEGER,
                drawing_date DATE UNIQUE NOT NULL,
                selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT 1,
                total_eligible INTEGER,
                random_seed INTEGER,
                selection_hash TEXT
            )
        ''')
        
        # Add new columns if they don't exist
        try:
            cursor.execute('ALTER TABLE daily_winners ADD COLUMN total_eligible INTEGER')
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute('ALTER TABLE daily_winners ADD COLUMN random_seed INTEGER')
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute('ALTER TABLE daily_winners ADD COLUMN selection_hash TEXT')
        except sqlite3.OperationalError:
            pass
        
        # Set previous winners to not current (only if table has rows)
        try:
            cursor.execute('UPDATE daily_winners SET is_current = 0 WHERE is_current = 1')
        except sqlite3.OperationalError:
            pass  # Table might be empty
        
        conn.commit()
        conn.close()
    
    def add_user(self, twitter_id: str, username: str, display_name: str, is_verified: bool = False) -> int:
        """Add a new user to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users (twitter_id, username, display_name, is_verified, last_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (twitter_id, username, display_name, is_verified, datetime.now()))
            
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
        except sqlite3.Error as e:
            print(f"Error adding user: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_by_twitter_id(self, twitter_id: str) -> Optional[Dict]:
        """Get user by Twitter ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE twitter_id = ?', (twitter_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'twitter_id': user[1],
                'username': user[2],
                'display_name': user[3],
                'is_verified': user[4],
                'total_points': user[5],
                'created_at': user[6],
                'last_active': user[7]
            }
        return None
    
    def add_keyword(self, keyword: str, tweet_id: str) -> int:
        """Add a new keyword for lottery"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO keywords (keyword, tweet_id, is_active)
                VALUES (?, ?, 1)
            ''', (keyword, tweet_id))
            
            keyword_id = cursor.lastrowid
            conn.commit()
            return keyword_id
        except sqlite3.Error as e:
            print(f"Error adding keyword: {e}")
            return None
        finally:
            conn.close()
    
    def get_active_keywords(self) -> List[Dict]:
        """Get all active keywords"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM keywords WHERE is_active = 1')
        keywords = cursor.fetchall()
        conn.close()
        
        return [{
            'id': kw[0],
            'keyword': kw[1],
            'tweet_id': kw[2],
            'is_active': kw[3],
            'created_at': kw[4],
            'lottery_run_at': kw[5]
        } for kw in keywords]
    
    def add_engagement(self, user_id: int, keyword_id: int, engagement_type: str, tweet_id: str, points: int = 1) -> bool:
        """Record user engagement with keyword post"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if engagement already exists
            cursor.execute('''
                SELECT id FROM engagements 
                WHERE user_id = ? AND keyword_id = ? AND engagement_type = ?
            ''', (user_id, keyword_id, engagement_type))
            
            if cursor.fetchone():
                return False  # Engagement already recorded
            
            # Add engagement
            cursor.execute('''
                INSERT INTO engagements (user_id, keyword_id, engagement_type, tweet_id, points_awarded)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, keyword_id, engagement_type, tweet_id, points))
            
            # Update user's total points
            cursor.execute('''
                UPDATE users SET total_points = total_points + ?, last_active = ?
                WHERE id = ?
            ''', (points, datetime.now(), user_id))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding engagement: {e}")
            return False
        finally:
            conn.close()
    
    def get_eligible_users_for_lottery(self, keyword_id: int) -> List[Dict]:
        """Get all users who engaged with a specific keyword"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT u.*, COUNT(e.id) as engagement_count
            FROM users u
            JOIN engagements e ON u.id = e.user_id
            WHERE e.keyword_id = ? AND u.is_verified = 1
            GROUP BY u.id
        ''', (keyword_id,))
        
        users = cursor.fetchall()
        conn.close()
        
        return [{
            'id': user[0],
            'twitter_id': user[1],
            'username': user[2],
            'display_name': user[3],
            'is_verified': user[4],
            'total_points': user[5],
            'created_at': user[6],
            'last_active': user[7],
            'engagement_count': user[8]
        } for user in users]
    
    def record_lottery_winner(self, keyword_id: int, winner_user_id: int, points_won: int) -> bool:
        """Record lottery winner"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO lottery_results (keyword_id, winner_user_id, points_won)
                VALUES (?, ?, ?)
            ''', (keyword_id, winner_user_id, points_won))
            
            # Update keyword as completed
            cursor.execute('''
                UPDATE keywords SET is_active = 0, lottery_run_at = ?
                WHERE id = ?
            ''', (datetime.now(), keyword_id))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error recording lottery winner: {e}")
            return False
        finally:
            conn.close()
    
    def get_lottery_history(self, limit: int = 10) -> List[Dict]:
        """Get recent lottery results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT lr.*, u.username, u.display_name, k.keyword
            FROM lottery_results lr
            JOIN users u ON lr.winner_user_id = u.id
            JOIN keywords k ON lr.keyword_id = k.id
            ORDER BY lr.lottery_run_at DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': result[0],
            'keyword_id': result[1],
            'winner_user_id': result[2],
            'points_won': result[3],
            'lottery_run_at': result[4],
            'winner_username': result[5],
            'winner_display_name': result[6],
            'keyword': result[7]
        } for result in results]
    
    def record_daily_winner(self, username: str, points: int, drawing_date: str = None, total_eligible: int = None, random_seed: int = None, selection_hash: str = None) -> bool:
        """Record a daily 24h lottery winner with audit trail - GUARANTEED only one winner per day"""
        from datetime import datetime, date
        import hashlib
        
        conn = sqlite3.connect(self.db_path)
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        # Set timeout for locks
        conn.execute('PRAGMA busy_timeout=5000')
        cursor = conn.cursor()
        
        try:
            if drawing_date is None:
                drawing_date = date.today().isoformat()
            
            # Use an exclusive transaction to prevent race conditions
            conn.execute('BEGIN EXCLUSIVE')
            
            # FIRST: Check if winner already exists for this date (within transaction)
            cursor.execute('SELECT id, winner_username FROM daily_winners WHERE drawing_date = ?', (drawing_date,))
            existing = cursor.fetchone()
            
            if existing:
                # Winner already selected for today - ensure it's marked as current and don't overwrite
                cursor.execute('UPDATE daily_winners SET is_current = 1 WHERE drawing_date = ?', (drawing_date,))
                conn.commit()
                conn.close()
                print(f"🛡️ Winner already exists for {drawing_date}: @{existing[1]} - preventing duplicate")
                return False
            
            # Only set previous winners to not current if we're inserting a new one
            cursor.execute('UPDATE daily_winners SET is_current = 0 WHERE drawing_date != ?', (drawing_date,))
            
            # Create selection hash for verification
            if selection_hash is None:
                hash_input = f"{drawing_date}{username}{points}{random_seed or 0}"
                selection_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
            
            # Insert new winner - UNIQUE constraint on drawing_date will prevent duplicates
            cursor.execute('''
                INSERT INTO daily_winners (winner_username, winner_points, drawing_date, is_current, total_eligible, random_seed, selection_hash)
                VALUES (?, ?, ?, 1, ?, ?, ?)
            ''', (username, points, drawing_date, total_eligible, random_seed, selection_hash))
            
            conn.commit()
            conn.close()
            print(f"✅ Winner recorded successfully: @{username} for {drawing_date}")
            return True
        except sqlite3.IntegrityError as e:
            # UNIQUE constraint violation - winner already exists (race condition caught)
            conn.rollback()
            conn.close()
            print(f"🛡️ IntegrityError: Winner already exists for {drawing_date} - race condition prevented")
            return False
        except sqlite3.Error as e:
            conn.rollback()
            conn.close()
            print(f"❌ Error recording daily winner: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass
    
    def get_current_daily_winner(self) -> Optional[Dict]:
        """Get the current daily winner with audit info"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT winner_username, winner_points, drawing_date, selected_at, total_eligible, random_seed, selection_hash
            FROM daily_winners
            WHERE is_current = 1
            ORDER BY selected_at DESC
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'username': result[0],
                'points': result[1],
                'drawing_date': result[2],
                'selected_at': result[3],
                'total_eligible': result[4],
                'random_seed': result[5],
                'selection_hash': result[6]
            }
        return None

    def get_winner_for_date(self, drawing_date: str) -> Optional[Dict]:
        """Get the winner for a specific drawing date (YYYY-MM-DD)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT winner_username, winner_points, drawing_date, selected_at
            FROM daily_winners
            WHERE drawing_date = ?
            LIMIT 1
        ''', (drawing_date,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {
                'username': result[0],
                'points': result[1],
                'drawing_date': result[2],
                'selected_at': result[3]
            }
        return None

