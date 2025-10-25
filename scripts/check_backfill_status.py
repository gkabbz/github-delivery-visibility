#!/usr/bin/env python3
"""
Check the status of BigQuery tables after backfill.

Shows row counts and sample data from each table.
"""

import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

# Configuration
BQ_PROJECT_ID = os.getenv("BQ_PROJECT_ID", "mozdata-nonprod")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "analysis")
TABLE_PREFIX = os.getenv("TABLE_PREFIX", "gkabbz_gh")


def main():
    print("\n📊 BigQuery Table Status Check")
    print("=" * 60)

    client = bigquery.Client(project=BQ_PROJECT_ID)

    tables = {
        "PRs": f"{TABLE_PREFIX}_prs",
        "Reviews": f"{TABLE_PREFIX}_reviews",
        "Files": f"{TABLE_PREFIX}_files",
        "Labels": f"{TABLE_PREFIX}_labels",
    }

    for name, table_name in tables.items():
        full_table = f"{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{table_name}"

        print(f"\n{name} Table: {table_name}")
        print("-" * 60)

        try:
            # Get row count
            query = f"SELECT COUNT(*) as count FROM `{full_table}`"
            result = list(client.query(query).result())
            count = result[0].count

            print(f"  Total rows: {count:,}")

            if count > 0:
                # Get recent entries
                if name == "PRs":
                    query = f"""
                    SELECT number, title, author, state, created_at
                    FROM `{full_table}`
                    ORDER BY created_at DESC
                    LIMIT 5
                    """
                elif name == "Reviews":
                    query = f"""
                    SELECT pr_number, reviewer, state, submitted_at
                    FROM `{full_table}`
                    ORDER BY submitted_at DESC
                    LIMIT 5
                    """
                elif name == "Files":
                    query = f"""
                    SELECT pr_number, filename, status, additions, deletions
                    FROM `{full_table}`
                    ORDER BY pr_number DESC
                    LIMIT 5
                    """
                elif name == "Labels":
                    query = f"""
                    SELECT pr_number, name as label
                    FROM `{full_table}`
                    ORDER BY pr_number DESC
                    LIMIT 5
                    """

                results = list(client.query(query).result())

                print(f"  Recent entries:")
                for row in results:
                    if name == "PRs":
                        print(f"    PR #{row.number}: {row.title[:50]}... by {row.author}")
                    elif name == "Reviews":
                        print(f"    PR #{row.pr_number}: Reviewed by {row.reviewer} ({row.state})")
                    elif name == "Files":
                        print(f"    PR #{row.pr_number}: {row.filename} (+{row.additions}/-{row.deletions})")
                    elif name == "Labels":
                        print(f"    PR #{row.pr_number}: {row.label}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ Status check complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
