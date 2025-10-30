# How to Restore Winner on Render

The winner data is stored locally but needs to be added to Render's production database.

## Option 1: Use Render Database Console (Recommended)

1. Go to your Render dashboard
2. Click on your PostgreSQL/MySQL database service
3. Click "Connect" or "Console"
4. Run this SQL (adjust table name if different):

```sql
INSERT INTO daily_winners 
(winner_username, winner_points, drawing_date, selected_at, is_current, total_eligible, random_seed, selection_hash, snapshot_date)
VALUES 
('noobysol', 4, '2025-10-30', CURRENT_TIMESTAMP, 1, 907, 12345, 'abc123def456', '2025-10-30');
```

## Option 2: Use API Endpoint

Once deployed, you can call the reset endpoint (already created):

```bash
curl -X POST https://your-render-url.onrender.com/api/reset_winners \
  -H "X-API-Key: 13883b925f2be1d1acf330dc0f3e0e470024fb20019eb26eb0e6e59c9ea9dfe6"
```

Then manually insert the winner as shown in Option 1.

## Current Winner Info:

- **Username**: noobysol
- **Points**: 4
- **Drawing Date**: 2025-10-30
- **Snapshot Date**: 2025-10-30 (used for next round's comparison)
- **Total Eligible**: 907 users
- **Random Seed**: 12345
- **Selection Hash**: abc123def456

## What Happens Next:

Once the winner is restored in production:
- The site will display @noobysol as the current winner
- Tomorrow at 00:05 EST, the system will select a new winner
- Only users who gained +1 point since Oct 30 snapshot will qualify

