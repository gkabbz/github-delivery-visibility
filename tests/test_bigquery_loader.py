#!/usr/bin/env python3
"""
Test script for BigQueryLoader.

This demonstrates loading cached PR data with embeddings into BigQuery.
"""

from src.github_delivery.bigquery_loader import BigQueryLoader
from src.github_delivery.cache import PRCache

# Configuration
BQ_PROJECT_ID = "mozdata-nonprod"
BQ_DATASET_ID = "analysis"
EMBEDDING_PROJECT_ID = "mozdata"
REPOSITORY = "mozilla/bigquery-etl"


def main():
    print("\n🧪 Testing BigQueryLoader with Cached PRs\n")
    print("=" * 60)

    # Step 1: Load PRs from cache
    print("\n1. Loading PRs from cache...")
    cache = PRCache()
    pr_numbers = cache.get_cached_pr_numbers(REPOSITORY)

    if not pr_numbers:
        print("   ✗ No cached PRs found!")
        print("   Run the collector first to cache some PRs.")
        return

    print(f"   ✓ Found {len(pr_numbers)} cached PRs")

    # Load first 5 PRs for testing (to keep it quick)
    test_count = min(5, len(pr_numbers))
    print(f"   Loading first {test_count} PRs for testing...")

    prs = []
    for pr_num in pr_numbers[:test_count]:
        pr = cache.get_pr(REPOSITORY, pr_num)
        if pr:
            prs.append(pr)
            print(f"     ✓ PR #{pr_num}: {pr.title[:50]}...")

    print(f"   ✓ Loaded {len(prs)} PRs from cache")

    # Step 2: Initialize BigQuery loader
    print("\n2. Initializing BigQueryLoader...")
    loader = BigQueryLoader(
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID,
        embedding_project_id=EMBEDDING_PROJECT_ID
    )

    # Step 3: Load PRs into BigQuery with embeddings
    print(f"\n3. Loading PRs into BigQuery with embeddings...")
    result = loader.load_pull_requests(
        repo_name=REPOSITORY,
        pull_requests=prs
    )

    print(f"\n   ✓ Load complete!")
    print(f"     - PRs: {result['prs']}")
    print(f"     - Reviews: {result['reviews']}")
    print(f"     - Files: {result['files']}")
    print(f"     - Labels: {result['labels']}")

    # Step 4: Verify data was loaded
    print("\n4. Verifying data in BigQuery...")
    counts = loader.get_table_row_counts()
    print(f"   Current table row counts:")
    print(f"     - gkabbz_gh_prs: {counts['prs']}")
    print(f"     - gkabbz_gh_reviews: {counts['reviews']}")
    print(f"     - gkabbz_gh_files: {counts['files']}")
    print(f"     - gkabbz_gh_labels: {counts['labels']}")

    print("\n" + "=" * 60)
    print("✅ BigQueryLoader test complete!")
    print("\n💡 Key Takeaway:")
    print("   - Real mozilla/bigquery-etl PRs loaded with 768-dimensional embeddings")
    print("   - Reviews, files, and labels loaded separately")
    print("   - Ready for semantic search queries!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
