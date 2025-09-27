"""
Persistent cache for GitHub PR data to avoid duplicate fetches.

Stores PR data in JSON format organized by repository and PR number.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from .models import PullRequest


class PRCache:
    """
    Persistent cache for storing and retrieving GitHub PR data.

    Cache structure:
    cache/
    ├── mozilla_bigquery-etl/
    │   ├── pr_8162.json
    │   ├── pr_8161.json
    │   └── index.json  # metadata about cached PRs
    """

    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize the PR cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_repo_cache_dir(self, repository: str) -> Path:
        """Get cache directory for a specific repository."""
        # Replace / with _ for filesystem safety
        safe_repo_name = repository.replace("/", "_")
        repo_dir = self.cache_dir / safe_repo_name
        repo_dir.mkdir(exist_ok=True)
        return repo_dir

    def _get_pr_cache_file(self, repository: str, pr_number: int) -> Path:
        """Get cache file path for a specific PR."""
        repo_dir = self._get_repo_cache_dir(repository)
        return repo_dir / f"pr_{pr_number}.json"

    def _get_index_file(self, repository: str) -> Path:
        """Get index file path for a repository."""
        repo_dir = self._get_repo_cache_dir(repository)
        return repo_dir / "index.json"

    def _pr_to_dict(self, pr: PullRequest) -> Dict[str, Any]:
        """Convert PullRequest to dictionary for JSON storage."""
        return {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "state": pr.state.value,
            "created_at": pr.created_at.isoformat(),
            "updated_at": pr.updated_at.isoformat(),
            "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
            "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
            "author": {
                "login": pr.author.login,
                "name": pr.author.name,
                "avatar_url": pr.author.avatar_url,
                "html_url": pr.author.html_url
            },
            "html_url": pr.html_url,
            "base_branch": pr.base_branch,
            "head_branch": pr.head_branch,
            "labels": [{"name": label.name, "color": label.color, "description": label.description}
                      for label in pr.labels],
            "reviews": [{"id": review.id,
                        "user": {"login": review.user.login, "name": review.user.name,
                                "avatar_url": review.user.avatar_url, "html_url": review.user.html_url},
                        "state": review.state.value,
                        "submitted_at": review.submitted_at.isoformat(),
                        "body": review.body,
                        "html_url": review.html_url}
                       for review in pr.reviews],
            "file_stats": [{"filename": fs.filename, "additions": fs.additions,
                           "deletions": fs.deletions, "changes": fs.changes,
                           "status": fs.status, "patch": fs.patch}
                          for fs in pr.file_stats],
            "requested_reviewers": [{"login": user.login, "name": user.name,
                                    "avatar_url": user.avatar_url, "html_url": user.html_url}
                                   for user in pr.requested_reviewers],
            "assignees": [{"login": user.login, "name": user.name,
                          "avatar_url": user.avatar_url, "html_url": user.html_url}
                         for user in pr.assignees],
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "draft": pr.draft,
            "mergeable": pr.mergeable,
            "cached_at": datetime.now().isoformat()
        }

    def _dict_to_pr(self, data: Dict[str, Any]) -> PullRequest:
        """Convert dictionary back to PullRequest object."""
        from .models import PRState, User, Label, Review, ReviewState, FileStat

        # Reconstruct User objects
        author = User(
            login=data["author"]["login"],
            name=data["author"].get("name"),
            avatar_url=data["author"].get("avatar_url"),
            html_url=data["author"].get("html_url")
        )

        # Reconstruct other complex objects
        labels = [Label(name=label["name"], color=label["color"],
                       description=label.get("description")) for label in data["labels"]]

        reviews = []
        for review_data in data["reviews"]:
            review_user = User(
                login=review_data["user"]["login"],
                name=review_data["user"].get("name"),
                avatar_url=review_data["user"].get("avatar_url"),
                html_url=review_data["user"].get("html_url")
            )
            review = Review(
                id=review_data["id"],
                user=review_user,
                state=ReviewState(review_data["state"]),
                submitted_at=datetime.fromisoformat(review_data["submitted_at"]),
                body=review_data.get("body"),
                html_url=review_data.get("html_url")
            )
            reviews.append(review)

        file_stats = [FileStat(
            filename=fs["filename"],
            additions=fs["additions"],
            deletions=fs["deletions"],
            changes=fs["changes"],
            status=fs["status"],
            patch=fs.get("patch")
        ) for fs in data["file_stats"]]

        requested_reviewers = [User(
            login=user["login"], name=user.get("name"),
            avatar_url=user.get("avatar_url"), html_url=user.get("html_url")
        ) for user in data["requested_reviewers"]]

        assignees = [User(
            login=user["login"], name=user.get("name"),
            avatar_url=user.get("avatar_url"), html_url=user.get("html_url")
        ) for user in data["assignees"]]

        return PullRequest(
            number=data["number"],
            title=data["title"],
            body=data["body"],
            state=PRState(data["state"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            merged_at=datetime.fromisoformat(data["merged_at"]) if data["merged_at"] else None,
            closed_at=datetime.fromisoformat(data["closed_at"]) if data["closed_at"] else None,
            author=author,
            html_url=data["html_url"],
            base_branch=data["base_branch"],
            head_branch=data["head_branch"],
            labels=labels,
            reviews=reviews,
            file_stats=file_stats,
            requested_reviewers=requested_reviewers,
            assignees=assignees,
            additions=data["additions"],
            deletions=data["deletions"],
            changed_files=data["changed_files"],
            draft=data["draft"],
            mergeable=data.get("mergeable")
        )

    def has_pr(self, repository: str, pr_number: int) -> bool:
        """Check if a PR is already cached."""
        cache_file = self._get_pr_cache_file(repository, pr_number)
        return cache_file.exists()

    def get_pr(self, repository: str, pr_number: int) -> Optional[PullRequest]:
        """Retrieve a PR from cache."""
        cache_file = self._get_pr_cache_file(repository, pr_number)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return self._dict_to_pr(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Corrupted cache file {cache_file}: {e}")
            return None

    def store_pr(self, repository: str, pr: PullRequest) -> None:
        """Store a PR in the cache."""
        cache_file = self._get_pr_cache_file(repository, pr.number)

        try:
            data = self._pr_to_dict(pr)
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)

            # Update index
            self._update_index(repository, pr.number)

        except Exception as e:
            print(f"Warning: Failed to cache PR #{pr.number}: {e}")

    def _update_index(self, repository: str, pr_number: int) -> None:
        """Update the repository index with cached PR."""
        index_file = self._get_index_file(repository)

        # Load existing index
        index = {"cached_prs": [], "last_updated": None}
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    index = json.load(f)
            except json.JSONDecodeError:
                pass

        # Add PR to index if not already there
        if pr_number not in index["cached_prs"]:
            index["cached_prs"].append(pr_number)
            index["cached_prs"].sort()

        index["last_updated"] = datetime.now().isoformat()

        # Save updated index
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

    def get_cached_pr_numbers(self, repository: str) -> List[int]:
        """Get list of PR numbers that are cached for a repository."""
        index_file = self._get_index_file(repository)
        if not index_file.exists():
            return []

        try:
            with open(index_file, 'r') as f:
                index = json.load(f)
            return index.get("cached_prs", [])
        except json.JSONDecodeError:
            return []

    def cleanup_old_cache(self, repository: str, days: int = 30) -> None:
        """Remove cache files older than specified days."""
        repo_dir = self._get_repo_cache_dir(repository)
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for cache_file in repo_dir.glob("pr_*.json"):
            if cache_file.stat().st_mtime < cutoff:
                cache_file.unlink()
                print(f"Removed old cache file: {cache_file}")