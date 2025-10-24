#!/usr/bin/env python3
"""
Truncate production tables to clear streaming buffers.

This is needed when switching from streaming inserts to staging table + MERGE pattern.
"""

import os
from dotenv import load_dotenv
from google.cloud import bigquery

# Load environment
load_dotenv()

def main():
    """Truncate all production tables."""
    project_id = os.getenv('BQ_PROJECT_ID', 'mozdata-nonprod')
    dataset_id = os.getenv('BQ_DATASET_ID', 'analysis')

    client = bigquery.Client()

    tables = [
        f"{project_id}.{dataset_id}.gkabbz_gh_prs",
        f"{project_id}.{dataset_id}.gkabbz_gh_reviews",
        f"{project_id}.{dataset_id}.gkabbz_gh_files",
        f"{project_id}.{dataset_id}.gkabbz_gh_labels",
    ]

    print("🗑️  Truncating production tables to clear streaming buffers...")
    print("=" * 70)

    for table in tables:
        try:
            query = f"TRUNCATE TABLE `{table}`"
            print(f"  Truncating {table.split('.')[-1]}...")
            job = client.query(query)
            job.result()
            print(f"    ✓ Truncated")
        except Exception as e:
            print(f"    ✗ Error: {e}")

    print("\n✅ All tables truncated!")
    print("   You can now run backfill with the new staging table approach.")

if __name__ == '__main__':
    main()
