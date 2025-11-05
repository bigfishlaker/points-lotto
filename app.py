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
            print("Database empty - loading winners from backup file...")
            import json
            import os
            
            # Try to load from winners_backup.json first
            backup_file = 'winners_backup.json'
            initial_winners = []
            
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, 'r') as f:
                        initial_winners = json.load(f)
                    print(f"✅ Loaded {len(initial_winners)} winners from {backup_file}")
                except Exception as e:
                    print(f"⚠️  Failed to load {backup_file}: {e}")
                    initial_winners = []
            
            # Fallback to hardcoded winners if backup doesn't exist or is empty
            if not initial_winners:
                print("Using hardcoded initial winners as fallback...")
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
            
            # Verify and update backup file
            winners = db.get_all_winners()
            print(f"Database now has {len(winners)} winners")
            
            # Auto-update backup file after loading winners
            try:
                import json
                backup_data = []
                for w in winners:
                    backup_data.append({
                        'username': w.get('username'),
                        'points': w.get('points'),
                        'drawing_date': w.get('drawing_date'),
                        'total_eligible': w.get('total_eligible'),
                        'random_seed': w.get('random_seed'),
                        'selection_hash': w.get('selection_hash')
                    })
                with open('winners_backup.json', 'w') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)
                print(f"✅ Updated winners_backup.json with {len(backup_data)} winners")
            except Exception as e:
                print(f"⚠️  Failed to update backup file: {e}")
        else:
            print(f"Database already initialized with {len(winners)} winners")
        
        # Restore missing winners from backup file instead of reselecting
        # This prevents reselection of winners that were already chosen
        import json
        import os
        import hashlib
        
        backup_file = 'winners_backup.json'
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r') as f:
                    backup_winners = json.load(f)
                
                existing_winners = db.get_all_winners()
                existing_dates = {w['drawing_date'] for w in existing_winners}
                
                # Find missing winners in backup
                missing_from_backup = []
                for backup_winner in backup_winners:
                    date = backup_winner.get('drawing_date')
                    if date and date not in existing_dates:
                        missing_from_backup.append(backup_winner)
                
                if missing_from_backup:
                    print(f"🔍 Found {len(missing_from_backup)} missing winners in backup file, restoring...")
                    conn = sqlite3.connect(db.db_path)
                    cursor = conn.cursor()
                    
                    for winner in missing_from_backup:
                        date = winner['drawing_date']
                        username = winner['username']
                        points = winner['points']
                        
                        # Double-check if it exists
                        cursor.execute('SELECT id FROM daily_winners WHERE drawing_date = ?', (date,))
                        if cursor.fetchone():
                            continue
                        
                        # Generate selection_hash if not provided
                        selection_hash = winner.get('selection_hash')
                        if not selection_hash:
                            hash_input = f"{date}{username}{points}{winner.get('random_seed', 0)}"
                            selection_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
                        
                        # Insert missing winner - but NEVER overwrite existing
                        try:
                            cursor.execute('''
                                INSERT INTO daily_winners (winner_username, winner_points, drawing_date, drawing_period, is_current, total_eligible, random_seed, selection_hash)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                username,
                                points,
                                date,
                                date,
                                0,  # Will update current winner separately
                                winner.get('total_eligible'),
                                winner.get('random_seed'),
                                selection_hash
                            ))
                            print(f"  ✅ Restored from backup: @{username} ({date}, {points} pts)")
                        except sqlite3.IntegrityError as e:
                            # UNIQUE constraint violation - winner already exists, don't overwrite
                            cursor.execute('SELECT winner_username FROM daily_winners WHERE drawing_date = ?', (date,))
                            existing = cursor.fetchone()
                            if existing:
                                print(f"  🛡️ SKIPPED: Winner already exists for {date}: @{existing[0]} - not overwriting")
                            else:
                                print(f"  ⚠️  IntegrityError restoring @{username}: {e}")
                        except sqlite3.Error as e:
                            print(f"  ⚠️  Failed to restore @{username}: {e}")
                    
                    # Set most recent winner as current
                    cursor.execute('UPDATE daily_winners SET is_current = 0 WHERE 1=1')
                    cursor.execute('''
                        UPDATE daily_winners 
                        SET is_current = 1 
                        WHERE id = (SELECT id FROM daily_winners ORDER BY COALESCE(selected_at, drawing_date) DESC LIMIT 1)
                    ''')
                    conn.commit()
                    conn.close()
                    print(f"✅ Restored {len(missing_from_backup)} winners from backup")
            except Exception as e:
                print(f"⚠️  Failed to restore from backup file: {e}")
                import traceback
                traceback.print_exc()
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
        # CRITICAL: First check if winner already exists for this EXACT date - NEVER reselect
        # This is the PRIMARY check - only ONE winner per 24-hour period (by drawing_date)
        existing = db.get_winner_for_date(drawing_date)
        if existing:
            print(f"BLOCKED: Winner already exists for {drawing_date}: @{existing['username']} - skipping selection")
            return existing
        
        # Additional safety check: Also check by period (for backwards compatibility)
        # But drawing_date is the definitive check for one-per-day
        period_check = db.get_winner_for_period(drawing_date)
        if period_check and period_check.get('drawing_date') == drawing_date:
            print(f"BLOCKED: Winner found by period for {drawing_date}: @{period_check['username']} - skipping selection")
            return period_check
        
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
            
            # Auto-update backup file when new winner is saved
            try:
                import json
                all_winners_updated = db.get_all_winners()
                backup_data = []
                for w in all_winners_updated:
                    backup_data.append({
                        'username': w.get('username'),
                        'points': w.get('points'),
                        'drawing_date': w.get('drawing_date'),
                        'total_eligible': w.get('total_eligible'),
                        'random_seed': w.get('random_seed'),
                        'selection_hash': w.get('selection_hash')
                    })
                with open('winners_backup.json', 'w') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)
                print(f"✅ Auto-updated winners_backup.json ({len(backup_data)} winners)")
            except Exception as e:
                print(f"⚠️  Failed to update backup file: {e}")
            
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
    """Scheduler runs at 00:05 EST daily with improved reliability"""
    global _scheduler_running
    print("Scheduler started - will select winner at 00:05 EST daily")
    
    last_processed_date = None
    last_check_hour = None
    
    while _scheduler_running:
        try:
            now_est = get_est_now()
            today_str = now_est.date().isoformat()
            current_hour = now_est.hour
            current_minute = now_est.minute
            
            # Expanded window: 00:05-00:15 EST (10 minutes instead of 5)
            # Also check if we're past midnight and haven't processed today yet
            should_process = False
            
            if current_hour == 0 and 5 <= current_minute <= 15:
                # Within the selection window
                should_process = True
            elif current_hour == 0 and current_minute < 5:
                # Before 00:05, wait until window opens
                pass
            elif current_hour == 0 and current_minute > 15:
                # Past window, but check if we missed it
                existing = db.get_winner_for_date(today_str)
                if not existing:
                    print(f"⚠️  Missed selection window for {today_str}, attempting now...")
                    should_process = True
            
            if should_process and last_processed_date != today_str:
                with _winner_selection_lock:
                    # CRITICAL: Double-check winner doesn't exist before selecting
                    existing = db.get_winner_for_date(today_str)
                    if existing:
                        print(f"✅ Winner already exists for {today_str}: @{existing['username']} - skipping selection")
                        last_processed_date = today_str
                    elif not existing:
                        print(f"🎰 Selecting winner for {today_str} at {now_est.strftime('%H:%M:%S')} EST...")
                        
                        # Wait 5 minutes for PointsMarket update, but do it BEFORE checking window
                        # Calculate time until 00:05 if we're before it
                        if current_hour == 0 and current_minute < 5:
                            wait_seconds = (5 - current_minute) * 60 - now_est.second
                            if wait_seconds > 0:
                                print(f"⏳ Waiting {wait_seconds} seconds until 00:05 EST...")
                                time.sleep(wait_seconds)
                        
                        # Additional wait for PointsMarket to update (reduced from 5 min to 2 min)
                        print("⏳ Waiting 2 minutes for PointsMarket to update...")
                        time.sleep(120)
                        
                        # Retry logic for winner selection
                        max_retries = 3
                        retry_delay = 30  # 30 seconds between retries
                        winner_selected = False
                        
                        for attempt in range(max_retries):
                            try:
                                print(f"🔄 Attempt {attempt + 1}/{max_retries} to select winner...")
                                result = select_winner()
                                if result:
                                    print(f"✅ Winner selected successfully: @{result['username']} ({result['points']} pts)")
                                    winner_selected = True
                                    break
                                else:
                                    print(f"⚠️  Attempt {attempt + 1} failed - no winner returned")
                                    if attempt < max_retries - 1:
                                        print(f"⏳ Retrying in {retry_delay} seconds...")
                                        time.sleep(retry_delay)
                            except Exception as e:
                                print(f"❌ Error during winner selection (attempt {attempt + 1}): {e}")
                                import traceback
                                traceback.print_exc()
                                if attempt < max_retries - 1:
                                    print(f"⏳ Retrying in {retry_delay} seconds...")
                                    time.sleep(retry_delay)
                        
                        if not winner_selected:
                            print(f"❌ Failed to select winner after {max_retries} attempts for {today_str}")
                            # Don't mark as processed so we can retry later
                            continue
                        
                        last_processed_date = today_str
                    else:
                        print(f"✅ Winner already exists for {today_str}: @{existing['username']}")
                        last_processed_date = today_str
            
            # Reset tracking when we move to a new hour (but keep last_processed_date for the day)
            if last_check_hour is not None and current_hour != last_check_hour:
                if current_hour > 0 and last_processed_date == today_str:
                    # New hour after processing, keep tracking
                    pass
            
            last_check_hour = current_hour
            
            # Check every 30 seconds for more responsive selection
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ Scheduler error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)
            
@app.route('/')
def index():
    """Main page - shows qualified users and current winner"""
    if not POINTSMARKET_ENABLED:
        return "PointsMarket integration not available", 404
    
    try:
        # Get qualified users (all with 1+ point) - ALL users
        print("Fetching leaderboard from PointsMarket...")
        try:
            users = points_scraper.get_leaderboard(limit=None)
            if users is None:
                print("⚠️  get_leaderboard returned None")
                users = []
            elif not isinstance(users, list):
                print(f"⚠️  get_leaderboard returned non-list: {type(users)}")
                users = []
            else:
                print(f"✅ Fetched {len(users)} users from PointsMarket")
        except Exception as e:
            print(f"❌ Error fetching leaderboard: {e}")
            import traceback
            traceback.print_exc()
            users = []
        
        # Filter for users with 1+ points (qualification requirement)
        qualified = [u for u in users if u.get('total_points', 0) >= 1]
        print(f"Found {len(qualified)} qualified users (1+ points) out of {len(users)} total users")
        
        if len(qualified) == 0 and len(users) > 0:
            print(f"⚠️  No qualified users found, but {len(users)} total users fetched")
            print(f"   Sample user: {users[0] if users else 'N/A'}")
        
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
            print("⚠️  WARNING: No qualified users to display!")
        
        print(f"Rendering page with {len(qualified)} qualified users")
        
        return render_template(
            'index.html',
            qualified_users=qualified,
            total_qualified=len(qualified),
            next_reset=next_midnight.isoformat(),
            current_winner=current_winner,
            all_winners=all_winners or [],
            api_error=None if qualified or not users else "Unable to fetch users from PointsMarket. Please try again later."
        )
    except Exception as e:
        print(f"❌ Error in index route: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            'index.html',
            qualified_users=[],
            total_qualified=0,
            next_reset=None,
            current_winner=None,
            all_winners=[],
            api_error=f"Error loading page: {str(e)}"
        )


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

def check_and_select_missing_winners():
    """Check for missing winners on startup and select them - but NEVER reselect existing winners"""
    if not POINTSMARKET_ENABLED:
        return
    
    print("🔍 Checking for missing winners on startup...")
    try:
        now_est = get_est_now()
        today_str = now_est.date().isoformat()
        
        # Use lock to prevent race condition with scheduler
        with _winner_selection_lock:
            # CRITICAL: Check if today's winner is missing - NEVER reselect if exists
            today_winner = db.get_winner_for_date(today_str)
            if today_winner:
                print(f"✅ Today's winner already exists: @{today_winner['username']} - skipping selection")
            elif not today_winner:
                print(f"⚠️  No winner found for today ({today_str}), attempting selection...")
                result = select_winner()
                if result:
                    print(f"✅ Selected today's winner: @{result['username']} ({result['points']} pts)")
                else:
                    print(f"⚠️  Could not select winner for {today_str} - scheduler will retry")
            
            # Check yesterday's winner (in case app was down) - but NEVER reselect if exists
            yesterday = (now_est - timedelta(days=1)).date().isoformat()
            yesterday_winner = db.get_winner_for_date(yesterday)
            if yesterday_winner:
                print(f"✅ Yesterday's winner already exists: @{yesterday_winner['username']} - skipping selection")
            elif not yesterday_winner:
                print(f"⚠️  No winner found for yesterday ({yesterday}), attempting selection...")
                result = select_winner_for_date(yesterday)
                if result:
                    print(f"✅ Selected yesterday's winner: @{result['username']} ({result['points']} pts)")
        
    except Exception as e:
        print(f"❌ Error checking for missing winners: {e}")
        import traceback
        traceback.print_exc()

# Check for missing winners on startup
if POINTSMARKET_ENABLED:
    check_and_select_missing_winners()

# Start scheduler
if POINTSMARKET_ENABLED:
    _scheduler_running = True
    _scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
    _scheduler_thread.start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
