#!/usr/bin/env python3
"""
Test find_prs_by_date_range method.
"""

from src.github_delivery.bq_data_source import BigQueryDataSource
from datetime import datetime, timedelta, timezone

# Configuration
BQ_PROJECT_ID = "mozdata-nonprod"
BQ_DATASET_ID = "analysis"
TABLE_PREFIX = "gkabbz_gh"
REPOSITORY = "mozilla/bigquery-etl"


def main():
    print("\n🧪 Testing find_prs_by_date_range()\n")
    print("=" * 60)

    # Initialize data source
    print("\n1. Initializing BigQueryDataSource...")
    data_source = BigQueryDataSource(
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID,
        table_prefix=TABLE_PREFIX
    )

    # Test 1: Find PRs from last 30 days
    print("\n2. Testing find_prs_by_date_range() - last 30 days...")
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    prs = data_source.find_prs_by_date_range(
        start_date=thirty_days_ago,
        end_date=now,
        limit=10
    )

    print(f"\n   Results:")
    print(f"   Found {len(prs)} PRs merged in last 30 days")
    for pr in prs:
        print(f"     - PR #{pr.number}: {pr.title[:50]}...")
        print(f"       Merged: {pr.merged_at.date() if pr.merged_at else 'N/A'}")

    # Test 2: With repo filter
    print("\n3. Testing with repo filter...")
    prs_filtered = data_source.find_prs_by_date_range(
        start_date=thirty_days_ago,
        end_date=now,
        repo_name=REPOSITORY,
        limit=10
    )

    print(f"\n   Results for {REPOSITORY}:")
    print(f"   Found {len(prs_filtered)} PRs")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
