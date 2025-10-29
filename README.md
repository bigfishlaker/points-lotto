# Twitter Points Lottery System

A lottery system that integrates with PointsMarket.io to track users who have points and qualify for your lottery.

## Quick Start

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run the Server
```bash
python app.py
```

Then open: **http://localhost:5000**

## Features

### ✅ PointsMarket.io Integration
- Fetches all users from PointsMarket.io leaderboard (910+ users)
- Tracks users with minimum points (currently set to 1+ points)
- Shows user rankings and point balances
- Search functionality to find specific users

### ✅ Web Interface
- **Main Page**: http://localhost:5000/
- **Qualified Users**: http://localhost:5000/qualified?min_points=1
- **View All Users**: Shows first 100, click "Show All Users" for all 885

### ✅ Daily Tracking
- Tracks users who gain points every 24 hours
- Compare today vs yesterday
- See who gained +1 point
- Run: `python daily_points_tracker.py`

### ✅ API Endpoints
- `GET /api/qualified?min_points=1` - Get all qualified users (JSON)
- `GET /api/check_user?username=snapsnocaps` - Check specific user
- `GET /api/stats` - System statistics

## Files

### Core Files
- `app.py` - Main Flask application
- `pointsmarket_scraper.py` - Scrapes PointsMarket.io data
- `points_integration.py` - Integrates with lottery system
- `daily_points_tracker.py` - Tracks daily point changes
- `database.py` - Database management
- `lottery_engine.py` - Lottery logic
- `show_qualified_users.py` - CLI to view qualified users
- `sync_pointsmarket.py` - Sync data from PointsMarket.io

### Configuration
- `config.py` - Configuration settings
- `env_example.txt` - Environment variables template
- `requirements.txt` - Python dependencies

## Usage Examples

### View Qualified Users
```bash
python show_qualified_users.py --min-points 1
```

### Sync PointsMarket Data
```bash
python sync_pointsmarket.py --leaderboard --min-points 50
```

### Run Daily Tracking
```bash
python daily_points_tracker.py
```

## Current Status

- **Total Users Tracked**: 910 from PointsMarket.io
- **Users with 1+ points**: 885 eligible
- **Web Server**: Running on http://localhost:5000
- **Top Users**: 
  1. @g1raffe_ - 182 points
  2. @nobsfud - 145 points
  3. @BossPenguin7 - 141 points
  4. @0x_Ali3N - 136 points
  5. @ChrisFusillo - 129 points
  6. @AihansuCrypto - 114 points
  7. **@snapsnocaps** - 107 points ✅

## Documentation

- `POINTSMARKET_INTEGRATION.md` - Full PointsMarket.io integration guide
- `run_daily_tracking.py` - Schedule daily tracking reports

## Notes

- PointsMarket.io integration requires internet connection
- All 885 users with 1+ points are eligible
- Daily snapshots saved to `daily_snapshots/` folder
- Web interface includes search functionality
