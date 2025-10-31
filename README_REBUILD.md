# Points Lotto - Clean Rebuild

A simple 24-hour lottery system that selects winners daily from PointsMarket.io users.

## How It Works

### System Overview
1. **Qualification**: All users with 1+ point on PointsMarket.io qualify (baseline mode)
2. **Selection**: Winner chosen randomly at **00:05 EST** daily
3. **Database**: Simple SQLite database stores one winner per day
4. **Display**: Shows current winner, qualified users leaderboard, and all-time winners ticker

### Components

#### `app.py` - Main Application
- Flask web server
- Scheduler runs in background thread
- Checks every minute for 00:05 EST window
- Waits 5 minutes after midnight for PointsMarket update
- Selects winner if none exists for today

#### `database_clean.py` - Database Layer
- Simple schema: `daily_winners` table
- One winner per day (date is UNIQUE)
- Tracks: username, points, date, seed, hash for verification

#### `templates/index.html` - UI
- Styled like PointsMarket.io (dark theme, clean design)
- Shows:
  - Winners ticker (scrolling feed at top)
  - Stats cards (qualified users, current winner)
  - Leaderboard (top 100 qualified users)
  - Current winner card
  - Countdown to next drawing

### API Endpoints
- `GET /` - Main page with leaderboard
- `GET /api/current_winner` - Get today's winner
- `GET /api/all_winners` - Get all winners (for ticker)
- `GET /api/qualified` - Get qualified users list
- `POST /api/select_winner` - Manually trigger selection

### Winner Selection Process
1. Fetch fresh leaderboard from PointsMarket.io
2. Filter users with 1+ point (baseline qualification)
3. Generate random seed from date + timestamp + count
4. Select random winner from qualified pool
5. Save to database with verification hash
6. Mark as current winner

### Initial Winners (Seeded)
- `@noobysol` - 2025-10-30 (4 points)
- `@doomercorp` - 2025-10-31 (5 points) - Current

### Deployment
1. Push to GitHub (already done)
2. Render auto-deploys from main branch
3. Run `python seed_winners.py` on first deploy (or manually via API)
4. Scheduler starts automatically

### Files Structure
```
├── app.py                 # Main Flask app
├── database_clean.py     # Clean database layer
├── templates/
│   └── index.html        # PointsMarket.io styled UI
├── seed_winners.py       # Seed initial winners
├── pointsmarket_scraper.py # PointsMarket.io integration
└── requirements.txt      # Dependencies
```

### Key Features
✅ Clean, simple codebase (no bloat)
✅ 24-hour drawings at 00:05 EST
✅ Baseline qualification (1+ point)
✅ Wall of Fame ticker (all winners)
✅ PointsMarket.io styling
✅ Automatic scheduler
✅ Winner verification (seed + hash)

