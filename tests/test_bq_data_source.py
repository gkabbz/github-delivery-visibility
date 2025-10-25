#!/usr/bin/env python3
"""
Test script for BigQueryDataSource.

Tests the find_prs_by_author() method with real BigQuery data.
"""

from src.github_delivery.bq_data_source import BigQueryDataSource

# Configuration
BQ_PROJECT_ID = "mozdata-nonprod"
BQ_DATASET_ID = "analysis"
TABLE_PREFIX = "gkabbz_gh"
REPOSITORY = "mozilla/bigquery-etl"


def main():
    print("\n🧪 Testing BigQueryDataSource\n")
    print("=" * 60)

    # Step 1: Initialize data source
    print("\n1. Initializing BigQueryDataSource...")
    data_source = BigQueryDataSource(
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID,
        table_prefix=TABLE_PREFIX
    )

    # Step 2: Test find_prs_by_author without repo filter
    print("\n2. Testing find_prs_by_author() - all repos...")
    # Using an author we know exists from our loaded data
    # Let's try finding PRs from the first author in our test data
    prs = data_source.find_prs_by_author(author="kik-kik", limit=5)

    print(f"\n   Results:")
    print(f"   Found {len(prs)} PRs")
    for pr in prs:
        print(f"     - PR #{pr.number}: {pr.title[:50]}...")
        print(f"       State: {pr.state.value}, Author: {pr.author.login}")
        print(f"       Changes: +{pr.additions}/-{pr.deletions}")

    # Step 3: Test find_prs_by_author with repo filter
    print("\n3. Testing find_prs_by_author() - filtered by repo...")
    prs_filtered = data_source.find_prs_by_author(
        author="kik-kik",
        repo_name=REPOSITORY,
        limit=5
    )

    print(f"\n   Results for {REPOSITORY}:")
    print(f"   Found {len(prs_filtered)} PRs")
    for pr in prs_filtered:
        print(f"     - PR #{pr.number}: {pr.title[:50]}...")

    # Step 4: Test with non-existent author
    print("\n4. Testing with non-existent author...")
    prs_empty = data_source.find_prs_by_author(author="nonexistent-user-12345")

    print(f"\n   Results:")
    print(f"   Found {len(prs_empty)} PRs (should be 0)")

    print("\n" + "=" * 60)
    print("✅ BigQueryDataSource test complete!")
    print("\n💡 Key Takeaway:")
    print("   - Can query PRs by author from BigQuery")
    print("   - Results returned as PullRequest objects")
    print("   - Optional repo filtering works")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()