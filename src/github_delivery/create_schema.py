#!/usr/bin/env python3
"""
Create BigQuery schema for GitHub PR data.

This script reads table definitions from YAML files in the schemas/ directory
and creates the corresponding BigQuery tables.
"""

from google.cloud import bigquery
from google.api_core import exceptions
import yaml
from pathlib import Path
from typing import Dict, Any, List

# Configuration
PROJECT_ID = "mozdata-nonprod"
DATASET_ID = "analysis"

# Path to schema files
SCHEMAS_DIR = Path(__file__).parent / "schemas"


def load_schema_yaml(schema_name: str) -> Dict[str, Any]:
    """
    Load a schema definition from YAML file.

    Args:
        schema_name: Name of the schema file (without .yaml extension)

    Returns:
        Dictionary containing the schema definition
    """
    schema_file = SCHEMAS_DIR / f"{schema_name}.yaml"

    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    with open(schema_file, 'r') as f:
        return yaml.safe_load(f)


def create_table_from_schema(
    client: bigquery.Client,
    schema_def: Dict[str, Any]
) -> bool:
    """
    Create a BigQuery table from a schema definition.

    Args:
        client: BigQuery client instance
        schema_def: Schema definition loaded from YAML

    Returns:
        True if successful, False otherwise
    """
    table_name = schema_def['table_name']
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    print(f"\n{'='*60}")
    print(f"Creating table: {table_id}")
    print(f"{'='*60}\n")

    # Build schema fields from YAML definition
    schema_fields = []
    for col in schema_def['columns']:
        field = bigquery.SchemaField(
            name=col['name'],
            field_type=col['type'],
            mode=col['mode'],
            description=col.get('description', '')
        )
        schema_fields.append(field)

    # Create the table object
    table = bigquery.Table(table_id, schema=schema_fields)
    table.description = schema_def.get('description', '')

    # Configure partitioning if specified
    if schema_def.get('partitioning'):
        part_config = schema_def['partitioning']
        table.time_partitioning = bigquery.TimePartitioning(
            type_=getattr(bigquery.TimePartitioningType, part_config['type']),
            field=part_config['field']
        )

    # Configure clustering if specified
    if schema_def.get('clustering'):
        table.clustering_fields = schema_def['clustering']

    try:
        # Create the table
        table = client.create_table(table)

        # Print success message
        print(f"✅ Table created successfully!")
        print(f"   Table ID: {table.table_id}")
        print(f"   Location: {table.location}")
        print(f"   Schema: {len(table.schema)} columns")

        if table.time_partitioning:
            print(f"   Partitioned by: {table.time_partitioning.field}")

        if table.clustering_fields:
            print(f"   Clustered by: {', '.join(table.clustering_fields)}")

        return True

    except exceptions.Conflict:
        print(f"⚠️  Table already exists: {table_id}")
        return False

    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False


def main():
    """Main function to create schema."""
    print("\n🏗️  Creating BigQuery Schema for GitHub PR Data\n")

    # Initialize BigQuery client
    try:
        client = bigquery.Client(project=PROJECT_ID)
        print(f"✅ Connected to project: {PROJECT_ID}")
        print(f"   Dataset: {DATASET_ID}")
    except Exception as e:
        print(f"❌ Failed to connect to BigQuery: {e}")
        return

    # Schema files to process (in order)
    schema_files = ['prs', 'reviews', 'files', 'labels']

    results = []

    print("\n📋 Creating tables...")

    # Create each table from its YAML schema
    for i, schema_name in enumerate(schema_files, 1):
        print(f"\n[{i}/{len(schema_files)}] {schema_name.capitalize()} table")

        try:
            # Load schema definition from YAML
            schema_def = load_schema_yaml(schema_name)

            # Create the table
            success = create_table_from_schema(client, schema_def)
            results.append((schema_name, success))

        except Exception as e:
            print(f"❌ Error processing {schema_name}: {e}")
            results.append((schema_name, False))

    # Print summary
    print(f"\n{'='*60}")
    print("📊 Summary:")
    print(f"{'='*60}")

    for table_name, success in results:
        status = "✅" if success else "⚠️"
        print(f"   {status} {table_name}")

    all_success = all(success for _, success in results)

    if all_success:
        print(f"\n✨ All tables created successfully!")
    else:
        print(f"\n⚠️  Some tables had issues (see details above)")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
