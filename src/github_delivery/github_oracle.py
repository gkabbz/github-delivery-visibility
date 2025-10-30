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

        Uses chunking for large result sets to ensure completeness.

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

        # For small result sets, use simple approach
        if len(prs) <= 20:
            return self._synthesize_simple(question, prs)

        # For large result sets, use chunking
        print(f"\n📊 Processing {len(prs)} PRs using chunked summarization...")
        return self._synthesize_chunked(question, prs)

    def _synthesize_simple(self, question: str, prs: List[PullRequest]) -> str:
        """
        Simple synthesis for small result sets (<=20 PRs).

        Args:
            question: Original user question
            prs: List of PRs (should be 20 or fewer)

        Returns:
            Natural language answer
        """
        # Build detailed context from PRs
        pr_summaries = []
        for pr in prs:
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

            # Add reviews if available
            if pr.reviews:
                summary += f"  Reviews:\n"
                for review in pr.reviews:
                    summary += f"    - {review['reviewer']} ({review['state']}) on {review['submitted_at'].date()}\n"

            # Add file count if available
            if pr.file_stats:
                summary += f"  Files changed: {len(pr.file_stats)}\n"

            pr_summaries.append(summary)

        context = "\n".join(pr_summaries)

        # Build synthesis prompt
        system_prompt = """You are a helpful assistant that answers questions about GitHub pull requests.

Given the user's question and a list of relevant PRs, provide a comprehensive, natural language answer.

Guidelines:
- Be specific and cite PR numbers
- IMPORTANT: Always clearly indicate whether PRs are merged or open/unmerged
  - For merged PRs: mention the merge date (e.g., "PR #123 merged August 15, 2025")
  - For open PRs: clearly state they are "open" or "not yet merged" (e.g., "PR #456 is currently open")
- Summarize key information and patterns
- If asked about time ranges, mention dates
- Provide insights and trends when relevant"""

        user_prompt = f"""Question: {question}

Relevant PRs:
{context}

Provide a comprehensive answer to the question based on these PRs."""

        # Call LLM
        response = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1000
        )

        return response.content

    def _synthesize_chunked(self, question: str, prs: List[PullRequest]) -> str:
        """
        Chunked synthesis for large result sets (>20 PRs).

        Breaks PRs into chunks, summarizes each chunk, then synthesizes final answer.

        Args:
            question: Original user question
            prs: List of PRs

        Returns:
            Natural language answer
        """
        chunk_size = 500
        chunk_summaries = []

        # Step 1: Summarize each chunk
        for i in range(0, len(prs), chunk_size):
            chunk = prs[i:i + chunk_size]
            chunk_num = (i // chunk_size) + 1
            total_chunks = (len(prs) + chunk_size - 1) // chunk_size

            print(f"  Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} PRs)...")

            chunk_summary = self._summarize_chunk(chunk, chunk_num)
            chunk_summaries.append(chunk_summary)

        # Step 2: Synthesize final answer from chunk summaries
        print(f"  Synthesizing final answer from {len(chunk_summaries)} chunk summaries...")
        return self._synthesize_final(question, prs, chunk_summaries)

    def _summarize_chunk(self, prs: List[PullRequest], chunk_num: int) -> str:
        """
        Summarize a chunk of PRs.

        Args:
            prs: List of PRs in this chunk
            chunk_num: Chunk number for reference

        Returns:
            Summary text for this chunk
        """
        # Build compact PR list for this chunk
        pr_list = []
        for pr in prs:
            pr_info = f"PR #{pr.number}: {pr.title} "
            pr_info += f"(by {pr.author.login}, "
            if pr.merged_at:
                pr_info += f"merged {pr.merged_at.date()})"
            else:
                pr_info += f"created {pr.created_at.date()})"
            pr_list.append(pr_info)

        context = "\n".join(pr_list)

        system_prompt = """You are summarizing a chunk of GitHub pull requests.

Your job is to extract key information and patterns from this chunk:
- Common themes or types of changes
- Notable authors or activity patterns
- Important PRs that stand out
- Date ranges covered
- IMPORTANT: Note whether PRs are merged or still open (check if "merged" date is present)

Be concise but informative. This summary will be combined with others."""

        user_prompt = f"""Summarize this chunk of {len(prs)} PRs:

{context}

Provide a concise summary highlighting key themes, patterns, and notable PRs."""

        response = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=500
        )

        return f"Chunk {chunk_num}: {response.content}"

    def _synthesize_final(self, question: str, prs: List[PullRequest], chunk_summaries: List[str]) -> str:
        """
        Synthesize final answer from chunk summaries.

        Args:
            question: Original user question
            prs: Full list of PRs (for metadata)
            chunk_summaries: Summaries from each chunk

        Returns:
            Final natural language answer
        """
        # Build context with overall stats + chunk summaries
        stats = f"""Total PRs: {len(prs)}
Date range: {min(pr.created_at for pr in prs).date()} to {max(pr.created_at for pr in prs).date()}
Unique authors: {len(set(pr.author.login for pr in prs))}

Chunk Summaries:
"""

        context = stats + "\n\n".join(chunk_summaries)

        system_prompt = """You are answering a question about GitHub pull requests.

You have access to summaries from multiple chunks of PRs. Synthesize these into a comprehensive answer.

Guidelines:
- Provide overall statistics and trends
- Highlight key themes across all PRs
- Mention specific notable PRs when relevant
- Be comprehensive but well-organized
- Use bullet points or sections for clarity"""

        user_prompt = f"""Question: {question}

Data:
{context}

Provide a comprehensive answer based on all the data."""

        response = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1500
        )

        return response.content
