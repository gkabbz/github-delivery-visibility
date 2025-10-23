#!/usr/bin/env python3
"""
GitHubOracle - Main application that orchestrates all components.

This is the high-level interface that:
1. Takes natural language questions
2. Plans queries using LLM
3. Executes queries against data source
4. Synthesizes answers using LLM
"""

from typing import List
from .data_source import PRDataSource
from .llm_client import LLMClient
from .query_planner import LLMQueryPlanner, QueryPlan, QueryType
from .models import PullRequest


class GitHubOracle:
    """
    Main orchestrator that connects all components.

    Example:
        oracle = GitHubOracle(data_source, llm_client)
        answer = oracle.ask("What did Alice ship last week?")
        print(answer)
    """

    def __init__(self, data_source: PRDataSource, llm_client: LLMClient):
        """
        Initialize GitHubOracle with required components.

        Args:
            data_source: PRDataSource implementation (e.g., BigQueryDataSource)
            llm_client: LLMClient implementation (e.g., AnthropicLLMClient)
        """
        self.data_source = data_source
        self.llm_client = llm_client
        self.query_planner = LLMQueryPlanner(llm_client)

    def ask(self, question: str, repo_name: str = None) -> str:
        """
        Answer a natural language question about GitHub PRs.

        Args:
            question: Natural language question (e.g., "What did Alice ship?")
            repo_name: Optional repository name to filter by

        Returns:
            Natural language answer
        """
        # Step 1: Plan the query
        plan = self.query_planner.plan(question, repo_name)

        # Step 2: Execute the query
        prs = self._execute_query(plan)

        # Step 3: Synthesize answer
        answer = self._synthesize_answer(question, prs, plan)

        return answer

    def _execute_query(self, plan: QueryPlan) -> List[PullRequest]:
        """
        Execute a query plan against the data source.

        Args:
            plan: QueryPlan with parameters

        Returns:
            List of matching PRs
        """
        # Handle specific PR lookup
        if plan.pr_number:
            pr = self.data_source.get_pr_detail(plan.repo_name, plan.pr_number)
            return [pr] if pr else []

        # Route based on query type
        if plan.query_type == QueryType.SEMANTIC:
            # Pure semantic search
            return self.data_source.semantic_search(
                query=plan.semantic_query,
                repo_name=plan.repo_name,
                limit=plan.limit
            )

        elif plan.query_type == QueryType.STRUCTURED:
            # Structured query - route to appropriate method
            if plan.author:
                return self.data_source.find_prs_by_author(
                    author=plan.author,
                    repo_name=plan.repo_name,
                    limit=plan.limit
                )
            elif plan.reviewer:
                return self.data_source.find_prs_by_reviewer(
                    reviewer=plan.reviewer,
                    repo_name=plan.repo_name,
                    limit=plan.limit
                )
            elif plan.filename:
                return self.data_source.find_prs_by_file(
                    filename=plan.filename,
                    repo_name=plan.repo_name,
                    limit=plan.limit
                )
            elif plan.directory:
                return self.data_source.find_prs_by_directory(
                    directory=plan.directory,
                    repo_name=plan.repo_name,
                    limit=plan.limit
                )
            elif plan.start_date and plan.end_date:
                return self.data_source.find_prs_by_date_range(
                    start_date=plan.start_date,
                    end_date=plan.end_date,
                    repo_name=plan.repo_name,
                    limit=plan.limit
                )
            else:
                return []

        elif plan.query_type == QueryType.HYBRID:
            # Hybrid: semantic search + structured filters
            # For now, do semantic search (structured filters already in plan)
            return self.data_source.semantic_search(
                query=plan.semantic_query,
                repo_name=plan.repo_name,
                limit=plan.limit
            )

        return []

    def _synthesize_answer(self, question: str, prs: List[PullRequest], plan: QueryPlan) -> str:
        """
        Use LLM to synthesize a natural language answer from PR results.

        Args:
            question: Original user question
            prs: List of PRs from query
            plan: The query plan that was executed

        Returns:
            Natural language answer
        """
        # Handle no results
        if not prs:
            return "No PRs found matching your query."

        # Build context from PRs
        pr_summaries = []
        for pr in prs[:10]:  # Limit to top 10 to avoid token limits
            summary = f"PR #{pr.number}: {pr.title}\n"
            summary += f"  Author: {pr.author.login}\n"
            summary += f"  State: {pr.state.value}\n"
            summary += f"  Created: {pr.created_at.date()}\n"
            if pr.merged_at:
                summary += f"  Merged: {pr.merged_at.date()}\n"
            if pr.body:
                # Truncate body to first 200 chars
                body_preview = pr.body[:200] + "..." if len(pr.body) > 200 else pr.body
                summary += f"  Description: {body_preview}\n"
            pr_summaries.append(summary)

        context = "\n".join(pr_summaries)

        # Build synthesis prompt
        system_prompt = """You are a helpful assistant that answers questions about GitHub pull requests.

Given the user's question and a list of relevant PRs, provide a concise, natural language answer.

Guidelines:
- Be specific and cite PR numbers
- Summarize key information
- If asked about time ranges, mention dates
- Keep the answer concise (2-4 sentences)"""

        user_prompt = f"""Question: {question}

Relevant PRs:
{context}

Provide a concise answer to the question based on these PRs."""

        # Call LLM
        response = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Slightly creative but mostly factual
            max_tokens=500
        )

        return response.content
