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

        print(f"✓ BigQueryLoader initialized")
        print(f"  BigQuery: {project_id}.{dataset_id}")
        print(f"  Embeddings: {embedding_project_id}/{embedding_location}")

    def load_pull_requests(
        self,
        repo_name: str,
        pull_requests: List[PullRequest]
    ) -> Dict[str, int]:
        """
        Load pull requests with embeddings into BigQuery.

        This method:
        1. Extracts PR bodies for embedding
        2. Generates embeddings in batch
        3. Transforms PRs to BigQuery row format
        4. Loads data into the prs table
        5. Also loads related reviews, files, and labels

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

        # Step 1: Generate embeddings for PR bodies
        print("  1. Generating PR body embeddings...")
        pr_bodies = [pr.body or "" for pr in pull_requests]
        pr_embeddings = self.embedding_gen.generate_batch_embeddings(pr_bodies)

        # Step 2: Transform PRs to BigQuery rows
        print("  2. Transforming PRs to BigQuery format...")
        cached_at = datetime.now(timezone.utc)
        pr_rows = []

        for pr, embedding in zip(pull_requests, pr_embeddings):
            row = self._pr_to_bigquery_row(repo_name, pr, embedding, cached_at)
            pr_rows.append(row)

        # Step 3: Insert PRs into BigQuery
        print(f"  3. Inserting {len(pr_rows)} PRs into BigQuery...")
        errors = self.bq_client.insert_rows_json(self.prs_table, pr_rows)

        if errors:
            print(f"    ✗ Errors inserting PRs: {errors}")
            raise RuntimeError(f"Failed to insert PRs: {errors}")

        print(f"    ✓ Inserted {len(pr_rows)} PRs")

        # Step 4: Load related data
        review_count = self._load_reviews(repo_name, pull_requests)
        file_count = self._load_files(repo_name, pull_requests)
        label_count = self._load_labels(repo_name, pull_requests)

        return {
            "prs": len(pr_rows),
            "reviews": review_count,
            "files": file_count,
            "labels": label_count
        }

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
        Load reviews with embeddings into BigQuery.

        Extracts reviews from all PRs, generates embeddings for review bodies,
        and loads them into the reviews table.

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

        # Generate embeddings for review bodies
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

        # Insert into BigQuery
        errors = self.bq_client.insert_rows_json(self.reviews_table, review_rows)

        if errors:
            print(f"    ✗ Errors inserting reviews: {errors}")
            return 0

        print(f"    ✓ Inserted {len(review_rows)} reviews")
        return len(review_rows)

    def _load_files(
        self,
        repo_name: str,
        pull_requests: List[PullRequest]
    ) -> int:
        """
        Load file changes with embeddings into BigQuery.

        Extracts file stats from all PRs, generates embeddings for patches,
        and loads them into the files table.

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

        # Generate embeddings for patches (code diffs)
        # Only embed patches that exist (some files might not have patch content)
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

        # Insert into BigQuery
        errors = self.bq_client.insert_rows_json(self.files_table, file_rows)

        if errors:
            print(f"    ✗ Errors inserting files: {errors}")
            return 0

        print(f"    ✓ Inserted {len(file_rows)} file changes")
        return len(file_rows)

    def _load_labels(
        self,
        repo_name: str,
        pull_requests: List[PullRequest]
    ) -> int:
        """
        Load PR labels into BigQuery.

        Extracts labels from all PRs and loads them into the labels table.
        Labels don't need embeddings (they're simple keywords).

        Args:
            repo_name: Repository name
            pull_requests: List of PRs containing labels

        Returns:
            Number of label records loaded
        """
        # Collect all labels from all PRs
        label_rows = []
        cached_at = datetime.now(timezone.utc)

        for pr in pull_requests:
            for label in pr.labels:
                row = {
                    "repo_name": repo_name,
                    "pr_number": pr.number,
                    "label_name": label.name,
                    "label_color": label.color,
                    "label_description": label.description
                }
                label_rows.append(row)

        if not label_rows:
            print("  6. ⊘ No labels to load")
            return 0

        print(f"  6. Loading {len(label_rows)} labels...")

        # Insert into BigQuery
        errors = self.bq_client.insert_rows_json(self.labels_table, label_rows)

        if errors:
            print(f"    ✗ Errors inserting labels: {errors}")
            return 0

        print(f"    ✓ Inserted {len(label_rows)} labels")
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
