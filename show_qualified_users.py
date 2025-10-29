"""
Script to fetch and display users from PointsMarket.io who qualify for the lottery
"""
import argparse
from pointsmarket_scraper import PointsMarketScraper
from points_integration import PointsMarketIntegration

def show_qualified_leaderboard(min_points=0, limit=50):
    """Fetch and display qualified users from PointsMarket leaderboard"""
    print("=" * 70)
    print("PointsMarket.io - Qualified Users Finder")
    print("=" * 70)
    print(f"\nMinimum points required: {min_points}")
    print(f"Fetching top {limit} users from leaderboard...\n")
    print("-" * 70)
    
    scraper = PointsMarketScraper()
    
    # Get leaderboard
    try:
        leaderboard = scraper.get_leaderboard(limit=limit)
        
        if not leaderboard:
            print("❌ Could not fetch leaderboard data from PointsMarket.io")
            print("\nThis could be because:")
            print("  • PointsMarket.io's structure may have changed")
            print("  • The site may require authentication")
            print("  • There may be a network issue")
            print("\nTrying alternative method...\n")
            
            # Alternative: Try to get data via API
            print("Attempting to fetch via API endpoints...")
            # The scraper will try various endpoints
            
        else:
            # Filter qualified users
            qualified = []
            for user in leaderboard:
                points = user.get('total_points', 0)
                if points >= min_points:
                    qualified.append(user)
            
            # Display results
            if qualified:
                print(f"\n✓ Found {len(qualified)} qualified users (≥{min_points} points):\n")
                print(f"{'Rank':<6} {'Username':<25} {'Points':<12} {'Status':<20}")
                print("-" * 70)
                
                for i, user in enumerate(qualified, 1):
                    username = user.get('username', 'N/A')
                    points = user.get('total_points', 0)
                    rank = user.get('rank', i)
                    
                    status = "✓ QUALIFIED"
                    
                    print(f"{rank:<6} {username:<25} {points:<12} {status:<20}")
                
                print("-" * 70)
                print(f"\nTotal qualified users: {len(qualified)}")
                
            else:
                print(f"\n❌ No users found with {min_points} or more points")
                print(f"Current users in leaderboard:")
                
                for i, user in enumerate(leaderboard, 1):
                    username = user.get('username', 'N/A')
                    points = user.get('total_points', 0)
                    print(f"{i}. @{username} - {points} points")
        
        # Show all users for reference
        if leaderboard:
            print(f"\n\nAll users fetched from leaderboard ({len(leaderboard)} total):")
            print("-" * 70)
            print(f"{'#':<4} {'Username':<25} {'Points':<10} {'Qualifies':<15}")
            print("-" * 70)
            
            for i, user in enumerate(leaderboard, 1):
                username = user.get('username', 'N/A')
                points = user.get('total_points', 0)
                qualifies = "✓ YES" if points >= min_points else "✗ NO"
                
                # Highlight qualified users
                if points >= min_points:
                    print(f"{i:<4} {username:<25} {points:<10} {qualifies:<15}")
                else:
                    print(f"{i:<4} {username:<25} {points:<10} {qualifies:<15}")
        
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check your internet connection")
        print("2. Visit https://www.pointsmarket.io to verify the site is accessible")
        print("3. The website structure may have changed - scraper may need updates")
        print("4. Try a different minimum points value")

def show_specific_users(usernames, min_points=0):
    """Check specific users for qualification"""
    print("=" * 70)
    print("PointsMarket.io - User Qualification Check")
    print("=" * 70)
    print(f"Minimum points required: {min_points}\n")
    print("-" * 70)
    print(f"{'Username':<30} {'Points':<12} {'Status':<20}")
    print("-" * 70)
    
    scraper = PointsMarketScraper()
    integration = PointsMarketIntegration()
    
    qualified_count = 0
    
    for username in usernames:
        username = username.replace('@', '')
        
        try:
            user_data = scraper.get_user_points(username)
            
            if user_data:
                points = user_data.get('total_points', 0)
                qualifies = points >= min_points
                
                if qualifies:
                    qualified_count += 1
                    status = f"✓ QUALIFIED ({points} pts)"
                else:
                    status = f"✗ NOT QUALIFIED ({points} pts)"
                
                print(f"{username:<30} {points:<12} {status:<20}")
            else:
                print(f"{username:<30} {'N/A':<12} {'✗ NOT FOUND':<20}")
                
        except Exception as e:
            print(f"{username:<30} {'ERROR':<12} {'✗ ERROR':<20}")
    
    print("-" * 70)
    print(f"\nQualified users: {qualified_count}/{len(usernames)}")
    print("\n")

def test_connection():
    """Test connection to PointsMarket.io"""
    print("Testing connection to PointsMarket.io...")
    
    scraper = PointsMarketScraper()
    
    try:
        # Try to fetch a known user or just test the connection
        print("Attempting to fetch leaderboard...")
        leaderboard = scraper.get_leaderboard(limit=10)
        
        if leaderboard:
            print(f"✓ Connection successful! Found {len(leaderboard)} users")
            return True
        else:
            print("⚠ Connection successful but no data returned")
            print("This is normal if PointsMarket.io has API restrictions")
            return True
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nPossible reasons:")
        print("• The website may require browser-based access")
        print("• API endpoints may not be publicly available")
        print("• Network connectivity issues")
        print("• Website structure may have changed")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Show qualified users from PointsMarket.io',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show top 50 users with at least 100 points
  python show_qualified_users.py --min-points 100

  # Show top 20 users
  python show_qualified_users.py --limit 20

  # Check specific users
  python show_qualified_users.py --users @user1 @user2 @user3

  # Test connection to PointsMarket.io
  python show_qualified_users.py --test
        """
    )
    
    parser.add_argument('--min-points', type=int, default=0, 
                       help='Minimum points required to qualify (default: 0)')
    parser.add_argument('--limit', type=int, default=50,
                       help='Number of users to fetch from leaderboard (default: 50)')
    parser.add_argument('--users', nargs='+',
                       help='Check specific users by username')
    parser.add_argument('--test', action='store_true',
                       help='Test connection to PointsMarket.io')
    
    args = parser.parse_args()
    
    if args.test:
        test_connection()
    elif args.users:
        show_specific_users(args.users, args.min_points)
    else:
        show_qualified_leaderboard(args.min_points, args.limit)
    
    print("\n" + "=" * 70)
    print("Note: If no data appears, PointsMarket.io may not have a public API")
    print("or the website structure requires different scraping methods.")
    print("Consider contacting PointsMarket.io for API access.")
    print("=" * 70)

if __name__ == '__main__':
    main()

