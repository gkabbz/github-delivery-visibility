#!/usr/bin/env python3
"""
Test find_prs_by_reviewer method.
"""

from src.github_delivery.bq_data_source import BigQueryDataSource

# Configuration
BQ_PROJECT_ID = "mozdata-nonprod"
BQ_DATASET_ID = "analysis"
TABLE_PREFIX = "gkabbz_gh"
REPOSITORY = "mozilla/bigquery-etl"


def main():
    print("\n🧪 Testing find_prs_by_reviewer()\n")
    print("=" * 60)

    # Initialize data source
    print("\n1. Initializing BigQueryDataSource...")
    data_source = BigQueryDataSource(
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID,
        table_prefix=TABLE_PREFIX
    )

    # Test 1: Find PRs reviewed by a specific person
    print("\n2. Testing find_prs_by_reviewer()...")
    # Using a reviewer we know exists from our loaded data
    prs = data_source.find_prs_by_reviewer(reviewer="scholtzan", limit=5)

    print(f"\n   Results:")
    print(f"   Found {len(prs)} PRs reviewed by scholtzan")
    for pr in prs:
        print(f"     - PR #{pr.number}: {pr.title[:50]}...")
        print(f"       Author: {pr.author.login}")

    # Test 2: With repo filter
    print("\n3. Testing with repo filter...")
    prs_filtered = data_source.find_prs_by_reviewer(
        reviewer="scholtzan",
        repo_name=REPOSITORY,
        limit=5
    )

    print(f"\n   Results for {REPOSITORY}:")
    print(f"   Found {len(prs_filtered)} PRs")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
