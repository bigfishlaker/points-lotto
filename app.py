from flask import Flask, render_template, request, jsonify
from datetime import datetime, timezone, timedelta
import threading
import time
import random
import hashlib
import os
import sqlite3
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
                    'username': 'noobysol',
                    'points': 1,  # First winner gets 1 point
                    'drawing_date': '2025-10-28',
                    'selected_at': datetime(2025, 10, 28, 0, 5, 0).isoformat(),
                    'total_eligible': 900,
                    'random_seed': 67890,
                    'selection_hash': 'def456ghi789',
                },
                {
                    'username': 'doomercorp',
                    'points': 2,  # Second winner gets 2 points
                    'drawing_date': '2025-10-29',
                    'selected_at': datetime(2025, 10, 29, 0, 5, 0).isoformat(),
                    'total_eligible': 920,
                    'random_seed': 12345,
                    'selection_hash': 'abc123def456',
                },
                {
                    'username': 'ororys',
                    'points': 3,  # Third winner gets 3 points
                    'drawing_date': '2025-10-30',
                    'selected_at': datetime(2025, 10, 30, 0, 5, 0).isoformat(),
                    'total_eligible': None,  # Unknown
                    'random_seed': None,  # Unknown
                    'selection_hash': None,  # Will be generated
                },
                {
                    'username': 'alppisik',
                    'points': 4,  # Fourth winner gets 4 points
                    'drawing_date': '2025-10-31',
                    'selected_at': datetime(2025, 10, 31, 0, 5, 0).isoformat(),
                    'total_eligible': None,  # Unknown
                    'random_seed': None,  # Unknown
                    'selection_hash': None,  # Will be generated
                },
                {
                    'username': 'ebechinedu',
                    'points': 5,  # Fifth winner gets 5 points
                    'drawing_date': '2025-11-01',
                    'selected_at': datetime(2025, 11, 1, 0, 5, 0).isoformat(),
                    'total_eligible': None,  # Unknown
                    'random_seed': None,  # Unknown
                    'selection_hash': None,  # Will be generated
                }
            ]
            
            print(f"Adding {len(initial_winners)} initial winners...")
            for i, winner in enumerate(initial_winners, 1):
                try:
                    print(f"  [{i}/{len(initial_winners)}] Attempting to add @{winner['username']} ({winner['points']} pts) for {winner['drawing_date']}...")
                    success = db.record_daily_winner(
                        winner['username'],
                        winner['points'],
                        winner['drawing_date'],
                        total_eligible=winner['total_eligible'],
                        random_seed=winner['random_seed'],
                        selection_hash=winner['selection_hash']
                    )
                    if success:
                        print(f"  ✅ Added initial winner: @{winner['username']}")
                    else:
                        print(f"  ⚠️  Failed to add: @{winner['username']} (may already exist or duplicate)")
                except Exception as e:
                    print(f"  ❌ ERROR adding @{winner['username']}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Verify
            winners = db.get_all_winners()
            print(f"Database now has {len(winners)} winners")
        else:
            print(f"Database already initialized with {len(winners)} winners")
        
        # Fill in missing winners for historical dates (if PointsMarket is available)
        if POINTSMARKET_ENABLED:
            missing_dates = ['2025-10-31', '2025-11-01']
            existing_winners = db.get_all_winners()
            existing_usernames = [w['username'] for w in existing_winners]
            
            for date_str in missing_dates:
                existing = db.get_winner_for_date(date_str)
                if not existing:
                    print(f"Selecting retroactive winner for {date_str}...")
                    # Try without exclusion first (more likely to succeed)
                    winner = select_winner_for_date(date_str, exclude_usernames=None)
                    if not winner:
                        # If that fails, try with exclusion
                        winner = select_winner_for_date(date_str, exclude_usernames=existing_usernames[:3])
                    if winner:
                        existing_usernames.append(winner['username'])  # Update list to avoid duplicates
                        print(f"  ✅ Selected @{winner['username']} for {date_str} ({winner['points']} pts)")
                    else:
                        print(f"  ⚠️  Failed to select winner for {date_str} - PointsMarket API may be unavailable")
            
            # Fix any incorrectly dated winners (winner #4 should be 2025-10-31, not 2025-11-01)
            all_winners = db.get_all_winners()
            winners_by_points = {w['points']: w for w in all_winners}
            if 4 in winners_by_points and 5 in winners_by_points:
                winner_4 = winners_by_points[4]
                winner_5 = winners_by_points[5]
                # If winner #4 has wrong date, fix it
                if winner_4['drawing_date'] == '2025-11-01' and winner_5['drawing_date'] == '2025-11-01':
                    print(f"⚠️  Fixing date for winner #4 (@{winner_4['username']}): 2025-11-01 -> 2025-10-31")
                    conn = sqlite3.connect(db.db_path)
                    c = conn.cursor()
                    c.execute('UPDATE daily_winners SET drawing_date = ?, drawing_period = ? WHERE winner_username = ? AND winner_points = 4',
                              ('2025-10-31', '2025-10-31', winner_4['username']))
                    conn.commit()
                    conn.close()
                    print(f"✅ Fixed date for @{winner_4['username']}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()

def get_est_now():
    """Get current time in EST/EDT"""
    est = timezone(timedelta(hours=-5))
    edt = timezone(timedelta(hours=-4))
    now_utc = datetime.now(timezone.utc)
    is_dst = now_utc.month >= 3 and now_utc.month < 11
    return now_utc.astimezone(edt if is_dst else est)

def select_winner_for_date(drawing_date: str, exclude_usernames: list = None):
    """Select winner for a specific date - baseline qualification (1+ point)"""
    if not POINTSMARKET_ENABLED:
        return None
    
    try:
        # Check if winner already exists
        existing = db.get_winner_for_date(drawing_date)
        if existing:
            return existing
        
        print(f"Fetching leaderboard for {drawing_date}...")
        users = None
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                users = points_scraper.get_leaderboard(limit=None)
                if users and len(users) > 0:
                    break  # Success, exit retry loop
            except Exception as e:
                error_msg = str(e)
                print(f"Error fetching leaderboard (attempt {attempt + 1}/{max_retries}): {error_msg[:100]}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"All {max_retries} attempts failed")
                    return None
        
        if not users:
            print("No users returned from API")
            return None
        
        # Baseline: all users with 1+ point qualify
        qualified = [u for u in users if u.get('total_points', 0) >= 1]
        
        # Exclude already selected winners if requested (but only if we have enough users)
        if exclude_usernames and len(qualified) > len(exclude_usernames):
            qualified = [u for u in qualified if u['username'] not in exclude_usernames]
            if not qualified:
                print("All excluded users, allowing any qualified user...")
                qualified = [u for u in users if u.get('total_points', 0) >= 1]
        
        if not qualified:
            print("No eligible users after filtering")
            return None
        
        print(f"{len(qualified)} qualified users")
        
        # Select winner using date-specific seed (deterministic for historical dates)
        seed_string = f"{drawing_date}00:05:00{len(qualified)}"
        random_seed = int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16) % 1000000
        random.seed(random_seed)
        winner = random.choice(qualified)
        random.seed()
        
        # Calculate lottery points: sequential based on TOTAL winner entries count
        all_winners = db.get_all_winners()
        lottery_points = len(all_winners) + 1  # Next sequential number
        
        selection_hash = hashlib.sha256(
            f"{drawing_date}{winner['username']}{lottery_points}{random_seed}".encode()
        ).hexdigest()[:16]
        
        # Save winner with lottery points
        success = db.record_daily_winner(
            winner['username'],
            lottery_points,
            drawing_date,
            total_eligible=len(qualified),
            random_seed=random_seed,
            selection_hash=selection_hash
        )
        
        if success:
            print(f"Winner for {drawing_date}: @{winner['username']} (lottery points: {lottery_points})")
            return {
                'username': winner['username'],
                'points': lottery_points,
                'drawing_date': drawing_date,
                'total_eligible': len(qualified),
                'random_seed': random_seed,
                'selection_hash': selection_hash
            }
        return None
    except Exception as e:
        print(f"Error selecting winner for {drawing_date}: {e}")
        return None

def select_winner():
    """Select winner for today - baseline qualification (1+ point)"""
    now_est = get_est_now()
    today_str = now_est.date().isoformat()
    return select_winner_for_date(today_str)

# Initialize database on module import (works for both dev and production)
# Must be called AFTER select_winner_for_date is defined
init_database_with_winners()

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
        
        # Get all winners for the leaderboard - ensure we have a list
        try:
            all_winners = db.get_all_winners()
            if all_winners is None:
                all_winners = []
            
            # Sort by selected_at if available, otherwise drawing_date (chronological order)
            if all_winners:
                def sort_key(w):
                    selected = w.get('selected_at') or ''
                    drawing = w.get('drawing_date') or ''
                    return selected if selected else drawing
                all_winners = sorted(all_winners, key=sort_key)
            
            # Get most recent winner for current winner display (last in sorted list = most recent)
            if all_winners:
                current_winner = all_winners[-1]
            else:
                # Fallback to current winner from database if no winners yet
                current_winner = db.get_current_daily_winner()
            
            # If no current winner from database, ensure we have one from all_winners
            if not current_winner and all_winners:
                current_winner = all_winners[-1]
            
            print(f"Rendering page with {len(all_winners)} winners")
            if all_winners:
                print(f"  First winner: @{all_winners[0].get('username', 'unknown')} - {all_winners[0].get('drawing_date', 'N/A')}")
                print(f"  All winner usernames: {[w.get('username') for w in all_winners]}")
        except Exception as e:
            print(f"Error getting winners: {e}")
            import traceback
            traceback.print_exc()
            all_winners = []
        
        # Ensure qualified_users is always a list, even if empty
        if not qualified:
            qualified = []
        
        return render_template(
            'index.html',
            qualified_users=qualified,
            total_qualified=len(qualified),
            next_reset=next_midnight.isoformat(),
            current_winner=current_winner,
            all_winners=all_winners or []
        )
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/api/current_winner')
def api_current_winner():
    """Get current winner with RNG details"""
    # Try to get current winner from database first
    winner = db.get_current_daily_winner()
    
    # If no current winner (is_current=1), get the most recent winner
    if not winner:
        all_winners = db.get_all_winners()
        if all_winners:
            # Sort by date and get most recent
            def sort_key(w):
                selected = w.get('selected_at') or ''
                drawing = w.get('drawing_date') or ''
                return selected if selected else drawing
            sorted_winners = sorted(all_winners, key=sort_key)
            winner = sorted_winners[-1] if sorted_winners else None
    
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
