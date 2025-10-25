#!/usr/bin/env python3
"""
Test get_pr_detail method.
"""

from src.github_delivery.bq_data_source import BigQueryDataSource

# Configuration
BQ_PROJECT_ID = "mozdata-nonprod"
BQ_DATASET_ID = "analysis"
TABLE_PREFIX = "gkabbz_gh"
REPOSITORY = "mozilla/bigquery-etl"


def main():
    print("\n🧪 Testing get_pr_detail()\n")
    print("=" * 60)

    # Initialize data source
    print("\n1. Initializing BigQueryDataSource...")
    data_source = BigQueryDataSource(
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID,
        table_prefix=TABLE_PREFIX
    )

    # Test 1: Get a PR that exists
    pr_number = 8127
    print(f"\n2. Testing get_pr_detail() with PR #{pr_number}")

    pr = data_source.get_pr_detail(repo_name=REPOSITORY, pr_number=pr_number)

    if pr:
        print(f"\n   ✓ Found PR:")
        print(f"     Number: #{pr.number}")
        print(f"     Title: {pr.title}")
        print(f"     Author: {pr.author.login}")
        print(f"     State: {pr.state.value}")
        print(f"     Created: {pr.created_at.date()}")
        print(f"     Changes: +{pr.additions}/-{pr.deletions} in {pr.changed_files} files")
    else:
        print(f"\n   ✗ PR not found")

    # Test 2: Get a PR that doesn't exist
    print(f"\n3. Testing with non-existent PR #999999...")
    pr_none = data_source.get_pr_detail(repo_name=REPOSITORY, pr_number=999999)

    if pr_none:
        print(f"   ✗ Unexpected: Found PR (should not exist)")
    else:
        print(f"   ✓ Correctly returned None for non-existent PR")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
