from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from datetime import datetime, timedelta, date
import threading
import time
import random
import hashlib
import os
from functools import wraps
from database import DatabaseManager
from lottery_engine import LotteryEngine
from config import Config

# Twitter monitor is optional - import only if available
try:
    from twitter_monitor import TwitterMonitor
    TWITTER_MONITOR_AVAILABLE = True
except ImportError:
    TwitterMonitor = None
    TWITTER_MONITOR_AVAILABLE = False

# Try to import flask-limiter for rate limiting
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    print("⚠️  flask-limiter not installed. Rate limiting disabled. Install with: pip install flask-limiter")

# PointsMarket integration
try:
    from points_integration import PointsMarketIntegration
    from pointsmarket_scraper import PointsMarketScraper
    POINTSMARKET_ENABLED = True
except ImportError:
    POINTSMARKET_ENABLED = False

app = Flask(__name__)
config = Config()

# Security: Require SECRET_KEY in production
if config.DEBUG is False and config.SECRET_KEY == 'your-secret-key-here':
    raise ValueError("SECRET_KEY must be set in environment variables for production deployment!")

app.config['SECRET_KEY'] = config.SECRET_KEY

# Initialize rate limiter if available
limiter = None
if LIMITER_AVAILABLE:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
    print("✅ Rate limiting enabled")
else:
    print("⚠️  Rate limiting disabled (install flask-limiter to enable)")

# Initialize components
db = DatabaseManager()
lottery_engine = LotteryEngine()

# Initialize Twitter monitor only if credentials are available and module is available
twitter_monitor = None
try:
    if TWITTER_MONITOR_AVAILABLE and TwitterMonitor and Config().TWITTER_API_KEY and Config().TWITTER_API_SECRET:
        twitter_monitor = TwitterMonitor()
except Exception as e:
    print(f"Twitter monitor not available: {e}")

# Initialize PointsMarket integration if available
if POINTSMARKET_ENABLED:
    points_integration = PointsMarketIntegration()
    points_scraper = PointsMarketScraper()

# Global variables for background tasks
monitor_thread = None
lottery_thread = None
daily_winner_scheduler_thread = None
snapshot_thread = None
_scheduler_started = False

def ensure_scheduler_started():
    """Ensure daily winner scheduler is started (only once, even with multiple workers)"""
    global daily_winner_scheduler_thread, _scheduler_started
    
    if _scheduler_started or daily_winner_scheduler_thread is not None:
        return
    
    if POINTSMARKET_ENABLED:
        print("🎯 Starting daily winner scheduler...")
        daily_winner_scheduler_thread = threading.Thread(
            target=daily_winner_scheduler,
            daemon=True
        )
        daily_winner_scheduler_thread.start()
        _scheduler_started = True
        print("✅ Daily winner scheduler running (will select winner at midnight)")

# Admin API Key authentication
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', None)

def require_api_key(f):
    """Decorator to protect admin endpoints with API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not ADMIN_API_KEY:
            return jsonify({
                'success': False,
                'message': 'Admin API not configured. Set ADMIN_API_KEY in environment.'
            }), 503
        
        # Check for API key in header or JSON body
        api_key = request.headers.get('X-API-Key')
        if not api_key and request.is_json:
            api_key = request.json.get('api_key')
        
        if api_key != ADMIN_API_KEY:
            return jsonify({
                'success': False,
                'message': 'Unauthorized. Valid API key required.'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def dashboard():
    """Main page - shows live qualified users for next drawing"""
    if not POINTSMARKET_ENABLED:
        return "PointsMarket integration not available", 404
    
    try:
        from daily_points_tracker import DailyPointsTracker
        from datetime import datetime, timedelta
        
        # Fetch FRESH live data for initial display
        current_users = points_scraper.get_leaderboard(limit=None)
        
        # Get last winner's snapshot for round-based qualification
        last_snapshot_date = db.get_last_winner_snapshot_date()
        qualified = []
        
        if last_snapshot_date:
            # Round-based: show ALL users, mark only those who gained +1 as qualified
            tracker = DailyPointsTracker()
            previous_snapshot = tracker.load_snapshot(last_snapshot_date)
            
            if previous_snapshot:
                current_dict = {u['username']: u for u in current_users}
                previous_users = previous_snapshot.get('users', {})
                
                # Check if snapshot has actual user data
                if previous_users and len(previous_users) > 0:
                    # We have a valid snapshot with user data
                    for username in current_dict:
                        current_user = current_dict[username]
                        current_points = current_user.get('total_points', 0)
                        qualifies = False
                        gain = 0
                        baseline = 0
                        
                        if username in previous_users:
                            previous_points = previous_users[username].get('total_points', 0)
                            gain = current_points - previous_points
                            baseline = previous_points
                            if gain >= 1 and current_points >= 1:
                                qualifies = True
                        else:
                            # New user
                            if current_points >= 1:
                                gain = current_points
                                qualifies = True
                        
                        qualified.append({
                            'username': username,
                            'total_points': current_points,
                            'gain': gain,
                            'baseline': baseline,
                            'qualifies': qualifies
                        })
                else:
                    # Snapshot exists but is empty - treat as baseline
                    for user in current_users:
                        current_points = user.get('total_points', 0)
                        if current_points >= 1:
                            qualified.append({
                                'username': user['username'],
                                'total_points': current_points,
                                'gain': 0,
                                'baseline': 0,
                                'qualifies': True
                            })
        else:
            # No previous snapshot - show all users with all marked as qualified for initial display
            for user in current_users:
                current_points = user.get('total_points', 0)
                if current_points >= 1:  # Only show users with at least 1 point
                    qualified.append({
                        'username': user['username'],
                        'total_points': current_points,
                        'gain': 0,
                        'baseline': 0,
                        'qualifies': True
                    })
        
        # Sort by total points and add rank numbers
        qualified.sort(key=lambda x: x.get('total_points', 0), reverse=True)
        for idx, user in enumerate(qualified, 1):
            user['rank'] = idx
        
        # Calculate next reset time
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        next_reset_iso = next_midnight.isoformat()
        
        # Get current daily winner
        current_winner = db.get_current_daily_winner()
        
        # Count how many actually qualify
        actually_qualified = sum(1 for u in qualified if u.get('qualifies', False)) if qualified else 0
        
        return render_template('qualified.html',
                             qualified_users=qualified,
                             total=actually_qualified,
                             is_baseline=is_baseline,
                             next_reset_iso=next_reset_iso,
                             current_winner=current_winner)
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/keywords')
def keywords():
    """Keywords management page"""
    active_keywords = db.get_active_keywords()
    return render_template('keywords.html', keywords=active_keywords)

@app.route('/winners')
def winners():
    """Winners history page"""
    winners = db.get_lottery_history(limit=50)
    return render_template('winners.html', winners=winners)

@app.route('/users')
def users():
    """Users page"""
    # Get all users with their stats
    conn = db.db_path
    import sqlite3
    conn = sqlite3.connect(conn)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.*, COUNT(e.id) as total_engagements, 
               SUM(e.points_awarded) as total_points_earned
        FROM users u
        LEFT JOIN engagements e ON u.id = e.user_id
        GROUP BY u.id
        ORDER BY u.total_points DESC
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    users_data = [{
        'id': user[0],
        'twitter_id': user[1],
        'username': user[2],
        'display_name': user[3],
        'is_verified': user[4],
        'total_points': user[5],
        'created_at': user[6],
        'last_active': user[7],
        'total_engagements': user[8],
        'total_points_earned': user[9]
    } for user in users]
    
    return render_template('users.html', users=users_data)

@app.route('/api/run_lottery', methods=['POST'])
@require_api_key
def api_run_lottery():
    """API endpoint to manually run lottery"""
    try:
        result = lottery_engine.manual_lottery_run()
        return jsonify({
            'success': True,
            'message': 'Lottery run completed',
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error running lottery: {str(e)}'
        })

@app.route('/api/start_monitoring', methods=['POST'])
@require_api_key
def api_start_monitoring():
    """API endpoint to start Twitter monitoring"""
    global monitor_thread
    
    if not twitter_monitor:
        return jsonify({
            'success': False,
            'message': 'Twitter API credentials not configured'
        })
    
    if monitor_thread and monitor_thread.is_alive():
        return jsonify({
            'success': False,
            'message': 'Monitoring is already running'
        })
    
    try:
        account = request.json.get('account', Config().MAIN_TWITTER_ACCOUNT)
        monitor_thread = threading.Thread(
            target=twitter_monitor.monitor_account,
            args=(account,),
            daemon=True
        )
        monitor_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Started monitoring account: {account}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error starting monitoring: {str(e)}'
        })

@app.route('/api/stop_monitoring', methods=['POST'])
@require_api_key
def api_stop_monitoring():
    """API endpoint to stop Twitter monitoring"""
    global monitor_thread
    
    if monitor_thread and monitor_thread.is_alive():
        # Note: This is a simple way to stop, in production you'd want proper thread management
        monitor_thread = None
        
        return jsonify({
            'success': True,
            'message': 'Monitoring stopped'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Monitoring is not running'
        })

@app.route('/api/start_lottery_scheduler', methods=['POST'])
@require_api_key
def api_start_lottery_scheduler():
    """API endpoint to start lottery scheduler"""
    global lottery_thread
    
    if lottery_thread and lottery_thread.is_alive():
        return jsonify({
            'success': False,
            'message': 'Lottery scheduler is already running'
        })
    
    try:
        lottery_thread = threading.Thread(
            target=lottery_engine.start_scheduler,
            daemon=True
        )
        lottery_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Lottery scheduler started'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error starting lottery scheduler: {str(e)}'
        })

@app.route('/api/reset_winners', methods=['POST'])
@require_api_key
def api_reset_winners():
    """Reset all daily winners (admin only)"""
    import sqlite3
    
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute('SELECT COUNT(*) FROM daily_winners')
        count = cursor.fetchone()[0]
        
        # Delete all winners
        cursor.execute('DELETE FROM daily_winners')
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully cleared {count} winner(s). System ready for fresh drawing.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stop_lottery_scheduler', methods=['POST'])
@require_api_key
def api_stop_lottery_scheduler():
    """API endpoint to stop lottery scheduler"""
    try:
        lottery_engine.stop_scheduler()
        return jsonify({
            'success': True,
            'message': 'Lottery scheduler stopped'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error stopping lottery scheduler: {str(e)}'
        })

@app.route('/api/stats')
def api_stats():
    """API endpoint to get current stats"""
    stats = lottery_engine.get_lottery_stats()
    next_lottery = lottery_engine.get_next_lottery_time()
    
    return jsonify({
        'stats': stats,
        'next_lottery_time': next_lottery.isoformat() if next_lottery else None,
        'monitoring_status': monitor_thread.is_alive() if monitor_thread else False,
        'scheduler_status': lottery_thread.is_alive() if lottery_thread else False,
        'twitter_configured': twitter_monitor is not None
    })

@app.route('/api/keywords')
def api_keywords():
    """API endpoint to get active keywords"""
    keywords = db.get_active_keywords()
    return jsonify(keywords)

@app.route('/api/winners')
def api_winners():
    """API endpoint to get recent winners"""
    winners = db.get_lottery_history(limit=20)
    return jsonify(winners)

@app.route('/qualified')
@app.route('/dashboard')
def qualified_users():
    """Unified page: switch between min1 and 24h gain views via ?view=..."""
    if not POINTSMARKET_ENABLED:
        return "PointsMarket integration not available", 404
    
    try:
        from daily_points_tracker import DailyPointsTracker
        from datetime import datetime, timedelta
        
        tracker = DailyPointsTracker()
        view = request.args.get('view', 'min1')  # 'min1' or 'gain24'
        
        # Compute dataset based on view
        qualified = []
        is_baseline = False
        if view == 'min1':
            # All users with >=1 point
            qualified = points_integration.get_qualified_users(min_points=1, limit=None)
        else:
            # 24h gains view
            today_str = datetime.now().strftime('%Y-%m-%d')
            yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Ensure we have today's snapshot
            today_snapshot = tracker.load_snapshot(today_str)
            if not today_snapshot:
                current_users = points_scraper.get_leaderboard(limit=None)
                tracker.save_snapshot(current_users)
                today_snapshot = tracker.load_snapshot(today_str)
            
            gains_data = tracker.get_daily_gains(min_gain=1)
            
            # If no baseline yet, show all users with note
            if gains_data.get('baseline_created'):
                is_baseline = True
                for username, user_data in today_snapshot.get('users', {}).items():
                    total_pts = user_data.get('total_points', 0)
                    # Only include users with >= 1 total points (exclude negative)
                    if total_pts >= 1:
                        qualified.append({
                            'username': username,
                            'total_points': total_pts,
                            'rank': user_data.get('rank', 0),
                            'gain': 0,
                            'yesterday_points': 0,
                            'today_points': total_pts
                        })
            elif gains_data.get('gains'):
                # Show only users who gained points AND have >= 1 total points
                for gain_info in gains_data['gains']:
                    username = gain_info['username']
                    user_data = today_snapshot.get('users', {}).get(username, {})
                    total_pts = user_data.get('total_points', gain_info['today_points'])
                    # Only include users with >= 1 total points (exclude negative)
                    if total_pts >= 1:
                        qualified.append({
                            'username': username,
                            'total_points': total_pts,
                            'rank': user_data.get('rank', 0),
                            'gain': gain_info['gain'],
                            'yesterday_points': gain_info['yesterday_points'],
                            'today_points': gain_info['today_points']
                        })
        
        # Sort by points descending
        qualified.sort(key=lambda x: x['total_points'], reverse=True)
        
        # Calculate next reset time (midnight)
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_until_reset = (next_midnight - now).total_seconds()
        
        # Get current winner
        current_winner = db.get_current_daily_winner()
        
        return render_template('qualified.html', 
                             qualified_users=qualified,
                             min_points=1,
                             total=len(qualified),
                             is_baseline=is_baseline,
                             view=view,
                             next_reset_iso=next_midnight.isoformat(),
                             current_winner=current_winner)
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/qualified')
@limiter.limit("30 per minute") if limiter else lambda f: f
def api_qualified():
    """API endpoint to get qualified users for next drawing - LIVE DATA"""
    if not POINTSMARKET_ENABLED:
        return jsonify({'error': 'PointsMarket integration not available'}), 404
    
    limit = request.args.get('limit', None, type=int)
    
    try:
        from daily_points_tracker import DailyPointsTracker
        
        # Fetch FRESH live data
        current_users = points_scraper.get_leaderboard(limit=None)
        
        # Get last winner's snapshot for round-based qualification
        last_snapshot_date = db.get_last_winner_snapshot_date()
        qualified = []
        
        if last_snapshot_date:
            # Round-based: show ALL users, mark only those who gained +1 as qualified
            tracker = DailyPointsTracker()
            previous_snapshot = tracker.load_snapshot(last_snapshot_date)
            
            if previous_snapshot:
                current_dict = {u['username']: u for u in current_users}
                previous_users = previous_snapshot.get('users', {})
                
                # Check if snapshot has actual user data
                if previous_users and len(previous_users) > 0:
                    # We have a valid snapshot with user data
                    for username in current_dict:
                        current_user = current_dict[username]
                        current_points = current_user.get('total_points', 0)
                        qualifies = False
                        gain = 0
                        baseline = 0
                        
                        if username in previous_users:
                            previous_points = previous_users[username].get('total_points', 0)
                            gain = current_points - previous_points
                            baseline = previous_points
                            if gain >= 1 and current_points >= 1:
                                qualifies = True
                        else:
                            # New user
                            if current_points >= 1:
                                gain = current_points
                                qualifies = True
                        
                        qualified.append({
                            'username': username,
                            'total_points': current_points,
                            'gain': gain,
                            'baseline': baseline,
                            'qualifies': qualifies
                        })
                else:
                    # Snapshot exists but is empty - treat as baseline
                    for user in current_users:
                        current_points = user.get('total_points', 0)
                        if current_points >= 1:
                            qualified.append({
                                'username': user['username'],
                                'total_points': current_points,
                                'gain': 0,
                                'baseline': 0,
                                'qualifies': True
                            })
        else:
            # No previous snapshot - show all users with all marked as qualified for initial display
            for user in current_users:
                current_points = user.get('total_points', 0)
                if current_points >= 1:  # Only show users with at least 1 point
                    qualified.append({
                        'username': user['username'],
                        'total_points': current_points,
                        'gain': 0,
                        'baseline': 0,
                        'qualifies': True
                    })

        # Sort by total points
        qualified.sort(key=lambda x: x.get('total_points', 0), reverse=True)
        
        # Add rank numbers
        for idx, user in enumerate(qualified, 1):
            user['rank'] = idx
        
        if limit is not None and limit > 0:
            qualified = qualified[:limit]

        # Count how many actually qualify
        actually_qualified = sum(1 for u in qualified if u.get('qualifies', False))
        
        return jsonify({
            'success': True,
            'qualified_users': qualified,
            'total': len(qualified),
            'qualified_count': actually_qualified,
            'baseline_date': last_snapshot_date
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync_pointsmarket', methods=['POST'])
@require_api_key
def api_sync_pointsmarket():
    """API endpoint to sync PointsMarket data"""
    if not POINTSMARKET_ENABLED:
        return jsonify({'error': 'PointsMarket integration not available'}), 404
    
    try:
        min_points = request.json.get('min_points', 0) if request.json else 0
        usernames = request.json.get('usernames', []) if request.json else []
        
        if usernames:
            # Sync specific users
            results = points_integration.bulk_sync_users(usernames)
        else:
            # Sync from leaderboard
            results = points_integration.sync_qualified_leaderboard(min_points)
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/check_user', methods=['GET'])
def api_check_user():
    """API endpoint to check if a user qualifies"""
    if not POINTSMARKET_ENABLED:
        return jsonify({'error': 'PointsMarket integration not available'}), 404
    
    try:
        username = request.args.get('username')
        min_points = request.args.get('min_points', 0, type=int)
        
        if not username:
            return jsonify({'error': 'Username required'}), 400
        
        qualifies = points_integration.check_user_qualification(username, min_points)
        user_data = points_scraper.get_user_points(username)
        
        return jsonify({
            'success': True,
            'username': username,
            'qualifies': qualifies,
            'user_data': user_data,
            'min_points_required': min_points
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def select_daily_winner_with_fresh_data():
    """Select daily winner - fetches FRESH data first, then selects winner"""
    if not POINTSMARKET_ENABLED:
        print("❌ PointsMarket not enabled, cannot select winner")
        return None
    
    try:
        from daily_points_tracker import DailyPointsTracker
        from datetime import timezone, timedelta
        
        # Use EST for date tracking
        est = timezone(timedelta(hours=-5))
        edt = timezone(timedelta(hours=-4))
        now_utc = datetime.now(timezone.utc)
        is_dst = now_utc.month >= 3 and now_utc.month < 11
        est_offset = edt if is_dst else est
        now_est = now_utc.astimezone(est_offset)
        
        print(f"\n🎯 [{now_est.strftime('%H:%M:%S EST')}] Starting daily winner selection...")
        
        # STEP 1: Fetch FRESH data from PointsMarket
        print("📊 Fetching fresh leaderboard data from PointsMarket...")
        tracker = DailyPointsTracker()
        current_users = points_scraper.get_leaderboard(limit=None)
        print(f"✅ Fetched {len(current_users)} users")
        
        # STEP 2: Save today's snapshot (with fresh data) - using EST date
        today_str = now_est.date().isoformat()
        print(f"💾 Saving snapshot for {today_str}...")
        tracker.save_snapshot(current_users)
        today_snapshot = tracker.load_snapshot(today_str)
        
        # STEP 3: Get last winner's snapshot date (round-based qualification)
        last_snapshot_date = db.get_last_winner_snapshot_date()
        print(f"📅 Last winner's snapshot: {last_snapshot_date or 'First round'}")

        # STEP 4: Compare to last winner's snapshot to find gains since last round
        if last_snapshot_date and last_snapshot_date != today_str:
            print(f"📈 Comparing current data ({today_str}) to last round ({last_snapshot_date})...")
            previous_snapshot = tracker.load_snapshot(last_snapshot_date)
            
            if previous_snapshot:
                gains_data = {
                    'round_based': True,
                    'gains': []
                }
                
                # Compare current vs previous snapshot
                today_users = today_snapshot.get('users', {})
                previous_users = previous_snapshot.get('users', {})
                
                for username in today_users:
                    today_user = today_users[username]
                    today_points = today_user.get('total_points', 0)
                    
                    if username in previous_users:
                        previous_points = previous_users[username].get('total_points', 0)
                        gain = today_points - previous_points
                        
                        if gain >= 1:  # Must gain at least 1 point since last round
                            gains_data['gains'].append({
                                'username': username,
                                'previous_points': previous_points,
                                'today_points': today_points,
                                'gain': gain
                            })
                    else:
                        # New user since last round
                        if today_points >= 1:
                            gains_data['gains'].append({
                                'username': username,
                                'previous_points': 0,
                                'today_points': today_points,
                                'gain': today_points
                            })
            else:
                print(f"⚠️ Previous snapshot {last_snapshot_date} not found, using baseline")
                gains_data = {'baseline_created': True, 'gains': []}
        else:
            # First round or no previous snapshot
            print("📈 First round - using baseline comparison...")
            gains_data = tracker.get_daily_gains(min_gain=1)
        
        # STEP 5: Build qualified users list
        qualified = []
        
        if gains_data.get('baseline_created'):
            # First day - all users with ≥1 point
            print("📅 First round - using all users with ≥1 point")
            for username, user_data in today_snapshot.get('users', {}).items():
                total_pts = user_data.get('total_points', 0)
                if total_pts >= 1:
                    qualified.append({
                        'username': username,
                        'total_points': total_pts
                    })
        elif gains_data.get('gains'):
            # Round-based - only users who gained +1 since last winner
            print(f"📊 Found {len(gains_data['gains'])} users who gained 1+ points since last round")
            for gain_info in gains_data['gains']:
                username = gain_info['username']
                total_pts = gain_info['today_points']
                if total_pts >= 1:
                    qualified.append({
                        'username': username,
                        'total_points': total_pts
                    })
        
        if not qualified:
            print("❌ No eligible users found")
            return None
        
        print(f"✅ {len(qualified)} qualified users")
        
        # STEP 6: Check if winner already exists for today - using EST date
        drawing_date = now_est.date().isoformat()
        existing = db.get_winner_for_date(drawing_date)
        if existing:
            print(f"✅ Winner already selected for {drawing_date}: @{existing['username']}")
            return existing
        
        # STEP 7: Select winner randomly
        print("🎲 Selecting random winner...")
        seed_string = f"{drawing_date}{datetime.now().isoformat()}{len(qualified)}"
        random_seed = int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16) % 1000000
        
        random.seed(random_seed)
        winner = random.choice(qualified)
        random.seed()  # Reset seed
        
        winner_username = winner.get('username')
        winner_points = winner.get('total_points', 0)
        winner_index = qualified.index(winner)
        
        # Create verifiable hash
        selection_hash = hashlib.sha256(
            f"{drawing_date}{winner_username}{winner_points}{random_seed}{len(qualified)}".encode()
        ).hexdigest()[:16]
        
        # STEP 8: Save winner with snapshot date for next round
        success = db.record_daily_winner(
            winner_username, winner_points, drawing_date, 
            total_eligible=len(qualified),
            random_seed=random_seed,
            selection_hash=selection_hash,
            snapshot_date=today_str  # Store snapshot date for next round's comparison
        )
        
        if success:
            print(f"🏆 WINNER SELECTED: @{winner_username} ({winner_points} pts)")
            print(f"   Position: #{winner_index + 1} of {len(qualified)}")
            print(f"   Seed: {random_seed}")
            print(f"   Hash: {selection_hash}")
            return {
                'username': winner_username,
                'points': winner_points,
                'drawing_date': drawing_date,
                'total_eligible': len(qualified),
                'random_seed': random_seed,
                'selection_hash': selection_hash,
                'seed_string': seed_string,
                'winner_index': winner_index + 1
            }
        else:
            print("❌ Failed to record winner")
            return None
            
    except Exception as e:
        print(f"❌ Error selecting winner: {e}")
        import traceback
        traceback.print_exc()
        return None

# Thread lock for winner selection to prevent concurrent selections
_winner_selection_lock = threading.Lock()

def daily_winner_scheduler():
    """Background thread that selects winner automatically at midnight EST - GUARANTEED one winner per day"""
    from datetime import timezone, timedelta
    
    # EST is UTC-5, EDT is UTC-4
    est = timezone(timedelta(hours=-5))
    edt = timezone(timedelta(hours=-4))
    
    print("🕐 Daily winner scheduler started")
    print("   Will select winner at 00:05 EST (5 minutes after midnight) each day")
    print("   Waits 5 minutes after midnight for PointsMarket hourly update")
    print("   Checks every minute - waits for timer, then fetches fresh data")
    print("   🔒 Thread-safe lock ensures only ONE winner per day")
    
    last_processed_date = None
    
    while True:
        try:
            # Get current UTC time
            now_utc = datetime.now(timezone.utc)
            
            # Determine if we're in daylight saving time (roughly Mar-Nov)
            is_dst = now_utc.month >= 3 and now_utc.month < 11
            est_offset = edt if is_dst else est
            
            # Convert to EST
            now_est = now_utc.astimezone(est_offset)
            current_date = now_est.date()
            
            # Check if we're past midnight EST (00:05-00:10 window for fairness - wait for PointsMarket to update)
            if now_est.hour == 0 and 5 <= now_est.minute <= 10:
                # New day detected, check if we've already processed it
                if last_processed_date != current_date:
                    # USE LOCK to prevent concurrent selections
                    with _winner_selection_lock:
                        # Double-check inside lock (another process might have selected while we waited)
                        today_str = current_date.isoformat()
                        existing = db.get_winner_for_date(today_str)
                        
                        if not existing:
                            print(f"\n⏰ MIDNIGHT EST DETECTED! {now_est.strftime('%Y-%m-%d %H:%M:%S EST')} ({now_utc.strftime('%H:%M:%S UTC')})")
                            print("⏳ Waiting 5 minutes after midnight for PointsMarket to update...")
                            print("=" * 60)
                            time.sleep(300)  # Wait 5 minutes for PointsMarket hourly update
                            print("🚀 Timer has reached zero - selecting winner NOW")
                            print("🔒 Lock acquired - ensuring single winner selection")
                            print("📊 Step 1: Fetching FRESH data from PointsMarket...")
                            print("=" * 60)
                            result = select_daily_winner_with_fresh_data()
                            if result:
                                print("=" * 60)
                                print(f"✅ Winner selection complete: @{result['username']}")
                                print("🔓 Lock released")
                                print("=" * 60)
                            else:
                                print("=" * 60)
                                print("❌ Winner selection failed or was prevented")
                                print("🔓 Lock released")
                                print("=" * 60)
                        else:
                            print(f"✅ Winner already exists for {today_str}: @{existing['username']} (no selection needed)")
                    
                    last_processed_date = current_date
            else:
                # Update last_processed_date when we're past the midnight window
                if now_est.hour > 0:
                    last_processed_date = current_date
            
            # Sleep for 60 seconds before checking again
            time.sleep(60)
            
        except Exception as e:
            print(f"❌ Error in daily winner scheduler: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)  # Wait before retrying

# Initialize winner on startup if flag is set
if os.getenv('INIT_WINNER') == 'true':
    try:
        from init_winner import init_winner
        init_winner()
    except Exception as e:
        print(f"Warning: Could not initialize winner: {e}")

def snapshot_updater():
    """Background thread that takes snapshots every 5 minutes"""
    print("📸 Starting snapshot updater (every 5 minutes)...")
    while True:
        try:
            if POINTSMARKET_ENABLED:
                print(f"📸 [{datetime.now().strftime('%H:%M:%S')}] Taking snapshot...")
                from daily_points_tracker import DailyPointsTracker
                tracker = DailyPointsTracker()
                current_users = points_scraper.get_leaderboard(limit=None)
                tracker.save_snapshot(current_users)
                print(f"✅ Snapshot saved: {len(current_users)} users")
            # Sleep for 5 minutes (300 seconds)
            time.sleep(300)
        except Exception as e:
            print(f"❌ Error in snapshot updater: {e}")
            time.sleep(60)

def ensure_snapshot_thread_started():
    """Start the snapshot updater thread"""
    global snapshot_thread
    if snapshot_thread is None:
        snapshot_thread = threading.Thread(target=snapshot_updater, daemon=True)
        snapshot_thread.start()
        print("✅ Snapshot updater thread started")

# Start background threads
# ENABLED: Automatic snapshot updates every 5 minutes
if POINTSMARKET_ENABLED:
    ensure_snapshot_thread_started()

# Start scheduler immediately when module is imported (works with gunicorn)
# Must be called after daily_winner_scheduler function is defined
# ENABLED: Automatic winner selection at midnight EST
ensure_scheduler_started()

@app.route('/api/select_winner', methods=['POST'])
@limiter.limit("5 per hour") if limiter else lambda f: f
def api_select_winner():
    """API endpoint to select a daily winner (can be called manually or by scheduler)"""
    if not POINTSMARKET_ENABLED:
        return jsonify({'error': 'PointsMarket integration not available'}), 404
    
    # FIRST: Check if winner already exists for today - prevent duplicate selections
    from datetime import date
    drawing_date = date.today().isoformat()
    existing = db.get_winner_for_date(drawing_date)
    
    if existing:
        # Winner already selected for today - return existing winner
        return jsonify({
            'success': True,
            'message': 'Winner already selected for today',
            'winner': {
                'username': existing['username'],
                'points': existing['points'],
                'drawing_date': existing['drawing_date']
            },
            'note': 'No new winner selected - current winner remains active'
        })
    
    # Use lock to prevent concurrent selections via API
    with _winner_selection_lock:
        # Double-check inside lock
        existing_check = db.get_winner_for_date(drawing_date)
        if existing_check:
            return jsonify({
                'success': True,
                'message': 'Winner already selected for today (race condition prevented)',
                'winner': {
                    'username': existing_check['username'],
                    'points': existing_check['points'],
                    'drawing_date': existing_check['drawing_date']
                }
            })
        
        # Only proceed if no winner exists
        result = select_daily_winner_with_fresh_data()
    
    if result:
        return jsonify({
            'success': True,
            'winner': {
                'username': result['username'],
                'points': result['points'],
                'drawing_date': result['drawing_date']
            },
            'total_eligible': result.get('total_eligible', 0),
            'random_seed': result.get('random_seed'),
            'selection_hash': result.get('selection_hash'),
            'seed_string': result.get('seed_string'),
            'winner_index': result.get('winner_index'),
            'selection_criteria': 'Users with ≥1 total points who gained +1 point in last 24 hours'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to select winner or no eligible users'
        }), 500

@app.route('/api/check_qualification/<username>')
@limiter.limit("20 per minute") if limiter else lambda f: f
def api_check_qualification(username):
    """API endpoint to check if a username qualifies for the daily lottery"""
    if not POINTSMARKET_ENABLED:
        return jsonify({'error': 'PointsMarket integration not available'}), 404
    
    try:
        from daily_points_tracker import DailyPointsTracker
        
        # Remove @ if present
        username = username.lstrip('@').lower()
        
        # Get current data
        tracker = DailyPointsTracker()
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # First try snapshot, but if user not found, fetch fresh data
        today_snapshot = tracker.load_snapshot(today_str)
        if not today_snapshot:
            current_users = points_scraper.get_leaderboard(limit=None)
            tracker.save_snapshot(current_users)
            today_snapshot = tracker.load_snapshot(today_str)
        
        # Check if user exists in today's data (case-insensitive lookup)
        user_data = None
        for key, value in today_snapshot.get('users', {}).items():
            if key.lower() == username:
                user_data = value
                break
        
        # If not found in snapshot, fetch fresh data from API
        if not user_data:
            print(f"User {username} not in snapshot, fetching fresh data...")
            current_users = points_scraper.get_leaderboard(limit=None)
            # Update snapshot with fresh data
            tracker.save_snapshot(current_users)
            today_snapshot = tracker.load_snapshot(today_str)
            
            # Try case-insensitive lookup again with fresh data
            for key, value in today_snapshot.get('users', {}).items():
                if key.lower() == username:
                    user_data = value
                    break
        
        if not user_data:
            # Still not found - check all usernames for partial match
            all_users = points_scraper.get_leaderboard(limit=None)
            similar = [u for u in all_users if username in u.get('username', '').lower() or u.get('username', '').lower() in username]
            if similar:
                # Build a safe suggestions string without nested f-strings
                suggestions = ", ".join(["@" + (u.get('username') or '') for u in similar[:3]])
                return jsonify({
                    'username': username,
                    'found': False,
                    'qualifies': False,
                    'reason': 'User not found. Did you mean: ' + suggestions + '?',
                    'total_points': 0,
                    'gained_in_24h': 0,
                    'similar_usernames': [u.get('username') for u in similar[:5]]
                })
            return jsonify({
                'username': username,
                'found': False,
                'qualifies': False,
                'reason': 'User not found in leaderboard. Make sure you\'re using your exact PointsMarket.io username.',
                'total_points': 0,
                'gained_in_24h': 0
            })
        
        total_points = user_data.get('total_points', 0)
        
        # Check 24h gains
        gains_data = tracker.get_daily_gains(min_gain=1)
        gained_in_24h = 0
        qualifies = False
        reason = ""
        
        if gains_data.get('baseline_created'):
            # First day - only need ≥1 total point
            qualifies = total_points >= 1
            reason = "✅ QUALIFIED! Baseline day - you have 1+ points" if qualifies else f"❌ Need at least 1 point (you have {total_points})"
        elif gains_data.get('gains'):
            # Normal day - need ≥1 total AND +1 gain in last 24h
            user_gain_info = None
            for gain in gains_data['gains']:
                if gain['username'].lower() == username:
                    user_gain_info = gain
                    break
            
            if user_gain_info:
                gained_in_24h = user_gain_info['gain']
                qualifies = total_points >= 1 and gained_in_24h >= 1
                if qualifies:
                    reason = f"✅ QUALIFIED! You have {total_points} total points and gained {gained_in_24h} point(s) in the last 24 hours"
                else:
                    if total_points < 1:
                        reason = f"❌ Need at least 1 total point (you have {total_points})"
                    else:
                        reason = f"⚠️ You have {total_points} points but need to gain +1 point in the last 24h (you gained {gained_in_24h})"
            else:
                qualifies = False
                reason = f"❌ You have {total_points} total points but didn't gain any points in the last 24 hours"
        
        return jsonify({
            'username': username,
            'found': True,
            'qualifies': qualifies,
            'reason': reason,
            'total_points': total_points,
            'gained_in_24h': gained_in_24h,
            'rank': user_data.get('rank', 0)
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'username': username,
            'qualifies': False
        }), 500

@app.route('/api/all_winners')
def api_all_winners():
    """API endpoint to get all previous daily winners"""
    try:
        conn = db.db_path
        import sqlite3
        conn_db = sqlite3.connect(conn)
        cursor = conn_db.cursor()
        
        cursor.execute('''
            SELECT winner_username, winner_points, drawing_date, selected_at, total_eligible
            FROM daily_winners
            ORDER BY drawing_date DESC
        ''')
        
        results = cursor.fetchall()
        conn_db.close()
        
        winners = []
        for result in results:
            winners.append({
                'username': result[0],
                'points': result[1],
                'drawing_date': result[2],
                'selected_at': result[3],
                'total_eligible': result[4]
            })
        
        return jsonify({
            'success': True,
            'winners': winners,
            'total': len(winners)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'winners': []
        }), 500

@app.route('/api/current_winner')
def api_current_winner():
    """API endpoint to get the current daily winner with RNG info"""
    try:
        winner = db.get_current_daily_winner()
        if winner:
            return jsonify({
                'success': True,
                'winner': winner,
                'random_seed': winner.get('random_seed'),
                'total_eligible': winner.get('total_eligible'),
                'selection_hash': winner.get('selection_hash')
            })
        else:
            return jsonify({
                'success': False,
                'winner': None
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/daily-tracking')
def daily_tracking_page():
    """Daily points tracking page"""
    from daily_points_tracker import DailyPointsTracker
    import os
    from datetime import datetime, timedelta
    
    tracker = DailyPointsTracker()
    
    # Get today's report
    today_str = datetime.now().strftime('%Y-%m-%d')
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Check if today's snapshot exists
    today_snapshot = tracker.load_snapshot(today_str)
    yesterday_snapshot = tracker.load_snapshot(yesterday_str)
    
    # Get list of available snapshots
    snapshots = []
    if os.path.exists('daily_snapshots'):
        snapshot_files = [f for f in os.listdir('daily_snapshots') if f.startswith('snapshot_') and f.endswith('.json')]
        snapshots = sorted(snapshot_files, reverse=True)
    
    # Get report data
    if today_snapshot and yesterday_snapshot:
        gains_data = tracker.get_daily_gains(min_gain=1)
    else:
        gains_data = {
            'baseline_created': True,
            'date': today_str,
            'total_users': len(today_snapshot.get('users', {})) if today_snapshot else 0
        }
    
    # Get reports
    reports = []
    if os.path.exists('.'):
        report_files = [f for f in os.listdir('.') if f.startswith('daily_report_') and f.endswith('.txt')]
        reports = sorted(report_files, reverse=True)
    
    return render_template('daily_tracking.html',
                         gains_data=gains_data,
                         snapshots=snapshots,
                         reports=reports,
                         today_str=today_str,
                         yesterday_str=yesterday_str)

if __name__ == '__main__':
    # Create templates directory and basic HTML templates
    import os
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # Scheduler already started when module was imported (works with gunicorn)
    # This block only runs if script is executed directly (not via gunicorn)
    ensure_scheduler_started()
    
    # Production: debug should be False
    # Set DEBUG=True in .env only for local development
    debug_mode = Config().DEBUG
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)


