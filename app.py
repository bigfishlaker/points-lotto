from flask import Flask, render_template, request, jsonify
from datetime import datetime, timezone, timedelta
import threading
import time
import random
import hashlib
import os
from database import DatabaseManager

# PointsMarket integration
try:
    from pointsmarket_scraper import PointsMarketScraper
    POINTSMARKET_ENABLED = True
except ImportError:
    POINTSMARKET_ENABLED = False
    PointsMarketScraper = None

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize components
db = DatabaseManager()
if POINTSMARKET_ENABLED:
    points_scraper = PointsMarketScraper()

# Global scheduler state
_scheduler_running = False
_scheduler_thread = None
_winner_selection_lock = threading.Lock()

def init_database_with_winners():
    """Initialize database and add initial winners if empty"""
    try:
        winners = db.get_all_winners()
        print(f"Database has {len(winners)} existing winners")
        
        if len(winners) == 0:
            print("Initializing database with initial winners...")
            from datetime import datetime
            
            initial_winners = [
                {
                    'username': 'doomercorp',
                    'points': 100,
                    'drawing_date': '2025-10-29',
                    'selected_at': datetime(2025, 10, 29, 0, 5, 0).isoformat(),
                    'total_eligible': 920,
                    'random_seed': 12345,
                    'selection_hash': 'abc123def456',
                },
                {
                    'username': 'noobysol',
                    'points': 150,
                    'drawing_date': '2025-10-28',
                    'selected_at': datetime(2025, 10, 28, 0, 5, 0).isoformat(),
                    'total_eligible': 900,
                    'random_seed': 67890,
                    'selection_hash': 'def456ghi789',
                }
            ]
            
            for winner in initial_winners:
                success = db.record_daily_winner(
                    winner['username'],
                    winner['points'],
                    winner['drawing_date'],
                    total_eligible=winner['total_eligible'],
                    random_seed=winner['random_seed'],
                    selection_hash=winner['selection_hash']
                )
                if success:
                    print(f"  Added initial winner: @{winner['username']}")
                else:
                    print(f"  Failed to add: @{winner['username']} (may already exist)")
            
            # Verify
            winners = db.get_all_winners()
            print(f"Database now has {len(winners)} winners")
        else:
            print(f"Database already initialized with {len(winners)} winners")
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()

# Initialize database on module import (works for both dev and production)
init_database_with_winners()

def get_est_now():
    """Get current time in EST/EDT"""
        est = timezone(timedelta(hours=-5))
        edt = timezone(timedelta(hours=-4))
        now_utc = datetime.now(timezone.utc)
        is_dst = now_utc.month >= 3 and now_utc.month < 11
    return now_utc.astimezone(edt if is_dst else est)

def select_winner():
    """Select winner for today - baseline qualification (1+ point)"""
    if not POINTSMARKET_ENABLED:
        return None
    
    try:
        now_est = get_est_now()
        today_str = now_est.date().isoformat()
        
        # Check if winner already exists
        existing = db.get_winner_for_date(today_str)
        if existing:
            return existing
        
        print(f"Fetching leaderboard for {today_str}...")
        users = points_scraper.get_leaderboard(limit=None)
        
        # Baseline: all users with 1+ point qualify
        qualified = [u for u in users if u.get('total_points', 0) >= 1]
        
        if not qualified:
            print("No eligible users")
            return None
        
        print(f"{len(qualified)} qualified users")
        
        # Select winner
        seed_string = f"{today_str}{datetime.now().isoformat()}{len(qualified)}"
        random_seed = int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16) % 1000000
        random.seed(random_seed)
        winner = random.choice(qualified)
        random.seed()
        
        selection_hash = hashlib.sha256(
            f"{today_str}{winner['username']}{winner['total_points']}{random_seed}".encode()
        ).hexdigest()[:16]
        
        # Save winner
        success = db.record_daily_winner(
            winner['username'],
            winner['total_points'],
            today_str,
            total_eligible=len(qualified),
            random_seed=random_seed,
            selection_hash=selection_hash
        )
        
        if success:
            print(f"Winner: @{winner['username']} ({winner['total_points']} pts)")
            return {
                'username': winner['username'],
                'points': winner['total_points'],
                'drawing_date': today_str,
                'total_eligible': len(qualified),
                'random_seed': random_seed,
                'selection_hash': selection_hash
            }
            return None
    except Exception as e:
        print(f"Error selecting winner: {e}")
        return None

def daily_scheduler():
    """Scheduler runs at 00:05 EST daily"""
    global _scheduler_running
    print("Scheduler started - will select winner at 00:05 EST daily")
    
    last_processed_date = None
    
    while _scheduler_running:
        try:
            now_est = get_est_now()
            
            # Check if it's 00:05-00:10 EST window
            if now_est.hour == 0 and 5 <= now_est.minute <= 10:
                today_str = now_est.date().isoformat()
                
                if last_processed_date != today_str:
                    with _winner_selection_lock:
                        existing = db.get_winner_for_date(today_str)
                        if not existing:
                            print(f"Selecting winner for {today_str}...")
                            time.sleep(300)  # Wait 5 min for PointsMarket update
                            select_winner()
                        last_processed_date = today_str
            elif now_est.hour > 0:
                last_processed_date = None
            
            time.sleep(60)
        except Exception as e:
            print(f"Scheduler error: {e}")
            time.sleep(60)
            
@app.route('/')
def index():
    """Main page - shows qualified users and current winner"""
    if not POINTSMARKET_ENABLED:
        return "PointsMarket integration not available", 404
    
    try:
        # Get qualified users (all with 1+ point) - ALL users
        users = points_scraper.get_leaderboard(limit=None)
        qualified = [u for u in users if u.get('total_points', 0) >= 1]
        qualified.sort(key=lambda x: x.get('total_points', 0), reverse=True)
        
        # Add ranks
        for idx, u in enumerate(qualified, 1):
            u['rank'] = idx
        
        # Calculate next midnight EST (00:05)
        now_est = get_est_now()
        # Calculate next 00:05 EST
        # If it's before 00:05 today, next is today. Otherwise tomorrow.
        if now_est.hour == 0 and now_est.minute < 5:
            # Before 00:05 today, so next is today at 00:05
            next_midnight = now_est.replace(hour=0, minute=5, second=0, microsecond=0)
                else:
            # Already past 00:05 today, so next is tomorrow
            next_midnight = (now_est + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
        
        # Get current winner
        current_winner = db.get_current_daily_winner()
        
        # Get all winners for the leaderboard - ensure we have a list
        try:
            all_winners = db.get_all_winners()
            if all_winners is None:
                all_winners = []
            
            # Sort by selected_at if available, otherwise drawing_date
            if all_winners:
                def sort_key(w):
                    selected = w.get('selected_at') or ''
                    drawing = w.get('drawing_date') or ''
                    return selected if selected else drawing
                all_winners = sorted(all_winners, key=sort_key)
            
            print(f"Rendering page with {len(all_winners)} winners")
            if all_winners:
                print(f"  First winner: @{all_winners[0].get('username', 'unknown')} - {all_winners[0].get('drawing_date', 'N/A')}")
                print(f"  All winner usernames: {[w.get('username') for w in all_winners]}")
        except Exception as e:
            print(f"Error getting winners: {e}")
            import traceback
            traceback.print_exc()
            all_winners = []
        
        return render_template('index.html',
                             qualified_users=qualified,
                             total_qualified=len(qualified),
                             next_reset=next_midnight.isoformat(),
                             current_winner=current_winner,
                             all_winners=all_winners)
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/current_winner')
def api_current_winner():
    """Get current winner with RNG details"""
        winner = db.get_current_daily_winner()
        if winner:
            return jsonify({
                'success': True,
                'winner': winner,
            'total_eligible': winner.get('total_eligible'),
                'random_seed': winner.get('random_seed'),
                'selection_hash': winner.get('selection_hash')
        })
    return jsonify({'success': False, 'winner': None})

@app.route('/api/all_winners')
def api_all_winners():
    """Get all winners"""
    winners = db.get_all_winners()
    return jsonify({'success': True, 'winners': winners, 'total': len(winners)})

@app.route('/api/qualified')
def api_qualified():
    """Get qualified users"""
    if not POINTSMARKET_ENABLED:
        return jsonify({'error': 'Not available'}), 404
    
    users = points_scraper.get_leaderboard(limit=None)
    qualified = [{'username': u['username'], 'total_points': u.get('total_points', 0), 'rank': idx+1}
                 for idx, u in enumerate(sorted([u for u in users if u.get('total_points', 0) >= 1],
                                                 key=lambda x: x.get('total_points', 0), reverse=True), 1)]
    return jsonify({'success': True, 'qualified': qualified, 'total': len(qualified)})

@app.route('/api/check_qualification')
def api_check_qualification():
    """Check if a specific user qualifies and return detailed PointsMarket stats"""
    if not POINTSMARKET_ENABLED:
        return jsonify({'error': 'Not available'}), 404
    
    username = request.args.get('username', '').strip().replace('@', '')
    if not username:
        return jsonify({'success': False, 'error': 'Username required'}), 400
    
    try:
        users = points_scraper.get_leaderboard(limit=None)
        user = next((u for u in users if u['username'].lower() == username.lower()), None)
        
        if user:
            points = user.get('total_points', 0)
            qualifies = points >= 1
            
            # Get last transaction/tweet that earned points
            last_tweet = None
            try:
                transactions = points_scraper.get_user_transactions(username)
                if transactions:
                    # Find the most recent transaction that earned points
                    for trans in sorted(transactions, key=lambda x: x.get('created_at', ''), reverse=True):
                        if trans.get('points', 0) > 0 or trans.get('type') == 'earned':
                            last_tweet = {
                                'text': trans.get('description', trans.get('text', '')),
                                'tweet_id': trans.get('tweet_id', ''),
                                'created_at': trans.get('created_at', ''),
                                'points': trans.get('points', 1)
                            }
                            break
            except Exception as e:
                print(f"Error fetching transactions for {username}: {e}")
            
            # Return detailed stats from PointsMarket
            return jsonify({
                'success': True,
                'username': user['username'],
                'total_points': points,
                'rank': user.get('rank', 0),
                'upvotes': user.get('upvotes', 0),
                'downvotes': user.get('downvotes', 0),
                'transactions': user.get('transactions', 0),
                'badges': user.get('badges', []),
                'last_tweet': last_tweet,
                'qualifies': qualifies,
                'message': f"@{user['username']} {'✅ QUALIFIED' if qualifies else '❌ NOT QUALIFIED'} ({points} points)"
            })
        else:
            return jsonify({
                'success': False,
                'username': username,
                'qualifies': False,
                'message': f"@{username} not found on PointsMarket.io"
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/select_winner', methods=['POST'])
def api_select_winner():
    """Manually trigger winner selection"""
    with _winner_selection_lock:
        result = select_winner()
        if result:
            return jsonify({'success': True, 'winner': result})
        return jsonify({'success': False, 'error': 'Failed or already exists'}), 400

# Start scheduler
if POINTSMARKET_ENABLED:
    _scheduler_running = True
    _scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
    _scheduler_thread.start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
