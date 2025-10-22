"""
BigQuery implementation of PRDataSource.

This module provides a concrete implementation of the PRDataSource interface
that queries PR data from BigQuery tables.
"""

from typing import List, Optional
from datetime import datetime
from google.cloud import bigquery
from .data_source import PRDataSource
from .models import PullRequest, User, PRState


class BigQueryDataSource(PRDataSource):
    """
    BigQuery implementation of PR data source.

    Queries PR data from BigQuery tables and returns PullRequest objects.

    Example:
        >>> data_source = BigQueryDataSource(
        ...     project_id="mozdata-nonprod",
        ...     dataset_id="analysis"
        ... )
        >>> prs = data_source.find_prs_by_author("alice")
    """

    def __init__(
        self,
        project_id: str,
        dataset_id: str,
        table_prefix: str = "gkabbz_gh"
    ):
        """
        Initialize BigQuery data source.

        Args:
            project_id: GCP project ID (e.g., "mozdata-nonprod")
            dataset_id: BigQuery dataset name (e.g., "analysis")
            table_prefix: Table name prefix (default: "gkabbz_gh")
                         In production, this could be "gh" or "github_prs"

        Example:
            # Development
            >>> ds = BigQueryDataSource("mozdata-nonprod", "analysis", "gkabbz_gh")

            # Production
            >>> ds = BigQueryDataSource("moz-fx-data-shared-prod", "github_prs", "gh")
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_prefix = table_prefix
        self.client = bigquery.Client(project=project_id)

        # Table references - built from prefix
        self.prs_table = f"{project_id}.{dataset_id}.{table_prefix}_prs"
        self.reviews_table = f"{project_id}.{dataset_id}.{table_prefix}_reviews"
        self.files_table = f"{project_id}.{dataset_id}.{table_prefix}_files"
        self.labels_table = f"{project_id}.{dataset_id}.{table_prefix}_labels"

        print(f"✓ BigQueryDataSource initialized")
        print(f"  Project: {project_id}")
        print(f"  Dataset: {dataset_id}")
        print(f"  Table prefix: {table_prefix}")

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
            repo_name: Optional repository filter
            limit: Maximum number of PRs to return

        Returns:
            List of PullRequest objects
        """
        print(f"\n🔍 Searching for PRs by author: {author}")

        # Build SQL query
        #TODO: We might want to have a look up table for author. Most natural language would use someone's name e.g. for me people would ask George or George Kaberere not gkabbz (my github handle that is currently in author field)
        query = f"""
        SELECT
            repo_name,
            number,
            title,
            body,
            state,
            author,
            html_url,
            created_at,
            updated_at,
            merged_at,
            closed_at,
            base_branch,
            head_branch,
            additions,
            deletions,
            changed_files,
            draft
        FROM `{self.prs_table}`
        WHERE author = @author
        """

        # Add optional repo filter
        if repo_name:
            query += " AND repo_name = @repo_name"

        # Order by most recent first
        query += " ORDER BY created_at DESC"
        query += f" LIMIT {limit}"

        print(f"  SQL: {query[:100]}...")

        # Configure query parameters
        query_params = [
            bigquery.ScalarQueryParameter("author", "STRING", author),
        ]

        if repo_name:
            query_params.append(
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            )

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        # Execute query
        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()

        # Transform results to PullRequest objects
        prs = []
        for row in results:
            pr = self._row_to_pullrequest(row)
            prs.append(pr)

        print(f"  ✓ Found {len(prs)} PRs")
        return prs

    def _row_to_pullrequest(self, row: bigquery.Row) -> PullRequest:
        """
        Convert a BigQuery row to a PullRequest object.

        Args:
            row: BigQuery row from prs table

        Returns:
            PullRequest object
        """
        # Create author user
        author = User(login=row.author)

        # Parse state
        state = PRState(row.state)

        # Create PullRequest
        # Note: We're only loading basic PR data here, not reviews/files/labels
        # Those can be loaded separately if needed
        pr = PullRequest(
            number=row.number,
            title=row.title,
            body=row.body,
            state=state,
            created_at=row.created_at,
            updated_at=row.updated_at,
            merged_at=row.merged_at,
            closed_at=row.closed_at,
            author=author,
            html_url=row.html_url,
            base_branch=row.base_branch,
            head_branch=row.head_branch,
            additions=row.additions,
            deletions=row.deletions,
            changed_files=row.changed_files,
            draft=row.draft,
            # Empty lists for related data (can be enriched later if needed)
            labels=[],
            reviews=[],
            file_stats=[],
            requested_reviewers=[],
            assignees=[]
        )

        return pr

    def find_prs_by_reviewer(
        self,
        reviewer: str,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PullRequest]:
        """
        Find PRs reviewed by a specific user.

        This requires joining the prs table with the reviews table.
        """
        print(f"\n🔍 Searching for PRs reviewed by: {reviewer}")

        # Build SQL query with JOIN
        query = f"""
        SELECT DISTINCT
            p.repo_name,
            p.number,
            p.title,
            p.body,
            p.state,
            p.author,
            p.html_url,
            p.created_at,
            p.updated_at,
            p.merged_at,
            p.closed_at,
            p.base_branch,
            p.head_branch,
            p.additions,
            p.deletions,
            p.changed_files,
            p.draft
        FROM `{self.prs_table}` p
        JOIN `{self.reviews_table}` r
          ON p.repo_name = r.repo_name AND p.number = r.pr_number
        WHERE r.reviewer = @reviewer
        """

        if repo_name:
            query += " AND p.repo_name = @repo_name"

        query += " ORDER BY p.created_at DESC"
        query += f" LIMIT {limit}"

        print(f"  SQL: {query[:100]}...")

        # Configure query parameters
        query_params = [
            bigquery.ScalarQueryParameter("reviewer", "STRING", reviewer),
        ]

        if repo_name:
            query_params.append(
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            )

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        # Execute query
        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()

        # Transform results
        prs = []
        for row in results:
            pr = self._row_to_pullrequest(row)
            prs.append(pr)

        print(f"  ✓ Found {len(prs)} PRs")
        return prs

    def find_prs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PullRequest]:
        """
        Find PRs merged within a date range.
        """
        print(f"\n🔍 Searching for PRs merged between {start_date.date()} and {end_date.date()}")

        query = f"""
        SELECT
            repo_name,
            number,
            title,
            body,
            state,
            author,
            html_url,
            created_at,
            updated_at,
            merged_at,
            closed_at,
            base_branch,
            head_branch,
            additions,
            deletions,
            changed_files,
            draft
        FROM `{self.prs_table}`
        WHERE merged_at BETWEEN @start_date AND @end_date
        """

        if repo_name:
            query += " AND repo_name = @repo_name"

        query += " ORDER BY merged_at DESC"
        query += f" LIMIT {limit}"

        print(f"  SQL: {query[:100]}...")

        # Configure query parameters
        query_params = [
            bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date),
            bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date),
        ]

        if repo_name:
            query_params.append(
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            )

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        # Execute query
        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()

        # Transform results
        prs = []
        for row in results:
            pr = self._row_to_pullrequest(row)
            prs.append(pr)

        print(f"  ✓ Found {len(prs)} PRs")
        return prs

    def find_prs_by_file(
        self,
        filename: str,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PullRequest]:
        """
        Find PRs that changed a specific file.

        This requires joining with the files table.
        """
        print(f"\n🔍 Searching for PRs that changed file: {filename}")

        query = f"""
        SELECT DISTINCT
            p.repo_name,
            p.number,
            p.title,
            p.body,
            p.state,
            p.author,
            p.html_url,
            p.created_at,
            p.updated_at,
            p.merged_at,
            p.closed_at,
            p.base_branch,
            p.head_branch,
            p.additions,
            p.deletions,
            p.changed_files,
            p.draft
        FROM `{self.prs_table}` p
        JOIN `{self.files_table}` f
          ON p.repo_name = f.repo_name AND p.number = f.pr_number
        WHERE f.filename = @filename
        """

        if repo_name:
            query += " AND p.repo_name = @repo_name"

        query += " ORDER BY p.created_at DESC"
        query += f" LIMIT {limit}"

        print(f"  SQL: {query[:100]}...")

        # Configure query parameters
        query_params = [
            bigquery.ScalarQueryParameter("filename", "STRING", filename),
        ]

        if repo_name:
            query_params.append(
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            )

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        # Execute query
        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()

        # Transform results
        prs = []
        for row in results:
            pr = self._row_to_pullrequest(row)
            prs.append(pr)

        print(f"  ✓ Found {len(prs)} PRs")
        return prs

    def find_prs_by_directory(
        self,
        directory: str,
        repo_name: Optional[str] = None,
        limit: int = 100
    ) -> List[PullRequest]:
        """
        Find PRs that changed files in a directory.

        Uses LIKE pattern matching on filename.
        """
        print(f"\n🔍 Searching for PRs that changed directory: {directory}")

        # Ensure directory ends with /
        if not directory.endswith('/'):
            directory += '/'

        query = f"""
        SELECT DISTINCT
            p.repo_name,
            p.number,
            p.title,
            p.body,
            p.state,
            p.author,
            p.html_url,
            p.created_at,
            p.updated_at,
            p.merged_at,
            p.closed_at,
            p.base_branch,
            p.head_branch,
            p.additions,
            p.deletions,
            p.changed_files,
            p.draft
        FROM `{self.prs_table}` p
        JOIN `{self.files_table}` f
          ON p.repo_name = f.repo_name AND p.number = f.pr_number
        WHERE f.filename LIKE @directory_pattern
        """

        if repo_name:
            query += " AND p.repo_name = @repo_name"

        query += " ORDER BY p.created_at DESC"
        query += f" LIMIT {limit}"

        print(f"  SQL: {query[:100]}...")

        # Configure query parameters
        # Add % wildcard for LIKE pattern
        query_params = [
            bigquery.ScalarQueryParameter("directory_pattern", "STRING", f"{directory}%"),
        ]

        if repo_name:
            query_params.append(
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            )

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        # Execute query
        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()

        # Transform results
        prs = []
        for row in results:
            pr = self._row_to_pullrequest(row)
            prs.append(pr)

        print(f"  ✓ Found {len(prs)} PRs")
        return prs

    def semantic_search(
        self,
        query: str,
        repo_name: Optional[str] = None,
        limit: int = 10
    ) -> List[PullRequest]:
        """
        Find PRs by semantic similarity using vector embeddings.

        This uses ML_DISTANCE to compute cosine similarity between
        the query embedding and PR body embeddings.
        """
        print(f"\n🔍 Semantic search: '{query}'")

        # Step 1: Generate embedding for the query
        from .embeddings import EmbeddingGenerator
        embedding_gen = EmbeddingGenerator()
        query_embedding = embedding_gen.generate_embedding(query)

        print(f"  Generated query embedding ({len(query_embedding)} dims)")

        # Step 2: Search using vector similarity
        # ML_DISTANCE computes cosine distance (0 = identical, 2 = opposite)
        # We want smallest distances (most similar)
        sql = f"""
        SELECT
            repo_name,
            number,
            title,
            body,
            state,
            author,
            html_url,
            created_at,
            updated_at,
            merged_at,
            closed_at,
            base_branch,
            head_branch,
            additions,
            deletions,
            changed_files,
            draft,
            ML.DISTANCE(body_embedding, @query_embedding, 'COSINE') as distance
        FROM `{self.prs_table}`
        WHERE ARRAY_LENGTH(body_embedding) > 0
        """

        if repo_name:
            sql += " AND repo_name = @repo_name"

        sql += " ORDER BY distance ASC"
        sql += f" LIMIT {limit}"

        print(f"  SQL: {sql[:100]}...")

        # Configure query parameters
        query_params = [
            bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
        ]

        if repo_name:
            query_params.append(
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            )

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        # Execute query
        query_job = self.client.query(sql, job_config=job_config)
        results = query_job.result()

        # Transform results
        prs = []
        for row in results:
            pr = self._row_to_pullrequest(row)
            prs.append(pr)

        print(f"  ✓ Found {len(prs)} similar PRs")
        return prs

    def get_pr_detail(
        self,
        repo_name: str,
        pr_number: int
    ) -> Optional[PullRequest]:
        """
        Get full details of a specific PR.
        """
        print(f"\n🔍 Getting PR detail: {repo_name}#{pr_number}")

        query = f"""
        SELECT
            repo_name,
            number,
            title,
            body,
            state,
            author,
            html_url,
            created_at,
            updated_at,
            merged_at,
            closed_at,
            base_branch,
            head_branch,
            additions,
            deletions,
            changed_files,
            draft
        FROM `{self.prs_table}`
        WHERE repo_name = @repo_name AND number = @pr_number
        """

        print(f"  SQL: {query[:100]}...")

        # Configure query parameters
        query_params = [
            bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name),
            bigquery.ScalarQueryParameter("pr_number", "INT64", pr_number),
        ]

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

        # Execute query
        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()

        # Get first result (should be only one)
        for row in results:
            pr = self._row_to_pullrequest(row)
            print(f"  ✓ Found PR: {pr.title}")
            return pr

        print(f"  ✗ PR not found")
        return None
