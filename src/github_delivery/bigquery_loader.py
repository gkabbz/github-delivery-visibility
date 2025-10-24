"""
BigQuery data loader with embedding support.

This module loads GitHub PR data into BigQuery tables with vector embeddings
for semantic search capabilities.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from google.cloud import bigquery
from .models import PullRequest, Review, FileStat, Label
from .embeddings import EmbeddingGenerator


class BigQueryLoader:
    """
    Loads GitHub data into BigQuery with embeddings.

    This class handles:
    1. Generating embeddings for text content (PR body, review body, patches)
    2. Transforming data models into BigQuery row format
    3. Batch loading data into BigQuery tables

    Example:
        >>> loader = BigQueryLoader(
        ...     project_id="mozdata-nonprod",
        ...     dataset_id="analysis"
        ... )
        >>> loader.load_pull_requests(repo_name="mozilla/bigquery-etl", prs=prs)
    """

    def __init__(
        self,
        project_id: str,
        dataset_id: str,
        embedding_project_id: str = "mozdata",
        embedding_location: str = "us-west1"
    ):
        """
        Initialize the BigQuery loader.

        Args:
            project_id: GCP project for BigQuery (e.g., "mozdata-nonprod")
            dataset_id: BigQuery dataset name (e.g., "gkabbz_github")
            embedding_project_id: GCP project for embeddings (default: "mozdata")
            embedding_location: Region for embeddings (default: "us-west1")

        Note:
            Embeddings and BigQuery can use different projects if needed.
        """
        self.project_id = project_id
        self.dataset_id = dataset_id

        # Initialize BigQuery client
        self.bq_client = bigquery.Client(project=project_id)

        # Initialize embedding generator
        self.embedding_gen = EmbeddingGenerator(
            project_id=embedding_project_id,
            location=embedding_location
        )

        # Table references
        self.prs_table = f"{project_id}.{dataset_id}.gkabbz_gh_prs"
        self.reviews_table = f"{project_id}.{dataset_id}.gkabbz_gh_reviews"
        self.files_table = f"{project_id}.{dataset_id}.gkabbz_gh_files"
        self.labels_table = f"{project_id}.{dataset_id}.gkabbz_gh_labels"

        # Staging table references (with 3-day expiration)
        self.staging_prs_table = f"{project_id}.{dataset_id}.gkabbz_staging_gh_prs"
        self.staging_reviews_table = f"{project_id}.{dataset_id}.gkabbz_staging_gh_reviews"
        self.staging_files_table = f"{project_id}.{dataset_id}.gkabbz_staging_gh_files"
        self.staging_labels_table = f"{project_id}.{dataset_id}.gkabbz_staging_gh_labels"

        # Ensure staging tables exist with 3-day expiration
        self._ensure_staging_tables_exist()

        print(f"✓ BigQueryLoader initialized")
        print(f"  BigQuery: {project_id}.{dataset_id}")
        print(f"  Embeddings: {embedding_project_id}/{embedding_location}")

    def _ensure_staging_tables_exist(self):
        """
        Ensure staging tables exist with 3-day expiration.

        Staging tables have the same schema as production tables but:
        - Expire after 3 days (auto-cleanup by BigQuery)
        - Used for batch loading before MERGE to production
        - Allows troubleshooting failed backfills
        """
        from datetime import timedelta

        staging_tables = [
            (self.staging_prs_table, self.prs_table),
            (self.staging_reviews_table, self.reviews_table),
            (self.staging_files_table, self.files_table),
            (self.staging_labels_table, self.labels_table),
        ]

        for staging_table, prod_table in staging_tables:
            try:
                # Check if staging table exists
                self.bq_client.get_table(staging_table)
            except Exception:
                # Table doesn't exist, create it with same schema as production
                try:
                    prod_table_ref = self.bq_client.get_table(prod_table)

                    # Create staging table with same schema
                    staging_table_ref = bigquery.Table(staging_table, schema=prod_table_ref.schema)

                    # Set 3-day expiration
                    staging_table_ref.expires = datetime.now(timezone.utc) + timedelta(days=3)

                    # Copy partitioning and clustering from production table
                    if prod_table_ref.time_partitioning:
                        staging_table_ref.time_partitioning = prod_table_ref.time_partitioning
                    if prod_table_ref.clustering_fields:
                        staging_table_ref.clustering_fields = prod_table_ref.clustering_fields

                    self.bq_client.create_table(staging_table_ref)
                    print(f"  Created staging table: {staging_table.split('.')[-1]}")
                except Exception as e:
                    print(f"  Warning: Could not create staging table {staging_table}: {e}")

    def load_pull_requests(
        self,
        repo_name: str,
        pull_requests: List[PullRequest]
    ) -> Dict[str, int]:
        """
        Load pull requests with embeddings into BigQuery.

        This method:
        1. Checks for existing PRs and filters to only new ones
        2. Generates embeddings for new PR bodies only
        3. Transforms PRs to BigQuery row format
        4. Loads new PRs into the prs table
        5. Checks for existing reviews/files/labels and loads only new ones

        This is idempotent - you can safely re-run with the same date range.

        Args:
            repo_name: Repository name (e.g., "mozilla/bigquery-etl")
            pull_requests: List of PullRequest objects to load

        Returns:
            Dict with counts of loaded records:
            {"prs": 5, "reviews": 12, "files": 43, "labels": 8}

        Example:
            >>> result = loader.load_pull_requests(
            ...     repo_name="mozilla/bigquery-etl",
            ...     pull_requests=[pr1, pr2, pr3]
            ... )
            >>> print(f"Loaded {result['prs']} PRs")
        """
        if not pull_requests:
            print("  ⊘ No pull requests to load")
            return {"prs": 0, "reviews": 0, "files": 0, "labels": 0}

        print(f"\n📥 Loading {len(pull_requests)} PRs for {repo_name}")

        # Step 1: Generate embeddings for ALL PRs
        print("  1. Generating PR body embeddings...")
        pr_bodies = [pr.body or "" for pr in pull_requests]
        pr_embeddings = self.embedding_gen.generate_batch_embeddings(pr_bodies)

        # Step 2: Use MERGE to upsert PRs (handles both INSERT and UPDATE)
        print("  2. Upserting PRs to BigQuery using MERGE...")
        cached_at = datetime.now(timezone.utc)

        upserted_count = self._merge_prs(repo_name, pull_requests, pr_embeddings, cached_at)
        print(f"    ✓ Upserted {upserted_count} PRs (inserted new + updated existing)")

        # Step 5: Load related data (reviews, files, labels)
        # Each method checks for existing records and only loads new ones
        print("  5. Loading reviews/files/labels...")
        review_count = self._load_reviews(repo_name, pull_requests)
        file_count = self._load_files(repo_name, pull_requests)
        label_count = self._load_labels(repo_name, pull_requests)

        return {
            "prs_upserted": upserted_count,
            "reviews": review_count,
            "files": file_count,
            "labels": label_count
        }

    def _get_existing_pr_numbers(self, repo_name: str) -> set:
        """
        Query BigQuery to get existing PR numbers for a repository.

        Args:
            repo_name: Repository name (e.g., 'mozilla/bigquery-etl')

        Returns:
            Set of existing PR numbers
        """
        query = """
        SELECT number
        FROM `{table}`
        WHERE repo_name = @repo_name
        """.format(table=self.prs_table)

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            ]
        )

        try:
            results = self.bq_client.query(query, job_config=job_config).result()
            existing_numbers = {row.number for row in results}
            return existing_numbers
        except Exception as e:
            # If table doesn't exist yet or query fails, return empty set
            print(f"     Could not query existing PRs (table may not exist): {e}")
            return set()

    def _get_existing_review_ids(self, repo_name: str) -> set:
        """
        Query BigQuery to get existing review IDs for a repository.

        Args:
            repo_name: Repository name (e.g., 'mozilla/bigquery-etl')

        Returns:
            Set of existing review IDs
        """
        query = """
        SELECT review_id
        FROM `{table}`
        WHERE repo_name = @repo_name
        """.format(table=self.reviews_table)

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            ]
        )

        try:
            results = self.bq_client.query(query, job_config=job_config).result()
            existing_ids = {row.review_id for row in results}
            return existing_ids
        except Exception as e:
            # If table doesn't exist yet or query fails, return empty set
            print(f"     Could not query existing reviews (table may not exist): {e}")
            return set()

    def _get_existing_files(self, repo_name: str) -> set:
        """
        Query BigQuery to get existing file records for a repository.

        Args:
            repo_name: Repository name (e.g., 'mozilla/bigquery-etl')

        Returns:
            Set of (pr_number, filename) tuples representing existing file records
        """
        query = """
        SELECT pr_number, filename
        FROM `{table}`
        WHERE repo_name = @repo_name
        """.format(table=self.files_table)

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            ]
        )

        try:
            results = self.bq_client.query(query, job_config=job_config).result()
            existing_files = {(row.pr_number, row.filename) for row in results}
            return existing_files
        except Exception as e:
            # If table doesn't exist yet or query fails, return empty set
            print(f"     Could not query existing files (table may not exist): {e}")
            return set()

    def _get_existing_labels(self, repo_name: str) -> set:
        """
        Query BigQuery to get existing label records for a repository.

        Args:
            repo_name: Repository name (e.g., 'mozilla/bigquery-etl')

        Returns:
            Set of (pr_number, label_name) tuples representing existing label records
        """
        query = """
        SELECT pr_number, label_name
        FROM `{table}`
        WHERE repo_name = @repo_name
        """.format(table=self.labels_table)

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("repo_name", "STRING", repo_name)
            ]
        )

        try:
            results = self.bq_client.query(query, job_config=job_config).result()
            existing_labels = {(row.pr_number, row.label_name) for row in results}
            return existing_labels
        except Exception as e:
            # If table doesn't exist yet or query fails, return empty set
            print(f"     Could not query existing labels (table may not exist): {e}")
            return set()

    def _merge_prs(
        self,
        repo_name: str,
        pull_requests: List[PullRequest],
        embeddings: List[Optional[List[float]]],
        cached_at: datetime
    ) -> int:
        """
        Upsert PRs to BigQuery using staging table + MERGE pattern.

        This approach avoids streaming buffer conflicts by:
        1. Loading all PRs to staging table (batch load)
        2. MERGEing from staging to production (single query with deduplication)

        Args:
            repo_name: Repository name
            pull_requests: List of PRs to upsert
            embeddings: List of embeddings (one per PR)
            cached_at: Timestamp when data was collected

        Returns:
            Number of PRs upserted
        """
        if not pull_requests:
            return 0

        print(f"     Loading {len(pull_requests)} PRs to staging table...")

        # Step 1: Transform PRs to rows
        pr_rows = []
        for pr, embedding in zip(pull_requests, embeddings):
            row = self._pr_to_bigquery_row(repo_name, pr, embedding, cached_at)
            pr_rows.append(row)

        # Step 2: Batch load to staging table
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",  # Append to staging (3-day expiry handles cleanup)
        )

        load_job = self.bq_client.load_table_from_json(
            pr_rows,
            self.staging_prs_table,
            job_config=job_config
        )
        load_job.result()  # Wait for load to complete

        print(f"     Merging from staging to production...")

        # Step 3: MERGE from staging to production with deduplication
        # Deduplication: If multiple rows for same PR exist in staging, take most recent cached_at
        merge_query = """
        MERGE `{prod_table}` T
        USING (
            SELECT * EXCEPT(row_num)
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY repo_name, number ORDER BY cached_at DESC) as row_num
                FROM `{staging_table}`
                WHERE repo_name = '{repo_name}'
            )
            WHERE row_num = 1
        ) S
        ON T.repo_name = S.repo_name AND T.number = S.number
        WHEN MATCHED THEN
            UPDATE SET
                title = S.title,
                body = S.body,
                body_embedding = S.body_embedding,
                state = S.state,
                author = S.author,
                html_url = S.html_url,
                created_at = S.created_at,
                updated_at = S.updated_at,
                merged_at = S.merged_at,
                closed_at = S.closed_at,
                base_branch = S.base_branch,
                head_branch = S.head_branch,
                additions = S.additions,
                deletions = S.deletions,
                changed_files = S.changed_files,
                draft = S.draft,
                cached_at = S.cached_at
        WHEN NOT MATCHED THEN
            INSERT (
                repo_name, number, title, body, body_embedding, state, author, html_url,
                created_at, updated_at, merged_at, closed_at,
                base_branch, head_branch, additions, deletions, changed_files, draft, cached_at
            )
            VALUES (
                S.repo_name, S.number, S.title, S.body, S.body_embedding, S.state, S.author, S.html_url,
                S.created_at, S.updated_at, S.merged_at, S.closed_at,
                S.base_branch, S.head_branch, S.additions, S.deletions, S.changed_files, S.draft, S.cached_at
            )
        """.format(
            prod_table=self.prs_table,
            staging_table=self.staging_prs_table,
            repo_name=repo_name
        )

        merge_job = self.bq_client.query(merge_query)
        merge_job.result()  # Wait for MERGE to complete

        return len(pull_requests)

    def _pr_to_bigquery_row(
        self,
        repo_name: str,
        pr: PullRequest,
        embedding: Optional[List[float]],
        cached_at: datetime
    ) -> Dict[str, Any]:
        """
        Transform a PullRequest to BigQuery row format.

        Maps PullRequest fields to the schema defined in prs.yaml.

        Args:
            repo_name: Repository name
            pr: PullRequest object
            embedding: 768-dimensional embedding (or None if body was empty)
            cached_at: Timestamp when data was collected

        Returns:
            Dictionary matching BigQuery schema
        """
        return {
            # Identity
            "repo_name": repo_name,
            "number": pr.number,

            # Content
            "title": pr.title,
            "body": pr.body,
            "body_embedding": embedding or [],  # Empty array if no embedding

            # Metadata
            "state": pr.state.value,
            "author": pr.author.login,
            "html_url": pr.html_url,

            # Timestamps
            "created_at": pr.created_at.isoformat(),
            "updated_at": pr.updated_at.isoformat(),
            "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
            "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,

            # Branch info
            "base_branch": pr.base_branch,
            "head_branch": pr.head_branch,

            # Size metrics
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,

            # Flags
            "draft": pr.draft,

            # Cache tracking
            "cached_at": cached_at.isoformat()
        }

    def _load_reviews(
        self,
        repo_name: str,
        pull_requests: List[PullRequest]
    ) -> int:
        """
        Load reviews with embeddings into BigQuery using staging table + MERGE.

        Extracts reviews from all PRs, generates embeddings for review bodies,
        and loads them into the reviews table via staging table to avoid streaming buffer issues.

        Args:
            repo_name: Repository name
            pull_requests: List of PRs containing reviews

        Returns:
            Number of reviews loaded
        """
        # Collect all reviews from all PRs
        all_reviews = []
        pr_numbers = []

        for pr in pull_requests:
            for review in pr.reviews:
                all_reviews.append(review)
                pr_numbers.append(pr.number)

        if not all_reviews:
            print("  4. ⊘ No reviews to load")
            return 0

        print(f"  4. Loading {len(all_reviews)} reviews...")

        # Generate embeddings for ALL review bodies
        print(f"     Generating review body embeddings...")
        review_bodies = [review.body or "" for review in all_reviews]
        review_embeddings = self.embedding_gen.generate_batch_embeddings(review_bodies)

        # Transform to BigQuery rows
        cached_at = datetime.now(timezone.utc)
        review_rows = []

        for review, pr_number, embedding in zip(all_reviews, pr_numbers, review_embeddings):
            row = {
                "repo_name": repo_name,
                "pr_number": pr_number,
                "review_id": review.id,
                "reviewer": review.user.login,
                "state": review.state.value,
                "body": review.body,
                "body_embedding": embedding or [],
                "submitted_at": review.submitted_at.isoformat(),
                "html_url": review.html_url,
                "cached_at": cached_at.isoformat()
            }
            review_rows.append(row)

        # Load to staging table
        print(f"     Loading {len(review_rows)} reviews to staging table...")
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
        )

        load_job = self.bq_client.load_table_from_json(
            review_rows,
            self.staging_reviews_table,
            job_config=job_config
        )
        load_job.result()

        # MERGE from staging to production with deduplication
        print(f"     Merging from staging to production...")
        merge_query = f"""
        MERGE `{self.reviews_table}` T
        USING (
            SELECT * EXCEPT(row_num)
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY repo_name, review_id ORDER BY cached_at DESC) as row_num
                FROM `{self.staging_reviews_table}`
                WHERE repo_name = '{repo_name}'
            )
            WHERE row_num = 1
        ) S
        ON T.repo_name = S.repo_name AND T.review_id = S.review_id
        WHEN MATCHED THEN
            UPDATE SET
                pr_number = S.pr_number,
                reviewer = S.reviewer,
                state = S.state,
                body = S.body,
                body_embedding = S.body_embedding,
                submitted_at = S.submitted_at,
                html_url = S.html_url,
                cached_at = S.cached_at
        WHEN NOT MATCHED THEN
            INSERT (repo_name, pr_number, review_id, reviewer, state, body, body_embedding, submitted_at, html_url, cached_at)
            VALUES (S.repo_name, S.pr_number, S.review_id, S.reviewer, S.state, S.body, S.body_embedding, S.submitted_at, S.html_url, S.cached_at)
        """

        merge_job = self.bq_client.query(merge_query)
        merge_job.result()

        print(f"    ✓ Upserted {len(review_rows)} reviews")
        return len(review_rows)

    def _load_files(
        self,
        repo_name: str,
        pull_requests: List[PullRequest]
    ) -> int:
        """
        Load file changes with embeddings into BigQuery using staging table + MERGE.

        Extracts file stats from all PRs, generates embeddings for patches,
        and loads them into the files table via staging table to avoid streaming buffer issues.

        Args:
            repo_name: Repository name
            pull_requests: List of PRs containing file stats

        Returns:
            Number of file records loaded
        """
        # Collect all file stats from all PRs
        all_files = []
        pr_numbers = []

        for pr in pull_requests:
            for file_stat in pr.file_stats:
                all_files.append(file_stat)
                pr_numbers.append(pr.number)

        if not all_files:
            print("  5. ⊘ No file changes to load")
            return 0

        print(f"  5. Loading {len(all_files)} file changes...")

        # Generate embeddings for ALL patches (code diffs)
        print(f"     Generating patch embeddings...")
        patches = [file_stat.patch or "" for file_stat in all_files]
        patch_embeddings = self.embedding_gen.generate_batch_embeddings(patches)

        # Transform to BigQuery rows
        cached_at = datetime.now(timezone.utc)
        file_rows = []

        for file_stat, pr_number, embedding in zip(all_files, pr_numbers, patch_embeddings):
            row = {
                "repo_name": repo_name,
                "pr_number": pr_number,
                "filename": file_stat.filename,
                "additions": file_stat.additions,
                "deletions": file_stat.deletions,
                "status": file_stat.status,
                "patch": file_stat.patch,
                "patch_embedding": embedding or [],
                "patch_truncated": False,  # GitHub API doesn't indicate truncation in our cache
                "cached_at": cached_at.isoformat()
            }
            file_rows.append(row)

        # Load to staging table
        print(f"     Loading {len(file_rows)} file changes to staging table...")
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
        )

        load_job = self.bq_client.load_table_from_json(
            file_rows,
            self.staging_files_table,
            job_config=job_config
        )
        load_job.result()

        # MERGE from staging to production with deduplication
        print(f"     Merging from staging to production...")
        merge_query = f"""
        MERGE `{self.files_table}` T
        USING (
            SELECT * EXCEPT(row_num)
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY repo_name, pr_number, filename ORDER BY cached_at DESC) as row_num
                FROM `{self.staging_files_table}`
                WHERE repo_name = '{repo_name}'
            )
            WHERE row_num = 1
        ) S
        ON T.repo_name = S.repo_name AND T.pr_number = S.pr_number AND T.filename = S.filename
        WHEN MATCHED THEN
            UPDATE SET
                additions = S.additions,
                deletions = S.deletions,
                status = S.status,
                patch = S.patch,
                patch_embedding = S.patch_embedding,
                patch_truncated = S.patch_truncated,
                cached_at = S.cached_at
        WHEN NOT MATCHED THEN
            INSERT (repo_name, pr_number, filename, additions, deletions, status, patch, patch_embedding, patch_truncated, cached_at)
            VALUES (S.repo_name, S.pr_number, S.filename, S.additions, S.deletions, S.status, S.patch, S.patch_embedding, S.patch_truncated, S.cached_at)
        """

        merge_job = self.bq_client.query(merge_query)
        merge_job.result()

        print(f"    ✓ Upserted {len(file_rows)} file changes")
        return len(file_rows)

    def _load_labels(
        self,
        repo_name: str,
        pull_requests: List[PullRequest]
    ) -> int:
        """
        Load PR labels into BigQuery using staging table + MERGE.

        Extracts labels from all PRs and loads them into the labels table
        via staging table to avoid streaming buffer issues.
        Labels don't need embeddings (they're simple keywords).

        Args:
            repo_name: Repository name
            pull_requests: List of PRs containing labels

        Returns:
            Number of label records loaded
        """
        # Collect all labels from all PRs
        all_label_tuples = []  # (pr_number, label_name, label_color, label_description)

        for pr in pull_requests:
            for label in pr.labels:
                all_label_tuples.append((pr.number, label.name, label.color, label.description))

        if not all_label_tuples:
            print("  6. ⊘ No labels to load")
            return 0

        print(f"  6. Loading {len(all_label_tuples)} labels...")

        # Transform to BigQuery rows
        label_rows = []
        for pr_number, label_name, label_color, label_description in all_label_tuples:
            row = {
                "repo_name": repo_name,
                "pr_number": pr_number,
                "label_name": label_name,
                "label_color": label_color,
                "label_description": label_description
            }
            label_rows.append(row)

        # Load to staging table
        print(f"     Loading {len(label_rows)} labels to staging table...")
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
        )

        load_job = self.bq_client.load_table_from_json(
            label_rows,
            self.staging_labels_table,
            job_config=job_config
        )
        load_job.result()

        # MERGE from staging to production with deduplication
        print(f"     Merging from staging to production...")
        merge_query = f"""
        MERGE `{self.labels_table}` T
        USING (
            SELECT * EXCEPT(row_num)
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY repo_name, pr_number, label_name ORDER BY repo_name) as row_num
                FROM `{self.staging_labels_table}`
                WHERE repo_name = '{repo_name}'
            )
            WHERE row_num = 1
        ) S
        ON T.repo_name = S.repo_name AND T.pr_number = S.pr_number AND T.label_name = S.label_name
        WHEN MATCHED THEN
            UPDATE SET
                label_color = S.label_color,
                label_description = S.label_description
        WHEN NOT MATCHED THEN
            INSERT (repo_name, pr_number, label_name, label_color, label_description)
            VALUES (S.repo_name, S.pr_number, S.label_name, S.label_color, S.label_description)
        """

        merge_job = self.bq_client.query(merge_query)
        merge_job.result()

        print(f"    ✓ Upserted {len(label_rows)} labels")
        return len(label_rows)

    def get_table_row_counts(self) -> Dict[str, int]:
        """
        Get current row counts for all tables.

        Useful for verifying data was loaded correctly.

        Returns:
            Dict with table names and row counts:
            {"prs": 100, "reviews": 250, "files": 800, "labels": 150}
        """
        counts = {}

        for table_name, table_ref in [
            ("prs", self.prs_table),
            ("reviews", self.reviews_table),
            ("files", self.files_table),
            ("labels", self.labels_table)
        ]:
            query = f"SELECT COUNT(*) as count FROM `{table_ref}`"
            result = self.bq_client.query(query).result()
            count = list(result)[0].count
            counts[table_name] = count

        return counts
