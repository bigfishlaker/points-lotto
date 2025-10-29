# How Winner Selection Works

## Current Flow (PROBLEMATIC)

### ❌ Client-Side Timer Problem
Currently, the winner is selected **by JavaScript in the browser** when the countdown timer hits zero:

1. **Frontend Timer** (`qualified.html`):
   - JavaScript calculates time until next midnight
   - Updates countdown every second
   - When `diff <= 0`, calls `selectNewWinner()`

2. **Problem**: If no one has the page open at midnight, no winner gets selected!

### Current Selection Process
When `/api/select_winner` is called:

1. **Data Gathering**:
   - Gets today's snapshot (if exists, otherwise creates it)
   - Compares to yesterday's snapshot
   - Finds users who: **≥1 total points AND gained +1 in last 24h**
   - Creates a list of `qualified` users

2. **Winner Selection**:
   - Checks if winner already exists for today (prevents duplicate)
   - If no winner exists:
     - Creates random seed from: `date + datetime + pool_size`
     - Uses `random.choice(qualified)` to pick winner
     - Records winner in database with hash for verification

3. **Random Seed Generation**:
   ```python
   seed_string = f"{drawing_date}{datetime.now().isoformat()}{len(qualified)}"
   random_seed = int(hashlib.sha256(seed_string.encode()).hexdigest()[:8], 16) % 1000000
   ```

## What You Asked For

You want:
- ✅ System **waits** until timer hits zero
- ✅ Then **gathers fresh data** from PointsMarket
- ✅ Then selects winner from that fresh data
- ✅ All happens **automatically** even if nobody is viewing the page

## Solution: Server-Side Scheduler

I'll create a background thread that:
1. **Checks every minute** for midnight (or custom reset time)
2. **At midnight**:
   - Fetches fresh data from PointsMarket API
   - Creates today's snapshot
   - Compares to yesterday to find 24h gains
   - Selects winner from qualified users
   - Saves winner to database
3. **Runs 24/7** - independent of browser

This ensures:
- ✅ Winner always selected at reset time
- ✅ Data is fresh (just fetched)
- ✅ Works even with no visitors
- ✅ Reliable and tamper-proof

