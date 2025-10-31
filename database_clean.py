import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path: str = "lottery.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize clean database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Daily winners table - one winner per day (24-hour drawings)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winner_username TEXT NOT NULL,
                winner_points INTEGER DEFAULT 0,
                drawing_date DATE UNIQUE NOT NULL,
                selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT 1,
                total_eligible INTEGER,
                random_seed INTEGER,
                selection_hash TEXT
            )
        ''')
        
        # Add columns if they don't exist
        for col in ['total_eligible', 'random_seed', 'selection_hash']:
            try:
                cursor.execute(f'ALTER TABLE daily_winners ADD COLUMN {col} INTEGER' if col in ['total_eligible', 'random_seed'] else f'ALTER TABLE daily_winners ADD COLUMN {col} TEXT')
            except sqlite3.OperationalError:
                pass
        
        conn.commit()
        conn.close()
    
    def record_winner(self, username: str, points: int, drawing_date: str, total_eligible: int = None, random_seed: int = None, selection_hash: str = None) -> bool:
        """Record a daily winner - one per day"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        try:
            conn.execute('BEGIN EXCLUSIVE')
            
            # Check if winner already exists for this date
            cursor.execute('SELECT id FROM daily_winners WHERE drawing_date = ?', (drawing_date,))
            if cursor.fetchone():
                conn.rollback()
                conn.close()
                return False
            
            # Set previous winners to not current
            cursor.execute('UPDATE daily_winners SET is_current = 0')
            
            # Insert new winner
            cursor.execute('''
                INSERT INTO daily_winners (winner_username, winner_points, drawing_date, is_current, total_eligible, random_seed, selection_hash)
                VALUES (?, ?, ?, 1, ?, ?, ?)
            ''', (username, points, drawing_date, total_eligible, random_seed, selection_hash))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.rollback()
            conn.close()
            return False
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error recording winner: {e}")
            return False
    
    def get_current_winner(self) -> Optional[Dict]:
        """Get the current active winner"""
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
        """Get winner for a specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT winner_username, winner_points, drawing_date, selected_at
            FROM daily_winners
            WHERE drawing_date = ?
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
    
    def get_all_winners(self) -> List[Dict]:
        """Get all winners ordered by date (newest first)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT winner_username, winner_points, drawing_date, selected_at
            FROM daily_winners
            ORDER BY drawing_date DESC
        ''')
        results = cursor.fetchall()
        conn.close()
        return [{
            'username': r[0],
            'points': r[1],
            'drawing_date': r[2],
            'selected_at': r[3] if r[3] else r[2]
        } for r in results]

