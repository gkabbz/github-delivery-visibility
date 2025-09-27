"""
Data models for GitHub delivery visibility.

Defines the core data structures for representing GitHub PRs, reviews, and metadata
used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class PRState(Enum):
    """Pull request state."""
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class ReviewState(Enum):
    """Review state."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"
    DISMISSED = "DISMISSED"


@dataclass
class User:
    """Represents a GitHub user."""
    login: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None

    @classmethod
    def from_github_data(cls, data: Dict[str, Any]) -> 'User':
        """Create User from GitHub API response."""
        return cls(
            login=data['login'],
            name=data.get('name'),
            avatar_url=data.get('avatar_url'),
            html_url=data.get('html_url')
        )


@dataclass
class Label:
    """Represents a GitHub label."""
    name: str
    color: str
    description: Optional[str] = None

    @classmethod
    def from_github_data(cls, data: Dict[str, Any]) -> 'Label':
        """Create Label from GitHub API response."""
        return cls(
            name=data['name'],
            color=data['color'],
            description=data.get('description')
        )


@dataclass
class FileStat:
    """Represents file change statistics."""
    filename: str
    additions: int
    deletions: int
    changes: int
    status: str  # added, deleted, modified, renamed
    patch: Optional[str] = None  # code diff content for public repos

    @property
    def directory_prefix(self) -> str:
        """Get the directory prefix for categorization."""
        if '/' not in self.filename:
            return ""
        return self.filename.split('/')[0] + '/'

    @classmethod
    def from_github_data(cls, data: Dict[str, Any]) -> 'FileStat':
        """Create FileStat from GitHub API response."""
        return cls(
            filename=data['filename'],
            additions=data['additions'],
            deletions=data['deletions'],
            changes=data['changes'],
            status=data['status'],
            patch=data.get('patch')  # Include patch content if available
        )


@dataclass
class Review:
    """Represents a GitHub PR review."""
    id: int
    user: User
    state: ReviewState
    submitted_at: datetime
    body: Optional[str] = None
    html_url: Optional[str] = None

    @classmethod
    def from_github_data(cls, data: Dict[str, Any]) -> 'Review':
        """Create Review from GitHub API response."""
        submitted_at = datetime.fromisoformat(data['submitted_at'].replace('Z', '+00:00'))
        return cls(
            id=data['id'],
            user=User.from_github_data(data['user']),
            state=ReviewState(data['state']),
            submitted_at=submitted_at,
            body=data.get('body'),
            html_url=data.get('html_url')
        )


@dataclass
class PullRequest:
    """Represents a GitHub Pull Request with all relevant metadata."""
    number: int
    title: str
    body: Optional[str]
    state: PRState
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime]
    closed_at: Optional[datetime]
    author: User
    html_url: str
    base_branch: str
    head_branch: str
    labels: List[Label] = field(default_factory=list)
    reviews: List[Review] = field(default_factory=list)
    file_stats: List[FileStat] = field(default_factory=list)
    requested_reviewers: List[User] = field(default_factory=list)
    assignees: List[User] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    draft: bool = False
    mergeable: Optional[bool] = None

    @property
    def is_merged(self) -> bool:
        """Check if PR is merged."""
        return self.merged_at is not None

    @property
    def size_category(self) -> str:
        """Categorize PR by size."""
        total_changes = self.additions + self.deletions
        if total_changes <= 10:
            return "XS"
        elif total_changes <= 50:
            return "S"
        elif total_changes <= 200:
            return "M"
        elif total_changes <= 500:
            return "L"
        else:
            return "XL"

    @property
    def directory_prefixes(self) -> List[str]:
        """Get unique directory prefixes from changed files."""
        prefixes = set()
        for file_stat in self.file_stats:
            prefix = file_stat.directory_prefix
            if prefix:
                prefixes.add(prefix)
        return sorted(list(prefixes))

    @property
    def age_days(self) -> int:
        """Get age of PR in days."""
        return (datetime.now().replace(tzinfo=self.created_at.tzinfo) - self.created_at).days

    @property
    def has_pending_reviews(self) -> bool:
        """Check if PR has pending reviews."""
        return len(self.requested_reviewers) > 0

    @property
    def latest_review_state(self) -> Optional[ReviewState]:
        """Get the state of the most recent review."""
        if not self.reviews:
            return None
        return max(self.reviews, key=lambda r: r.submitted_at).state

    def is_waiting_for_user(self, username: str) -> bool:
        """Check if PR is waiting for a specific user's review."""
        return any(reviewer.login == username for reviewer in self.requested_reviewers)

    @classmethod
    def from_github_data(cls, data: Dict[str, Any]) -> 'PullRequest':
        """Create PullRequest from GitHub API response."""
        created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))

        merged_at = None
        if data.get('merged_at'):
            merged_at = datetime.fromisoformat(data['merged_at'].replace('Z', '+00:00'))

        closed_at = None
        if data.get('closed_at'):
            closed_at = datetime.fromisoformat(data['closed_at'].replace('Z', '+00:00'))

        # Determine state
        if merged_at:
            state = PRState.MERGED
        elif data['state'] == 'closed':
            state = PRState.CLOSED
        else:
            state = PRState.OPEN

        # Parse labels
        labels = [Label.from_github_data(label_data) for label_data in data.get('labels', [])]

        # Parse requested reviewers
        requested_reviewers = [
            User.from_github_data(reviewer_data)
            for reviewer_data in data.get('requested_reviewers', [])
        ]

        # Parse assignees
        assignees = [
            User.from_github_data(assignee_data)
            for assignee_data in data.get('assignees', [])
        ]

        return cls(
            number=data['number'],
            title=data['title'],
            body=data.get('body'),
            state=state,
            created_at=created_at,
            updated_at=updated_at,
            merged_at=merged_at,
            closed_at=closed_at,
            author=User.from_github_data(data['user']),
            html_url=data['html_url'],
            base_branch=data['base']['ref'],
            head_branch=data['head']['ref'],
            labels=labels,
            requested_reviewers=requested_reviewers,
            assignees=assignees,
            additions=data.get('additions', 0),
            deletions=data.get('deletions', 0),
            changed_files=data.get('changed_files', 0),
            draft=data.get('draft', False),
            mergeable=data.get('mergeable')
        )


@dataclass
class DigestTheme:
    """Represents a categorized theme in a digest."""
    name: str
    pull_requests: List[PullRequest] = field(default_factory=list)
    description: Optional[str] = None

    @property
    def pr_count(self) -> int:
        """Number of PRs in this theme."""
        return len(self.pull_requests)

    @property
    def contributors(self) -> List[str]:
        """List of unique contributors for this theme."""
        return list(set(pr.author.login for pr in self.pull_requests))

    @property
    def total_changes(self) -> int:
        """Total lines changed across all PRs in theme."""
        return sum(pr.additions + pr.deletions for pr in self.pull_requests)


@dataclass
class DigestStats:
    """Statistics for a digest period."""
    total_merged_prs: int
    total_contributors: int
    total_additions: int
    total_deletions: int
    most_active_contributors: List[tuple[str, int]]  # (username, pr_count)
    most_changed_directories: List[tuple[str, int]]  # (directory, change_count)
    average_pr_size: float

    @classmethod
    def from_pull_requests(cls, pull_requests: List[PullRequest]) -> 'DigestStats':
        """Calculate stats from a list of pull requests."""
        if not pull_requests:
            return cls(
                total_merged_prs=0,
                total_contributors=0,
                total_additions=0,
                total_deletions=0,
                most_active_contributors=[],
                most_changed_directories=[],
                average_pr_size=0.0
            )

        # Count contributors
        contributor_counts = {}
        directory_changes = {}
        total_additions = 0
        total_deletions = 0

        for pr in pull_requests:
            # Count contributor activity
            contributor_counts[pr.author.login] = contributor_counts.get(pr.author.login, 0) + 1

            # Count directory changes
            for prefix in pr.directory_prefixes:
                changes = pr.additions + pr.deletions
                directory_changes[prefix] = directory_changes.get(prefix, 0) + changes

            total_additions += pr.additions
            total_deletions += pr.deletions

        # Sort contributors by PR count
        most_active = sorted(contributor_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Sort directories by change count
        most_changed_dirs = sorted(directory_changes.items(), key=lambda x: x[1], reverse=True)[:5]

        # Calculate average PR size
        avg_size = (total_additions + total_deletions) / len(pull_requests) if pull_requests else 0

        return cls(
            total_merged_prs=len(pull_requests),
            total_contributors=len(contributor_counts),
            total_additions=total_additions,
            total_deletions=total_deletions,
            most_active_contributors=most_active,
            most_changed_directories=most_changed_dirs,
            average_pr_size=avg_size
        )