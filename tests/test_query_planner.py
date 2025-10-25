#!/usr/bin/env python3
"""
Test LLMQueryPlanner implementation.
"""

from dotenv import load_dotenv
from src.github_delivery.llm_client import AnthropicLLMClient
from src.github_delivery.query_planner import LLMQueryPlanner

# Load environment variables
load_dotenv()


def main():
    print("\n🧪 Testing LLMQueryPlanner\n")
    print("=" * 60)

    # Initialize client and planner
    print("\n1. Initializing LLMClient and QueryPlanner...")
    llm_client = AnthropicLLMClient()
    planner = LLMQueryPlanner(llm_client)
    print("   ✓ Planner initialized")

    # Test questions
    test_questions = [
        "What did gkabbz ship last week?",
        "Find PRs about database migrations",
        "What authentication changes did scholtzan make?",
    ]

    for i, question in enumerate(test_questions, start=2):
        print(f"\n{i}. Testing: '{question}'")

        try:
            plan = planner.plan(question)

            print(f"   Query Type: {plan.query_type.value}")
            if plan.author:
                print(f"   Author: {plan.author}")
            if plan.reviewer:
                print(f"   Reviewer: {plan.reviewer}")
            if plan.start_date:
                print(f"   Start Date: {plan.start_date.date()}")
            if plan.end_date:
                print(f"   End Date: {plan.end_date.date()}")
            if plan.semantic_query:
                print(f"   Semantic Query: {plan.semantic_query}")
            if plan.filename:
                print(f"   Filename: {plan.filename}")
            if plan.directory:
                print(f"   Directory: {plan.directory}")
            print(f"   Limit: {plan.limit}")

        except Exception as e:
            print(f"   ✗ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
