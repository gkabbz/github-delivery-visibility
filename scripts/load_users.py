#!/usr/bin/env python3
"""
Load user data from CSV into BigQuery users table.

Usage:
    python scripts/load_users.py [--csv-path users.csv]

CSV Format:
    github_login,display_name,team
    gkabbz,George Kaberere,Data Platform Engineering

Note: This is MVP code. For production, consider:
- Moving user data to a separate managed system
- Using external configuration management
- Implementing proper access controls
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from google.cloud import bigquery

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
load_dotenv()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Load user data from CSV to BigQuery'
    )
    parser.add_argument(
        '--csv-path',
        default='users.csv',
        help='Path to CSV file (default: users.csv)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate CSV but do not load to BigQuery'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    return parser.parse_args()


def validate_csv(csv_path: str, verbose: bool = False) -> List[Dict[str, str]]:
    """
    Validate CSV file and return rows.

    Args:
        csv_path: Path to CSV file
        verbose: Print detailed validation info

    Returns:
        List of row dictionaries

    Raises:
        ValueError: If CSV is invalid
    """
    if not os.path.exists(csv_path):
        raise ValueError(f"CSV file not found: {csv_path}")

    rows = []
    required_columns = {'github_login', 'display_name', 'team'}

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        # Validate header
        if not reader.fieldnames:
            raise ValueError("CSV file is empty")

        missing_cols = required_columns - set(reader.fieldnames)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Validate rows
        for i, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            # Check required fields
            if not row['github_login']:
                raise ValueError(f"Row {i}: github_login is required")
            if not row['display_name']:
                raise ValueError(f"Row {i}: display_name is required")

            # Team can be empty
            if not row['team']:
                row['team'] = None

            rows.append(row)

            if verbose:
                print(f"  ✓ Row {i}: {row['github_login']} → {row['display_name']} ({row['team'] or 'No team'})")

    if not rows:
        raise ValueError("CSV has no data rows")

    return rows


def load_to_bigquery(rows: List[Dict[str, str]], verbose: bool = False):
    """
    Load user data to BigQuery using MERGE for idempotency.

    Args:
        rows: List of user dictionaries
        verbose: Print detailed progress
    """
    # Get BigQuery configuration
    project_id = os.getenv('BQ_PROJECT_ID', 'mozdata-nonprod')
    dataset_id = os.getenv('BQ_DATASET_ID', 'analysis')
    table_prefix = os.getenv('TABLE_PREFIX', 'gkabbz_gh')

    table_id = f"{project_id}.{dataset_id}.{table_prefix}_users"

    if verbose:
        print(f"\n  Target table: {table_id}")
        print(f"  Loading {len(rows)} users...")

    # Initialize client
    client = bigquery.Client(project=project_id)

    # Create staging table name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    staging_table_id = f"{project_id}.{dataset_id}.{table_prefix}_users_staging_{timestamp}"

    # Load data to staging table
    print(f"\n  1. Loading to staging table...")

    # Convert rows to BigQuery format
    bq_rows = []
    current_time = datetime.utcnow().isoformat()

    for row in rows:
        bq_rows.append({
            'github_login': row['github_login'],
            'display_name': row['display_name'],
            'team': row['team'],
            'last_updated': current_time
        })

    # Load to staging table
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("github_login", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("display_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("team", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("last_updated", "TIMESTAMP", mode="REQUIRED"),
        ],
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    job = client.load_table_from_json(
        bq_rows,
        staging_table_id,
        job_config=job_config
    )
    job.result()  # Wait for completion

    print(f"  ✓ Loaded {len(bq_rows)} rows to staging")

    # MERGE from staging to production
    print(f"\n  2. Merging to production table...")

    merge_query = f"""
    MERGE `{table_id}` AS target
    USING `{staging_table_id}` AS source
    ON target.github_login = source.github_login

    WHEN MATCHED THEN
      UPDATE SET
        display_name = source.display_name,
        team = source.team,
        last_updated = source.last_updated

    WHEN NOT MATCHED THEN
      INSERT (github_login, display_name, team, last_updated)
      VALUES (source.github_login, source.display_name, source.team, source.last_updated)
    """

    job = client.query(merge_query)
    job.result()  # Wait for completion

    print(f"  ✓ Merged to production table")

    # Clean up staging table
    print(f"\n  3. Cleaning up staging table...")
    client.delete_table(staging_table_id)
    print(f"  ✓ Staging table deleted")

    print(f"\n✅ Successfully loaded {len(rows)} users to {table_id}")


def main():
    """Main entry point."""
    args = parse_args()

    print("\n📊 Load Users to BigQuery")
    print("=" * 60)

    try:
        # Validate CSV
        print(f"\n  Validating CSV: {args.csv_path}")
        rows = validate_csv(args.csv_path, verbose=args.verbose)
        print(f"  ✓ CSV valid: {len(rows)} users")

        if args.dry_run:
            print("\n  🔍 Dry run - not loading to BigQuery")
            return

        # Load to BigQuery
        load_to_bigquery(rows, verbose=args.verbose)

    except ValueError as e:
        print(f"\n❌ Validation Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
