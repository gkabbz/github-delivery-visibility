#!/usr/bin/env python3
"""
Query Planner - Translates natural language questions into structured query plans.

The QueryPlanner uses an LLM to understand user questions and determine:
1. What type of query to run (structured, semantic, or hybrid)
2. What parameters to use (author, date range, keywords, etc.)
3. How to combine results if multiple queries are needed
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum


class QueryType(Enum):
    """Type of query to execute."""

    STRUCTURED = "structured"  # Metadata queries (author, date, reviewer)
    SEMANTIC = "semantic"      # Vector search on content
    HYBRID = "hybrid"          # Both structured + semantic


@dataclass
class QueryPlan:
    """
    Structured plan for executing a query against the data source.

    The LLM generates this plan by analyzing the user's question.
    """

    query_type: QueryType
    """Type of query to execute."""

    # Structured query parameters
    author: Optional[str] = None
    """GitHub username to filter by."""

    reviewer: Optional[str] = None
    """Reviewer username to filter by."""

    start_date: Optional[datetime] = None
    """Start of date range."""

    end_date: Optional[datetime] = None
    """End of date range."""

    filename: Optional[str] = None
    """File to filter by."""

    directory: Optional[str] = None
    """Directory to filter by."""

    pr_number: Optional[int] = None
    """Specific PR number to look up."""

    # Semantic query parameters
    semantic_query: Optional[str] = None
    """Natural language query for semantic search."""

    # Result parameters
    limit: Optional[int] = None
    """Maximum number of results to return (None = no limit)."""

    repo_name: Optional[str] = None
    """Repository to filter by (None = all repos)."""


class LLMQueryPlanner:
    """
    Uses an LLM to convert natural language questions into QueryPlans.

    Example:
        planner = LLMQueryPlanner(llm_client)
        plan = planner.plan("What did Alice ship last week?")
        # Returns: QueryPlan(query_type=STRUCTURED, author="alice", start_date=...)
    """

    def __init__(self, llm_client):
        """
        Initialize the query planner.

        Args:
            llm_client: LLMClient instance for making LLM calls
        """
        self.llm_client = llm_client
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for query planning."""
        return """You are a query planning assistant for a GitHub PR database.

Your job is to convert natural language questions into structured query plans.

Output ONLY valid JSON in this exact format:
{
    "query_type": "structured" | "semantic" | "hybrid",
    "author": "github_username" or null,
    "reviewer": "github_username" or null,
    "start_date": "YYYY-MM-DD" or null,
    "end_date": "YYYY-MM-DD" or null,
    "filename": "path/to/file.py" or null,
    "directory": "path/to/dir" or null,
    "pr_number": 123 or null,
    "semantic_query": "natural language query" or null,
    "limit": 10,
    "repo_name": "owner/repo" or null
}

Query Types:
- "structured": Use when filtering by metadata (author, date, reviewer, file)
- "semantic": Use when searching by concept/meaning (e.g., "authentication changes")
- "hybrid": Use both when combining metadata filters with semantic search

Limit Guidelines:
- Don't include "limit" unless the user asks for a specific number (e.g., "top 5", "last 10")
- Omit "limit" for queries like "What PRs were landed?" to return all results
- Only for semantic searches, you may add limit: 20 to get most relevant results

Examples:
Q: "What did alice ship last week?"
A: {"query_type": "structured", "author": "alice", "start_date": "2024-10-15", "end_date": "2024-10-22"}

Q: "Find PRs about database migrations"
A: {"query_type": "semantic", "semantic_query": "database migrations", "limit": 20}

Q: "What authentication changes did bob make?"
A: {"query_type": "hybrid", "author": "bob", "semantic_query": "authentication"}

Today's date: {today}

Output ONLY the JSON, no other text."""

    def plan(self, question: str, repo_name: Optional[str] = None) -> QueryPlan:
        """
        Convert a natural language question into a structured QueryPlan.

        Args:
            question: Natural language question (e.g., "What did Alice ship?")
            repo_name: Optional repository name to filter by

        Returns:
            QueryPlan with extracted parameters

        Raises:
            ValueError: If LLM response cannot be parsed
        """
        import json
        from datetime import datetime

        # Build prompt with today's date
        today = datetime.now().strftime("%Y-%m-%d")
        system_prompt = self.system_prompt.replace("{today}", today)

        # Call LLM
        response = self.llm_client.generate(
            prompt=question,
            system_prompt=system_prompt,
            temperature=0.0,  # Deterministic for consistency
            max_tokens=500
        )

        # Parse JSON response
        try:
            plan_dict = json.loads(response.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}\nResponse: {response.content}")

        # Convert to QueryPlan
        return self._dict_to_query_plan(plan_dict, repo_name)

    def _dict_to_query_plan(self, plan_dict: dict, repo_name: Optional[str] = None) -> QueryPlan:
        """
        Convert a dictionary from LLM response into a QueryPlan object.

        Args:
            plan_dict: Dictionary from parsed JSON
            repo_name: Optional repository override

        Returns:
            QueryPlan object
        """
        from datetime import datetime

        # Parse query type
        query_type = QueryType(plan_dict.get("query_type", "structured"))

        # Parse dates
        start_date = None
        if plan_dict.get("start_date"):
            start_date = datetime.strptime(plan_dict["start_date"], "%Y-%m-%d")

        end_date = None
        if plan_dict.get("end_date"):
            end_date = datetime.strptime(plan_dict["end_date"], "%Y-%m-%d")

        # Build QueryPlan
        return QueryPlan(
            query_type=query_type,
            author=plan_dict.get("author"),
            reviewer=plan_dict.get("reviewer"),
            start_date=start_date,
            end_date=end_date,
            filename=plan_dict.get("filename"),
            directory=plan_dict.get("directory"),
            pr_number=plan_dict.get("pr_number"),
            semantic_query=plan_dict.get("semantic_query"),
            limit=plan_dict.get("limit"),
            repo_name=repo_name or plan_dict.get("repo_name")
        )
