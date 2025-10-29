# Project Structure

## Core Application Files

### Main Files
- `app.py` - Flask web server (main entry point)
- `main.py` - Alternative entry point
- `config.py` - Configuration settings
- `database.py` - Database management
- `lottery_engine.py` - Lottery logic
- `twitter_monitor.py` - Twitter monitoring (requires API credentials)

### PointsMarket.io Integration
- `pointsmarket_scraper.py` - Scrapes PointsMarket.io API
- `points_integration.py` - Integrates PointsMarket data with lottery
- `show_qualified_users.py` - CLI tool to view qualified users
- `sync_pointsmarket.py` - Sync data from PointsMarket.io

### Daily Tracking
- `daily_points_tracker.py` - Track daily point gains
- `run_daily_tracking.py` - Schedule daily reports
- `daily_snapshots/` - Daily snapshots of leaderboard
- `daily_report_2025-10-29.txt` - Daily report output

### Data Files
- `lottery.db` - SQLite database
- `leaderboard.json` - Current leaderboard (910 users)
- `leaderboard.txt` - Human-readable leaderboard
- `daily_snapshots/snapshot_2025-10-29.json` - Today's snapshot

### Templates (Web Interface)
- `templates/dashboard.html` - Main dashboard
- `templates/qualified.html` - Qualified users page (with search!)
- `templates/keywords.html` - Keywords management
- `templates/users.html` - Users page
- `templates/winners.html` - Winners history

### Documentation
- `README.md` - Main documentation
- `POINTSMARKET_INTEGRATION.md` - PointsMarket integration guide
- `PROJECT_STRUCTURE.md` - This file

### Configuration
- `requirements.txt` - Python dependencies
- `env_example.txt` - Environment variables template

## Key URLs

- **Web Interface**: http://localhost:5000
- **Qualified Users**: http://localhost:5000/qualified?min_points=1
- **API**: http://localhost:5000/api/qualified?min_points=1

## What Each Script Does

- `python app.py` - Start web server
- `python show_qualified_users.py` - View qualified users in terminal
- `python sync_pointsmarket.py` - Sync PointsMarket data
- `python daily_points_tracker.py` - Track daily changes
- `python run_daily_tracking.py` - Schedule daily reports

