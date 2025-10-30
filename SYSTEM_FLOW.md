# Points Lotto System Flow

## Daily Winner Selection Cycle

### **Overview**
The Points Lotto system runs a **daily lottery** that selects one winner every 24 hours at midnight EST (specifically 00:05 AM EST / 05:05 UTC to allow PointsMarket.io time to update their data).

---

## 🎯 **Qualification Rules**

A user qualifies for the next drawing if they meet **BOTH** criteria:
1. **Total Points ≥ 1** - Must have at least 1 point in total
2. **Gained +1 Point in Last 24h** - Must have received at least 1 additional point since the last winner was selected

### **Special Cases:**
- **First Round (Baseline)**: If no previous winner exists, ALL users with ≥1 point automatically qualify
- **Negative/Zero Points**: Users with negative or zero points NEVER qualify

---

## 📊 **System Flow Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│                    DAY 1: INITIAL DISPLAY                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  1. Fetch live leaderboard from     │
        │     PointsMarket.io API             │
        │     → Returns all users with points │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  2. Check for previous snapshot     │
        │     → NO PREVIOUS WINNER            │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  3. BASELINE MODE:                  │
        │     → Show ALL users                │
        │     → Mark ALL as "Qualified"       │
        │     → Display on page               │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  4. Countdown to midnight           │
        │     → Timer shows time until 00:05  │
        │     → Users see live updates        │
        └─────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│             00:05 AM EST - WINNER SELECTION                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  1. Scheduler triggers at 00:05 EST │
        │     → Waits 5 min for data update   │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  2. Fetch FRESH leaderboard data    │
        │     → Get current points for ALL    │
        │     → Save snapshot to disk         │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  3. Calculate point gains           │
        │     → Compare vs previous snapshot  │
        │     → Find users with +1 point gain │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  4. Build qualified list            │
        │     → Only users with gain ≥ 1      │
        │     → AND total_points ≥ 1          │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  5. Random Number Generation        │
        │     → Create verifiable seed:       │
        │       SHA256(date + time + count)   │
        │     → Use seed to select winner     │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  6. Record winner in database       │
        │     → Save to daily_winners table   │
        │     → Include RNG audit info        │
        │     → Set is_current = 1            │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  7. Display winner on site          │
        │     → Show in header chip           │
        │     → Show RNG terminal animation   │
        │     → Add to history calendar       │
        └─────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│              DAY 2+: ONGOING QUALIFICATION                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  1. User visits the site            │
        │     → See current winner displayed  │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  2. Check if user qualifies         │
        │     → Fetch fresh leaderboard       │
        │     → Compare to last winner's      │
        │       snapshot (not just yesterday) │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  3. Display ALL users with status   │
        │     → "✓ Qualifies" for those with  │
        │       gain ≥ 1                      │
        │     → "✗ Not Qualified" for those   │
        │       without gain                  │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  4. Real-time qualification checker │
        │     → User searches their name      │
        │     → Shows if they qualify NOW     │
        │     → No need to wait until timer   │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  5. Countdown to next midnight      │
        │     → Shows time until 00:05 EST    │
        │     → Updates every second          │
        └─────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  6. Next winner selection           │
        │     → Repeat cycle from Day 1       │
        └─────────────────────────────────────┘
```

---

## 🔍 **Key Components**

### **1. Data Fetching (`pointsmarket_scraper.py`)**
- Connects to `https://www.pointsmarket.io/api/leaderboard`
- Returns JSON with user data:
  ```json
  {
    "username": "g1raffe_",
    "total_points": 182,
    "upvotes": 96,
    "downvotes": 1,
    "rank": 1
  }
  ```

### **2. Daily Snapshots (`daily_points_tracker.py`)**
- Saves user point data at specific moments
- Format: JSON files in `daily_snapshots/YYYY-MM-DD.json`
- Used for comparing point gains

### **3. Winner Selection (`app.py` - `select_daily_winner_with_fresh_data()`)**
- Fetches fresh data from PointsMarket
- Saves snapshot
- Calculates gains
- Filters qualified users
- Uses verifiable RNG to select winner
- Records winner with audit info

### **4. Scheduler (`app.py` - `daily_winner_scheduler`)**
- Background thread that runs continuously
- Checks every minute if current time is 00:05-00:10 EST
- Triggers winner selection automatically
- Prevents duplicate selections with locks

### **5. Display Page (`templates/qualified.html`)**
- Shows ALL users (not just qualified)
- Marks qualification status clearly
- Real-time countdown timer
- RNG terminal animation
- Past winners calendar
- Search functionality

---

## 🎲 **RNG Process (Auditable)**

When a winner is selected, the system:
1. Creates a verifiable seed: `SHA256(drawing_date + timestamp + total_eligible_users)`
2. Seeds Python's random number generator
3. Selects a random index from qualified users
4. Stores all details in database:
   - `random_seed`: The SHA256 hash
   - `total_eligible`: Number of qualified users
   - `selection_hash`: Verification hash
   - `snapshot_date`: Snapshot used for comparison

This makes the selection **provably fair** and **auditable**.

---

## ⚡ **Real-Time Features**

### **Live Qualification Checker**
- User searches their username
- System fetches fresh data if not in snapshot
- Instantly shows if they qualify
- No need to wait until midnight

### **Auto-Refresh**
- User list updates every 5 minutes automatically
- Countdown timer updates every second
- Winner display updates when new winner is selected

### **Automatic Winner Display**
- When timer hits 00:05 EST, scheduler selects winner
- Frontend polls every 5 seconds for 2 minutes
- Automatically shows RNG terminal when winner detected
- Winner stays displayed for 24 hours

---

## 🛡️ **Concurrency & Safety**

### **Preventing Duplicate Winners**
1. **Database UNIQUE constraint** on `drawing_date`
2. **Thread-safe lock** (`_winner_selection_lock`)
3. **Exclusive transaction** (`BEGIN EXCLUSIVE`)
4. **Check before insert** - returns existing winner if found

### **Fairness Guarantees**
1. **5-minute delay** after midnight for PointsMarket to update
2. **Round-based qualification** - compares to last winner's snapshot
3. **No negative points** - users with ≤0 points never qualify
4. **Verifiable RNG** - seed based on immutable data

---

## 📅 **Timeline Example**

```
Day 1 (Dec 1)
├─ 00:00 EST: System initialized, baseline mode
├─ 10:00 EST: User @alice has 50 points (qualifies)
├─ 12:00 EST: User @bob has 0 points (doesn't qualify)
├─ 23:59 EST: Timer shows "00:06:00 until reset"
└─ 00:05 EST: Winner selected from all baseline users

Day 2 (Dec 2)
├─ 00:06 EST: @alice won! (selected from baseline)
├─ 10:00 EST: @alice now has 60 points (+10 gained)
├─ 10:00 EST: @charlie has 5 points (new user, qualifies)
├─ 23:59 EST: Timer shows "00:06:00 until reset"
└─ 00:05 EST: Winner selected from users who gained +1

Day 3 (Dec 3)
├─ 00:06 EST: @charlie won!
├─ 10:00 EST: @alice still has 60 points (no gain)
├─ 10:00 EST: @bob gained 3 points (now qualifies)
├─ 23:59 EST: Timer shows "00:06:00 until reset"
└─ 00:05 EST: Winner selected from users who gained +1
```

---

## 🎯 **Summary**

The system ensures:
✅ **Fair selection** - Everyone with activity has a chance
✅ **Verifiable randomness** - Auditable RNG process
✅ **Live feedback** - Users know immediately if they qualify
✅ **Automatic operation** - No manual intervention needed
✅ **Round-based tracking** - Accurate point gain calculation
✅ **Transparent display** - Shows all users with clear status

