"""
Abstract data source interface for querying PR data.

This module defines the contract for data sources that provide access to
GitHub PR data. Implementations can use BigQuery, local cache, or other backends.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from .models import PullRequest


class PRDataSource(ABC):
    """
    Abstract interface for querying PR data.

    This interface defines the methods that any PR data source must implement.
    It abstracts away the underlying storage (BigQuery, cache, etc.) so that
    the rest of the application doesn't need to know implementation details.

    Example:
        >>> data_source = BigQueryDataSource(project="mozdata-nonprod")
        >>> prs = data_source.find_prs_by_author("alice")
        >>> print(f"Found {len(prs)} PRs by alice")
    """

    @abstractmethod
    def find_prs_by_author(
        self,
        author: str,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PullRequest]:
        """
        Find PRs authored by a specific user.

        Args:
            author: GitHub username of the PR author
            repo_name: Optional repository filter (e.g., "mozilla/bigquery-etl")
            limit: Maximum number of PRs to return (default: 100)

        Returns:
            List of PullRequest objects matching the criteria

        Example:
            >>> prs = data_source.find_prs_by_author("alice", limit=10)
            >>> print(f"Alice created {len(prs)} PRs")
        """
        pass

    @abstractmethod
    def find_prs_by_reviewer(
        self,
        reviewer: str,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PullRequest]:
        """
        Find PRs reviewed by a specific user.

        Args:
            reviewer: GitHub username of the reviewer
            repo_name: Optional repository filter
            limit: Maximum number of PRs to return (default: 100)

        Returns:
            List of PullRequest objects that were reviewed by the user

        Example:
            >>> prs = data_source.find_prs_by_reviewer("bob")
            >>> print(f"Bob reviewed {len(prs)} PRs")
        """
        pass

    @abstractmethod
    def find_prs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PullRequest]:
        """
        Find PRs merged within a date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            repo_name: Optional repository filter
            limit: Maximum number of PRs to return (default: 100)

        Returns:
            List of PullRequest objects merged in the date range

        Example:
            >>> from datetime import datetime, timedelta
            >>> last_week = datetime.now() - timedelta(days=7)
            >>> now = datetime.now()
            >>> prs = data_source.find_prs_by_date_range(last_week, now)
            >>> print(f"Merged {len(prs)} PRs last week")
        """
        pass

    @abstractmethod
    def find_prs_by_file(
        self,
        filename: str,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PullRequest]:
        """
        Find PRs that changed a specific file.

        Args:
            filename: Full file path (e.g., "src/auth/login.py")
            repo_name: Optional repository filter
            limit: Maximum number of PRs to return (default: 100)

        Returns:
            List of PullRequest objects that modified the file

        Example:
            >>> prs = data_source.find_prs_by_file("src/auth/login.py")
            >>> print(f"{len(prs)} PRs changed login.py")
        """
        pass

    @abstractmethod
    def find_prs_by_directory(
        self,
        directory: str,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PullRequest]:
        """
        Find PRs that changed files in a directory.

        Args:
            directory: Directory path (e.g., "src/auth/" or "sql/")
            repo_name: Optional repository filter
            limit: Maximum number of PRs to return (default: 100)

        Returns:
            List of PullRequest objects that modified files in the directory

        Example:
            >>> prs = data_source.find_prs_by_directory("src/auth/")
            >>> print(f"{len(prs)} PRs changed auth module")
        """
        pass

    @abstractmethod
    def semantic_search(
        self,
        query: str,
        repo_name: Optional[str] = None,
        limit: int = 10
    ) -> List[PullRequest]:
        """
        Find PRs by semantic similarity to a query.

        Uses vector embeddings to find PRs whose content is semantically
        similar to the query text, even if they don't use the exact words.

        Args:
            query: Natural language query (e.g., "authentication bug fixes")
            repo_name: Optional repository filter
            limit: Maximum number of PRs to return (default: 10)

        Returns:
            List of PullRequest objects ranked by similarity to query

        Example:
            >>> prs = data_source.semantic_search("login authentication")
            >>> print(f"Found {len(prs)} related PRs")
            >>> print(f"Most similar: {prs[0].title}")
        """
        pass

    @abstractmethod
    def get_pr_detail(
        self,
        repo_name: str,
        pr_number: int
    ) -> Optional[PullRequest]:
        """
        Get full details of a specific PR.

        Args:
            repo_name: Repository name (e.g., "mozilla/bigquery-etl")
            pr_number: PR number

        Returns:
            PullRequest object with full details, or None if not found

        Example:
            >>> pr = data_source.get_pr_detail("mozilla/bigquery-etl", 8162)
            >>> if pr:
            ...     print(f"PR #{pr.number}: {pr.title}")
            ...     print(f"Author: {pr.author.login}")
        """
        pass
