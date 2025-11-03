from database import DatabaseManager

db = DatabaseManager()
winners = db.get_all_winners()

print(f'\nTotal winners: {len(winners)}\n')
for i, w in enumerate(winners, 1):
    print(f"{i}. @{w['username']} - Date: {w['drawing_date']} - Points: {w['points']}")

