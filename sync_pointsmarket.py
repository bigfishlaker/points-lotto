"""
Script to sync PointsMarket.io data with the lottery system
Usage: python sync_pointsmarket.py
"""
from points_integration import PointsMarketIntegration
import argparse

def main():
    parser = argparse.ArgumentParser(description='Sync PointsMarket.io data with lottery system')
    parser.add_argument('--min-points', type=int, default=0, 
                       help='Minimum points required for users to qualify')
    parser.add_argument('--leaderboard', action='store_true',
                       help='Sync from leaderboard')
    parser.add_argument('--users', nargs='+', 
                       help='Specific usernames to sync')
    parser.add_argument('--existing', action='store_true',
                       help='Sync existing lottery participants')
    
    args = parser.parse_args()
    
    # Initialize integration
    integration = PointsMarketIntegration()
    integration.set_min_points_required(args.min_points)
    
    print("PointsMarket.io Integration Starting...")
    print(f"Minimum points required: {args.min_points}")
    print("-" * 50)
    
    if args.leaderboard:
        # Sync from leaderboard
        print("\nSyncing qualified users from leaderboard...")
        results = integration.sync_qualified_leaderboard(args.min_points)
        
        print(f"\nResults:")
        print(f"  Qualified users found: {results['qualified_users_found']}")
        print(f"  Successful syncs: {results['successful_syncs']}")
        print(f"  Failed syncs: {results['failed_syncs']}")
        
    elif args.users:
        # Sync specific users
        print(f"\nSyncing specific users: {args.users}")
        results = integration.bulk_sync_users(args.users)
        
        print(f"\nResults:")
        print(f"  Total users: {results['total']}")
        print(f"  Successful: {len(results['successful'])}")
        print(f"  Failed: {len(results['failed'])}")
        
        if results['failed']:
            print(f"\nFailed users:")
            for username in results['failed']:
                print(f"  - {username}")
                
    elif args.existing:
        # Sync existing lottery participants
        print("\nSyncing existing lottery participants...")
        results = integration.sync_lottery_participants()
        
        print(f"\nResults:")
        print(f"  Total users: {results['total']}")
        print(f"  Successful: {len(results['successful'])}")
        print(f"  Failed: {len(results['failed'])}")
        
    else:
        print("\nPlease specify an action:")
        print("  --leaderboard   : Sync from PointsMarket leaderboard")
        print("  --users USER1 USER2 ... : Sync specific users")
        print("  --existing       : Sync existing lottery participants")
        print("\nExample:")
        print("  python sync_pointsmarket.py --leaderboard --min-points 100")
        print("  python sync_pointsmarket.py --users john_doe jane_smith")
    
    print("\n" + "=" * 50)
    print("Sync complete!")

if __name__ == '__main__':
    main()

