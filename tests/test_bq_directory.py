#!/usr/bin/env python3
"""
Test find_prs_by_directory method.
"""

from src.github_delivery.bq_data_source import BigQueryDataSource

# Configuration
BQ_PROJECT_ID = "mozdata-nonprod"
BQ_DATASET_ID = "analysis"
TABLE_PREFIX = "gkabbz_gh"
REPOSITORY = "mozilla/bigquery-etl"


def main():
    print("\n🧪 Testing find_prs_by_directory()\n")
    print("=" * 60)

    # Initialize data source
    print("\n1. Initializing BigQueryDataSource...")
    data_source = BigQueryDataSource(
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID,
        table_prefix=TABLE_PREFIX
    )

    # Test with a common directory pattern
    test_directory = "sql"
    print(f"\n2. Testing find_prs_by_directory() with: {test_directory}/")

    prs = data_source.find_prs_by_directory(directory=test_directory, limit=5)

    print(f"\n   Results:")
    print(f"   Found {len(prs)} PRs that changed {test_directory}/")
    for pr in prs:
        print(f"     - PR #{pr.number}: {pr.title[:50]}...")
        print(f"       Author: {pr.author.login}")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
