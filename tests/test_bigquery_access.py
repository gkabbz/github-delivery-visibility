#!/usr/bin/env python3
"""
Test script to verify BigQuery access and table creation permissions.

This script will:
1. Check if you can connect to BigQuery
2. Create a test dataset (if needed)
3. Create a test table
4. Insert test data
5. Query the data
6. Clean up (delete table and dataset)
"""

from google.cloud import bigquery
from google.api_core import exceptions
import sys
from datetime import datetime
import time

# Configuration - UPDATE THESE VALUES
PROJECT_ID = "mozdata-nonprod"  # Your GCP project ID
DATASET_ID = "analysis"  # Using existing dataset (table will be deleted after test)
TABLE_ID = "gkabbz-gh-visibility-test"  # Test table name


def test_bigquery_access():
    """Test BigQuery access and table creation."""

    print(f"Testing BigQuery access for project: {PROJECT_ID}")
    print("=" * 60)

    try:
        # Step 1: Initialize BigQuery client
        print("\n1. Initializing BigQuery client...")
        client = bigquery.Client(project=PROJECT_ID)
        print(f"   ✓ Successfully connected as: {client.project}")

        # Step 2: Check if dataset exists, create if not
        print(f"\n2. Checking dataset: {DATASET_ID}...")
        dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"

        try:
            dataset = client.get_dataset(dataset_ref)
            print(f"   ✓ Dataset already exists: {dataset_ref}")
            dataset_existed = True
        except exceptions.NotFound:
            print(f"   - Dataset not found, creating: {dataset_ref}")
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            dataset.description = "Test dataset for permission verification (safe to delete)"
            dataset = client.create_dataset(dataset, timeout=30)
            print(f"   ✓ Dataset created: {dataset_ref}")
            dataset_existed = False

        # Step 3: Create test table
        print(f"\n3. Creating test table: {TABLE_ID}...")
        table_ref = f"{dataset_ref}.{TABLE_ID}"

        schema = [
            bigquery.SchemaField("id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("test_embedding", "FLOAT64", mode="REPEATED"),
        ]

        table = bigquery.Table(table_ref, schema=schema)
        table.description = "Test table for permission verification"

        try:
            table = client.create_table(table)
            print(f"   ✓ Table created: {table_ref}")
        except exceptions.Conflict:
            print(f"   - Table already exists, deleting and recreating...")
            client.delete_table(table_ref)
            time.sleep(2)  # Wait for deletion to propagate
            table = client.create_table(table)
            print(f"   ✓ Table recreated: {table_ref}")

        # Wait for table to be available
        print(f"   - Waiting for table to be ready...")
        time.sleep(3)

        # Step 4: Insert test data
        print(f"\n4. Inserting test data...")
        rows_to_insert = [
            {
                "id": 1,
                "name": "Test Row 1",
                "timestamp": datetime.utcnow().isoformat(),
                "test_embedding": [0.1, 0.2, 0.3, 0.4],
            },
            {
                "id": 2,
                "name": "Test Row 2",
                "timestamp": datetime.utcnow().isoformat(),
                "test_embedding": [0.5, 0.6, 0.7, 0.8],
            },
        ]

        errors = client.insert_rows_json(table_ref, rows_to_insert)
        if errors:
            print(f"   ✗ Errors occurred while inserting rows: {errors}")
            return False
        else:
            print(f"   ✓ Inserted {len(rows_to_insert)} rows successfully")

        # Step 5: Query the data
        print(f"\n5. Querying test data...")
        query = f"""
            SELECT id, name, timestamp, ARRAY_LENGTH(test_embedding) as embedding_dim
            FROM `{table_ref}`
            ORDER BY id
        """

        query_job = client.query(query)
        results = list(query_job.result())

        print(f"   ✓ Query returned {len(results)} rows:")
        for row in results:
            print(f"     - ID: {row.id}, Name: {row.name}, Embedding Dims: {row.embedding_dim}")

        # Step 6: Clean up
        print(f"\n6. Cleaning up test resources...")
        client.delete_table(table_ref, not_found_ok=True)
        print(f"   ✓ Deleted table: {TABLE_ID}")

        if not dataset_existed:
            client.delete_dataset(dataset_ref, delete_contents=True, not_found_ok=True)
            print(f"   ✓ Deleted dataset: {DATASET_ID}")
        else:
            print(f"   - Keeping existing dataset: {DATASET_ID}")

        # Success!
        print("\n" + "=" * 60)
        print("✅ SUCCESS! You have full BigQuery access:")
        print(f"   - Can create datasets in project: {PROJECT_ID}")
        print(f"   - Can create tables with ARRAY<FLOAT64> columns (for embeddings)")
        print(f"   - Can insert data")
        print(f"   - Can query data")
        print("\nYou're ready to proceed with Phase 0 setup!")
        print("=" * 60)

        return True

    except exceptions.PermissionDenied as e:
        print(f"\n✗ PERMISSION DENIED: {e}")
        print("\nYou may need to:")
        print("  1. Request 'BigQuery Data Editor' role on the project")
        print("  2. Request 'BigQuery Job User' role")
        print("  3. Authenticate with: gcloud auth application-default login")
        return False

    except exceptions.Forbidden as e:
        print(f"\n✗ FORBIDDEN: {e}")
        print("\nYou may not have access to this project.")
        print(f"Please verify the project ID: {PROJECT_ID}")
        return False

    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🔍 BigQuery Access Test\n")

    # Check if google-cloud-bigquery is installed
    try:
        import google.cloud.bigquery
    except ImportError:
        print("✗ ERROR: google-cloud-bigquery is not installed")
        print("\nPlease install it with:")
        print("  pip install google-cloud-bigquery")
        sys.exit(1)

    success = test_bigquery_access()
    sys.exit(0 if success else 1)