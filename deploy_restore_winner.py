#!/usr/bin/env python3
"""
Script to restore the winner on Render production database
Run this after deployment completes
"""

import requests
import os

# Render URL - replace with your actual Render URL
RENDER_URL = os.getenv('RENDER_URL', 'https://your-render-url.onrender.com')
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', '13883b925f2be1d1acf330dc0f3e0e470024fb20019eb26eb0e6e59c9ea9dfe6')

print("Restoring winner on production...")
print(f"Target: {RENDER_URL}")
print()

# Call the reset endpoint
response = requests.post(
    f"{RENDER_URL}/api/reset_winners",
    headers={"X-API-Key": ADMIN_API_KEY}
)

if response.status_code == 200:
    print("✅ Winners reset successfully")
else:
    print(f"❌ Failed to reset: {response.status_code}")
    print(response.text)
    exit(1)

print()
print("To restore the winner, you'll need to:")
print("1. Manually insert via Render's database console, OR")
print("2. Call /api/select_winner endpoint with proper data")
print()
print("Winner data:")
print("  Username: noobysol")
print("  Points: 4")
print("  Drawing date: 2025-10-30")
print("  Snapshot date: 2025-10-30")

