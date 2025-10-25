#!/usr/bin/env python3
"""
Test semantic_search method.
"""

from src.github_delivery.bq_data_source import BigQueryDataSource

# Configuration
BQ_PROJECT_ID = "mozdata-nonprod"
BQ_DATASET_ID = "analysis"
TABLE_PREFIX = "gkabbz_gh"
REPOSITORY = "mozilla/bigquery-etl"


def main():
    print("\n🧪 Testing semantic_search()\n")
    print("=" * 60)

    # Initialize data source
    print("\n1. Initializing BigQueryDataSource...")
    data_source = BigQueryDataSource(
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID,
        table_prefix=TABLE_PREFIX
    )

    # Test semantic search
    query = "database migration"
    print(f"\n2. Testing semantic_search() with query: '{query}'")

    prs = data_source.semantic_search(query=query, limit=5)

    print(f"\n   Results:")
    print(f"   Found {len(prs)} PRs semantically similar to '{query}'")
    for i, pr in enumerate(prs, 1):
        print(f"     {i}. PR #{pr.number}: {pr.title[:50]}...")
        print(f"        Body preview: {(pr.body or '')[:60]}...")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
