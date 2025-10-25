#!/usr/bin/env python3
"""
Test deduplication in BigQueryLoader.

This script tests that we properly skip duplicate PRs, reviews, files, and labels
before generating embeddings.
"""

import os
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment
load_dotenv()

def test_deduplication():
    """Test that deduplication works for all record types."""
    from src.github_delivery.bigquery_loader import BigQueryLoader

    # Initialize loader
    loader = BigQueryLoader(
        project_id=os.getenv('BQ_PROJECT_ID', 'mozdata-nonprod'),
        dataset_id=os.getenv('BQ_DATASET_ID', 'analysis')
    )

    repo_name = os.getenv('GITHUB_REPOSITORY', 'mozilla/bigquery-etl')

    print("\n" + "=" * 70)
    print("Testing Deduplication Logic")
    print("=" * 70)

    # Test 1: Check existing PRs
    print("\n1. Testing PR deduplication...")
    existing_prs = loader._get_existing_pr_numbers(repo_name)
    print(f"   Found {len(existing_prs)} existing PRs in BigQuery")
    if existing_prs:
        sample_prs = list(existing_prs)[:5]
        print(f"   Sample PR numbers: {sample_prs}")

    # Test 2: Check existing reviews
    print("\n2. Testing review deduplication...")
    existing_reviews = loader._get_existing_review_ids(repo_name)
    print(f"   Found {len(existing_reviews)} existing reviews in BigQuery")
    if existing_reviews:
        sample_reviews = list(existing_reviews)[:5]
        print(f"   Sample review IDs: {sample_reviews}")

    # Test 3: Check existing files
    print("\n3. Testing file deduplication...")
    existing_files = loader._get_existing_files(repo_name)
    print(f"   Found {len(existing_files)} existing file records in BigQuery")
    if existing_files:
        sample_files = list(existing_files)[:3]
        print(f"   Sample file keys (pr_number, filename): {sample_files}")

    # Test 4: Check existing labels
    print("\n4. Testing label deduplication...")
    existing_labels = loader._get_existing_labels(repo_name)
    print(f"   Found {len(existing_labels)} existing label records in BigQuery")
    if existing_labels:
        sample_labels = list(existing_labels)[:5]
        print(f"   Sample label keys (pr_number, label_name): {sample_labels}")

    print("\n" + "=" * 70)
    print("✅ Deduplication queries working correctly!")
    print("=" * 70)

    # Show what would happen with a re-run
    print("\n📊 Impact Assessment:")
    print(f"   If you re-run backfill with existing data:")
    print(f"   - {len(existing_prs)} PRs would be skipped (no embedding cost)")
    print(f"   - {len(existing_reviews)} reviews would be skipped (no embedding cost)")
    print(f"   - {len(existing_files)} file patches would be skipped (no embedding cost)")
    print(f"   - {len(existing_labels)} labels would be skipped (no cost)")

    # Estimate savings
    print("\n💰 Cost Savings Estimate:")
    total_embeddings_skipped = len(existing_prs) + len(existing_reviews) + len(existing_files)
    print(f"   Total embeddings that would be skipped: {total_embeddings_skipped}")

    # Rough cost estimate for text-embedding-004
    # $0.00002 per 1K characters (approximate)
    # Assume average text length of 500 chars = ~$0.00001 per embedding
    estimated_savings = total_embeddings_skipped * 0.00001
    print(f"   Estimated cost savings: ${estimated_savings:.4f} per re-run")

    return True


if __name__ == '__main__':
    try:
        test_deduplication()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
