#!/usr/bin/env python3
"""
Test GitHubOracle end-to-end.
"""

from dotenv import load_dotenv
from src.github_delivery.llm_client import AnthropicLLMClient
from src.github_delivery.bq_data_source import BigQueryDataSource
from src.github_delivery.github_oracle import GitHubOracle

# Load environment variables
load_dotenv()

# Configuration
BQ_PROJECT_ID = "mozdata-nonprod"
BQ_DATASET_ID = "analysis"
TABLE_PREFIX = "gkabbz_gh"
REPOSITORY = "mozilla/bigquery-etl"


def main():
    print("\n🔮 Testing GitHubOracle End-to-End\n")
    print("=" * 60)

    # Initialize components
    print("\n1. Initializing components...")
    data_source = BigQueryDataSource(
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID,
        table_prefix=TABLE_PREFIX
    )
    llm_client = AnthropicLLMClient()
    oracle = GitHubOracle(data_source, llm_client)
    print("   ✓ GitHubOracle initialized")

    # Test questions
    test_questions = [
        "What did gkabbz ship last week?",
        "Tell me about PR #8127",
    ]

    for i, question in enumerate(test_questions, start=2):
        print(f"\n{i}. Question: '{question}'")
        print("   " + "-" * 56)

        try:
            answer = oracle.ask(question, repo_name=REPOSITORY)
            print(f"\n   Answer:\n   {answer}\n")

        except Exception as e:
            print(f"   ✗ Error: {e}")

    print("=" * 60)
    print("✅ Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
