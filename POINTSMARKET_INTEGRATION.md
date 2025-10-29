# PointsMarket.io Integration Guide

This guide explains how to integrate PointsMarket.io data with your Twitter Points Lottery System.

## Overview

The PointsMarket.io integration allows you to:
- Fetch user point balances from PointsMarket.io
- Verify if users have sufficient points to qualify for your lottery
- Sync qualified users from the PointsMarket leaderboard
- Track external points alongside your internal lottery system

## Files Added

1. **`pointsmarket_scraper.py`** - Web scraper for PointsMarket.io
2. **`points_integration.py`** - Integration layer to sync data with your database
3. **`sync_pointsmarket.py`** - Script to manually sync data
4. **Database updates** - Added `external_points` and `points_source` columns

## Installation

Install the additional dependencies:

```bash
pip install -r requirements.txt
```

This will install `beautifulsoup4` and `lxml` for web scraping.

## Usage

### Option 1: Sync from PointsMarket Leaderboard

Sync users who have sufficient points from the PointsMarket leaderboard:

```bash
python sync_pointsmarket.py --leaderboard --min-points 100
```

This will:
- Fetch the top users from PointsMarket.io leaderboard
- Filter users with at least 100 points
- Add them to your lottery database
- Make them eligible for future lotteries

### Option 2: Sync Specific Users

Sync specific users by their usernames:

```bash
python sync_pointsmarket.py --users @user1 @user2 @user3
```

This is useful when you want to manually add specific users who you know have PointsMarket points.

### Option 3: Sync Existing Lottery Participants

Sync points data for users already in your lottery system:

```bash
python sync_pointsmarket.py --existing
```

This will update your existing users with their current PointsMarket.io point balances.

## Integration Methods

### Method 1: Qualification Check

Check if a user qualifies based on their PointsMarket points:

```python
from points_integration import PointsMarketIntegration

integration = PointsMarketIntegration()
integration.set_min_points_required(100)  # Users need at least 100 points

# Check if a user qualifies
if integration.check_user_qualification('@username'):
    print("User qualifies for lottery!")
```

### Method 2: Sync Single User

Sync points data for a specific user:

```python
from points_integration import PointsMarketIntegration

integration = PointsMarketIntegration()
success = integration.sync_user_data('@username')

if success:
    print("User data synced successfully!")
```

### Method 3: Sync Leaderboard

Automatically sync qualified users from the leaderboard:

```python
from points_integration import PointsMarketIntegration

integration = PointsMarketIntegration()
results = integration.sync_qualified_leaderboard(min_points=100)

print(f"Synced {results['successful_syncs']} qualified users")
```

## How It Works

### 1. PointsMarket.io Scraper (`pointsmarket_scraper.py`)

The scraper uses two approaches:
- **API Access**: Attempts to fetch data from PointsMarket.io's API endpoints
- **Web Scraping**: Falls back to parsing HTML if API is not available

The scraper can fetch:
- User point balances
- User rankings
- Transaction history
- Leaderboard data
- Distributor information

### 2. Integration Layer (`points_integration.py`)

The integration layer:
- Connects to your existing SQLite database
- Syncs external points data
- Updates user records with `external_points` and `points_source`
- Provides bulk sync capabilities

### 3. Database Schema

New columns added to the `users` table:
- `external_points` (INTEGER) - Points from PointsMarket.io
- `points_source` (TEXT) - Source of the points (e.g., 'pointsmarket.io')

## Automation

### Schedule Regular Syncs

Create a scheduled task to sync PointsMarket data regularly:

```python
import schedule
import time

def sync_pointsmarket():
    integration = PointsMarketIntegration()
    results = integration.sync_qualified_leaderboard(min_points=50)
    print(f"Daily sync complete: {results}")

# Schedule daily sync at 2 AM
schedule.every().day.at("02:00").do(sync_pointsmarket)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Integrate with Your Lottery

Modify your lottery engine to consider external points:

```python
# In lottery_engine.py or similar
def get_eligible_users_for_lottery_with_external_points(self, keyword_id: int, min_external_points: int = 0):
    """Get eligible users including external points qualification"""
    # Your existing query
    eligible_users = self.db.get_eligible_users_for_lottery(keyword_id)
    
    # Filter by external points if configured
    if min_external_points > 0:
        from points_integration import PointsMarketIntegration
        integration = PointsMarketIntegration()
        
        qualified = []
        for user in eligible_users:
            if integration.check_user_qualification(user['username'], min_external_points):
                qualified.append(user)
        
        return qualified
    
    return eligible_users
```

## Rate Limiting

The scraper includes built-in rate limiting to be respectful to PointsMarket.io:
- Default delay of 1 second between requests
- Configurable delay in bulk operations
- Graceful error handling

## Troubleshooting

### Issue: "No data found for user"

**Solution**: The user may not have a PointsMarket.io account, or the username format is incorrect. Try with and without the '@' symbol.

### Issue: Rate limit errors

**Solution**: Increase the delay between requests:

```python
results = integration.bulk_sync_users(usernames, delay=2.0)  # 2 second delay
```

### Issue: Database errors

**Solution**: Ensure your database has the new columns. Run the updated `database.py` to add the columns:

```python
from database import DatabaseManager
db = DatabaseManager()  # This will update the schema
```

## API vs Web Scraping

PointsMarket.io doesn't have a public API, so the scraper uses web scraping. If PointsMarket.io adds an API in the future:
1. Add API credentials to your `.env` file
2. Update `pointsmarket_scraper.py` to use the API first
3. Fall back to web scraping if API is unavailable

## Privacy and Compliance

- Only sync data that users have publicly available on PointsMarket.io
- Respect rate limits and don't overload their servers
- Consider caching data to minimize requests
- Be transparent about data collection

## Future Enhancements

Potential improvements:
1. Real-time sync via webhooks (if PointsMarket adds them)
2. Caching user data to reduce API calls
3. Batch processing for large-scale syncs
4. Integration with other points platforms
5. Automatic sync based on lottery schedules

## Support

For issues or questions:
1. Check the console output for error messages
2. Verify PointsMarket.io is accessible
3. Ensure your database is updated with new columns
4. Test with a single user first before bulk operations

