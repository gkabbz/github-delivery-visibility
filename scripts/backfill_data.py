#!/usr/bin/env python3
"""
Backfill BigQuery tables with historical PR data.

This script:
1. Collects PRs from GitHub (merged, closed, or open)
2. Generates embeddings for PR bodies
3. Loads everything to BigQuery

Usage:
    python backfill_data.py --days 90 --state all
    python backfill_data.py --days 30 --state merged
    python backfill_data.py --start-date 2024-01-01 --end-date 2024-12-31
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path so we can import from src/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.github_delivery.collector import GitHubCollector
from src.github_delivery.bigquery_loader import BigQueryLoader

# Load environment
load_dotenv()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Backfill BigQuery tables with historical PR data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backfill last 90 days (all PR states)
  python backfill_data.py --days 90

  # Backfill only merged PRs from last 30 days
  python backfill_data.py --days 30 --state merged

  # Backfill specific date range
  python backfill_data.py --start-date 2024-01-01 --end-date 2024-12-31

  # Dry run (collect but don't load)
  python backfill_data.py --days 30 --dry-run
        """
    )

    # Date range options
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        '--days',
        type=int,
        help='Number of days to backfill from today'
    )
    date_group.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD, used with --start-date)'
    )

    parser.add_argument(
        '--state',
        type=str,
        choices=['all', 'open', 'closed', 'merged'],
        default='all',
        help='PR state to collect (default: all)'
    )

    parser.add_argument(
        '--repo',
        type=str,
        help='Repository (owner/name). Defaults to GITHUB_REPOSITORY env var'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Collect PRs but do not load to BigQuery'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Configuration from environment
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ GITHUB_TOKEN not found in environment")
        print("   Add it to .env file")
        return 1

    repo = args.repo or os.getenv('GITHUB_REPOSITORY', 'mozilla/bigquery-etl')
    bq_project = os.getenv('BQ_PROJECT_ID', 'mozdata-nonprod')
    bq_dataset = os.getenv('BQ_DATASET_ID', 'analysis')
    table_prefix = os.getenv('TABLE_PREFIX', 'gkabbz_gh')

    print("\n📊 BigQuery Backfill Script")
    print("=" * 60)
    print(f"Repository: {repo}")
    print(f"BigQuery: {bq_project}.{bq_dataset}.{table_prefix}_*")
    print(f"PR State: {args.state}")

    # Calculate date range (timezone-aware)
    from datetime import timezone

    if args.days:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=args.days)
        print(f"Date Range: Last {args.days} days")
    else:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            # Make end_date exclusive by adding 1 day
            # This makes date ranges intuitive: 2025-01-01 to 2025-01-01 = entire day
            end_date = end_date + timedelta(days=1)
        else:
            end_date = datetime.now(timezone.utc)
        # Display the inclusive range for clarity
        display_end = end_date - timedelta(days=1) if args.end_date else end_date
        print(f"Date Range: {start_date.date()} to {display_end.date()}")

    print(f"Dry Run: {args.dry_run}")
    print("=" * 60)

    # Initialize collector
    print("\n1️⃣  Initializing GitHub collector...")
    collector = GitHubCollector(
        token=github_token,
        repository=repo
    )

    # Collect PRs
    print(f"\n2️⃣  Collecting PRs (state={args.state})...")
    print(f"   This may take a while for large date ranges...")

    all_prs = []

    try:
        if args.state == 'all' or args.state == 'merged':
            # Collect merged PRs
            print(f"\n   Fetching merged PRs...")
            merged_prs = collector.get_merged_prs(
                since=start_date,
                until=end_date
            )
            print(f"   ✓ Found {len(merged_prs)} merged PRs")
            all_prs.extend(merged_prs)

        if args.state == 'all' or args.state == 'open':
            # Collect open PRs
            print(f"\n   Fetching open PRs...")
            open_prs = collector.get_open_prs(limit=100)
            print(f"   ✓ Found {len(open_prs)} open PRs")
            all_prs.extend(open_prs)

        if args.state == 'closed':
            print(f"\n   ⚠️  'closed' state not directly supported by collector")
            print(f"   Fetching merged PRs instead...")
            merged_prs = collector.get_merged_prs(
                since=start_date,
                until=end_date
            )
            # Note: This gets merged PRs, which are technically closed
            print(f"   ✓ Found {len(merged_prs)} merged (closed) PRs")
            all_prs.extend(merged_prs)

        print(f"\n   📊 Total PRs collected: {len(all_prs)}")

        if not all_prs:
            print("\n   ⚠️  No PRs found in date range")
            return 0

        # Show sample
        if args.verbose:
            print("\n   Sample PRs:")
            for pr in all_prs[:5]:
                print(f"     - PR #{pr.number}: {pr.title[:50]}...")

    except Exception as e:
        print(f"\n   ❌ Error collecting PRs: {e}")
        return 1

    # Initialize counters for summary
    total_prs = 0
    total_reviews = 0
    total_files = 0
    total_labels = 0

    # Load to BigQuery (duplicate checking happens inside the loader)
    if args.dry_run:
        print("\n3️⃣  Dry run - skipping BigQuery load")
        print(f"   Would have loaded {len(all_prs)} PRs")
    else:
        print("\n3️⃣  Loading to BigQuery...")
        print("   Generating embeddings and inserting data...")
        print("   This will take several minutes...")

        try:
            loader = BigQueryLoader(
                project_id=bq_project,
                dataset_id=bq_dataset
            )

            # Load PRs with embeddings (also loads reviews, files, labels)
            # Uses MERGE to handle both inserts and updates
            stats = loader.load_pull_requests(
                repo_name=repo,
                pull_requests=all_prs
            )
            print(f"   ✓ Upserted {stats.get('prs_upserted', 0)} PRs (inserted new + updated existing)")
            print(f"   ✓ Loaded {stats.get('reviews', 0)} reviews")
            print(f"   ✓ Loaded {stats.get('files', 0)} file changes")
            print(f"   ✓ Loaded {stats.get('labels', 0)} labels")

            total_prs_upserted = stats.get('prs_upserted', 0)
            total_reviews = stats.get('reviews', 0)
            total_files = stats.get('files', 0)
            total_labels = stats.get('labels', 0)

        except Exception as e:
            print(f"\n   ❌ Error loading to BigQuery: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    print("\n" + "=" * 60)
    print("✅ Backfill complete!")
    print("=" * 60)

    # Summary
    print("\nSummary:")
    print(f"  Repository: {repo}")
    print(f"  Date Range: {start_date.date()} to {end_date.date()}")
    print(f"  PRs Collected: {len(all_prs)}")
    if not args.dry_run:
        print(f"  PRs Upserted: {total_prs_upserted}")
        print(f"  Reviews Loaded: {total_reviews}")
        print(f"  Files Loaded: {total_files}")
        print(f"  Labels Loaded: {total_labels}")

    print("\nTest it:")
    print(f'  ghoracle "What PRs were merged in the last week?"')
    print(f'  ghoracle "Find PRs about monitoring"')

    return 0


if __name__ == '__main__':
    exit(main())
