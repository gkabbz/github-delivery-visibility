#!/usr/bin/env python3
"""
Test find_prs_by_file method.
"""

from src.github_delivery.bq_data_source import BigQueryDataSource

# Configuration
BQ_PROJECT_ID = "mozdata-nonprod"
BQ_DATASET_ID = "analysis"
TABLE_PREFIX = "gkabbz_gh"
REPOSITORY = "mozilla/bigquery-etl"


def main():
    print("\n🧪 Testing find_prs_by_file()\n")
    print("=" * 60)

    # Initialize data source
    print("\n1. Initializing BigQueryDataSource...")
    data_source = BigQueryDataSource(
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID,
        table_prefix=TABLE_PREFIX
    )

    # First, let's see what files exist in our data
    from google.cloud import bigquery
    client = bigquery.Client(project=BQ_PROJECT_ID)
    query = f"SELECT DISTINCT filename FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{TABLE_PREFIX}_files` LIMIT 5"
    results = client.query(query).result()

    print("\n   Sample files in database:")
    filenames = []
    for row in results:
        print(f"     - {row.filename}")
        filenames.append(row.filename)

    if not filenames:
        print("   ✗ No files found in database")
        return

    # Test with first file
    test_file = filenames[0]
    print(f"\n2. Testing find_prs_by_file() with: {test_file}")

    prs = data_source.find_prs_by_file(filename=test_file, limit=5)

    print(f"\n   Results:")
    print(f"   Found {len(prs)} PRs that changed {test_file}")
    for pr in prs:
        print(f"     - PR #{pr.number}: {pr.title[:50]}...")
        print(f"       Author: {pr.author.login}")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
