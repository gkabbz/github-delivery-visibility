"""
Theming and categorization system for GitHub PRs.

Intelligently categorizes pull requests based on file paths, labels, and content
with specific optimizations for mozilla/bigquery-etl repository structure.
"""

import re
from typing import List, Dict, Optional, Set
from collections import defaultdict
from .models import PullRequest, DigestTheme, Label


class Themer:
    """
    Categorizes pull requests into meaningful themes for digest generation.

    Uses a combination of directory structure analysis, label inspection,
    and title parsing to group related changes together.
    """

    def __init__(self, config: Dict):
        """
        Initialize the themer with configuration.

        Args:
            config: Configuration dictionary with categorization rules
        """
        self.directory_themes = config.get('categorization', {}).get('directory_themes', {})
        self.label_themes = config.get('categorization', {}).get('label_themes', {})
        self.max_prs_per_theme = config.get('formatting', {}).get('max_prs_per_theme', 8)

    def categorize_pull_requests(self, pull_requests: List[PullRequest]) -> List[DigestTheme]:
        """
        Categorize a list of pull requests into themes.

        Args:
            pull_requests: List of PullRequest objects to categorize

        Returns:
            List of DigestTheme objects with categorized PRs
        """
        if not pull_requests:
            return []

        # Group PRs by theme
        theme_groups = defaultdict(list)

        for pr in pull_requests:
            theme_name = self._determine_theme(pr)
            theme_groups[theme_name].append(pr)

        # Create DigestTheme objects
        themes = []
        for theme_name, prs in theme_groups.items():
            # Sort PRs within theme by merge time (most recent first) or creation time
            prs.sort(key=lambda p: p.merged_at or p.created_at, reverse=True)

            theme = DigestTheme(
                name=theme_name,
                pull_requests=prs,
                description=self._get_theme_description(theme_name, prs)
            )
            themes.append(theme)

        # Sort themes by PR count (most active first)
        themes.sort(key=lambda t: t.pr_count, reverse=True)

        return themes

    def _determine_theme(self, pr: PullRequest) -> str:
        """
        Determine the theme for a single pull request.

        Args:
            pr: PullRequest to categorize

        Returns:
            Theme name
        """
        # First, try directory-based categorization
        directory_theme = self._get_directory_theme(pr)
        if directory_theme:
            return directory_theme

        # Second, try label-based categorization
        label_theme = self._get_label_theme(pr)
        if label_theme:
            return label_theme

        # Third, try title-based categorization
        title_theme = self._get_title_theme(pr)
        if title_theme:
            return title_theme

        # Default fallback
        return "Other Changes"

    def _get_directory_theme(self, pr: PullRequest) -> Optional[str]:
        """
        Get theme based on directory structure.

        Args:
            pr: PullRequest to analyze

        Returns:
            Theme name or None
        """
        # Count directory matches for each theme
        theme_scores = defaultdict(int)

        for file_stat in pr.file_stats:
            filename = file_stat.filename

            # Check each directory theme pattern
            for dir_pattern, theme_name in self.directory_themes.items():
                if filename.startswith(dir_pattern):
                    # Weight by file size (more changes = higher score)
                    theme_scores[theme_name] += file_stat.additions + file_stat.deletions + 1

        if not theme_scores:
            return None

        # Return theme with highest score
        return max(theme_scores.items(), key=lambda x: x[1])[0]

    def _get_label_theme(self, pr: PullRequest) -> Optional[str]:
        """
        Get theme based on PR labels.

        Args:
            pr: PullRequest to analyze

        Returns:
            Theme name or None
        """
        for label in pr.labels:
            if label.name in self.label_themes:
                return self.label_themes[label.name]

        return None

    def _get_title_theme(self, pr: PullRequest) -> Optional[str]:
        """
        Get theme based on PR title analysis.

        Args:
            pr: PullRequest to analyze

        Returns:
            Theme name or None
        """
        title = pr.title.lower()

        # BigQuery-ETL specific patterns
        if any(keyword in title for keyword in ['sql', 'query', 'dataset', 'table']):
            return "SQL & Data Products"

        if any(keyword in title for keyword in ['dag', 'airflow', 'pipeline', 'etl']):
            return "Pipeline Infrastructure"

        if any(keyword in title for keyword in ['test', 'testing', 'pytest', 'unittest']):
            return "Testing & Quality"

        if any(keyword in title for keyword in ['doc', 'documentation', 'readme', 'comment']):
            return "Documentation"

        if any(keyword in title for keyword in ['fix', 'bug', 'error', 'issue']):
            return "Bug Fixes"

        if any(keyword in title for keyword in ['feat', 'feature', 'add', 'new']):
            return "New Features"

        if any(keyword in title for keyword in ['update', 'upgrade', 'bump', 'dependency']):
            return "Dependencies & Updates"

        if any(keyword in title for keyword in ['refactor', 'cleanup', 'improve', 'optimize']):
            return "Code Improvements"

        if any(keyword in title for keyword in ['ci', 'cd', 'github', 'action', 'workflow']):
            return "CI/CD & Infrastructure"

        return None

    def _get_theme_description(self, theme_name: str, prs: List[PullRequest]) -> Optional[str]:
        """
        Generate a description for a theme based on its PRs.

        Args:
            theme_name: Name of the theme
            prs: List of PRs in this theme

        Returns:
            Theme description or None
        """
        if not prs:
            return None

        pr_count = len(prs)
        contributors = list(set(pr.author.login for pr in prs))
        total_changes = sum(pr.additions + pr.deletions for pr in prs)

        # Get most common file extensions or directories
        common_paths = self._get_common_paths(prs)

        description_parts = []

        if pr_count == 1:
            description_parts.append(f"1 PR")
        else:
            description_parts.append(f"{pr_count} PRs")

        if len(contributors) == 1:
            description_parts.append(f"by {contributors[0]}")
        else:
            description_parts.append(f"by {len(contributors)} contributors")

        if total_changes > 0:
            description_parts.append(f"({total_changes:,} lines changed)")

        if common_paths:
            description_parts.append(f"in {', '.join(common_paths[:2])}")

        return " ".join(description_parts)

    def _get_common_paths(self, prs: List[PullRequest]) -> List[str]:
        """
        Get the most common file paths or directories across PRs.

        Args:
            prs: List of PRs to analyze

        Returns:
            List of common path patterns
        """
        path_counts = defaultdict(int)

        for pr in prs:
            directories = set()
            for file_stat in pr.file_stats:
                # Extract directory or file pattern
                filename = file_stat.filename
                if '/' in filename:
                    # Get first directory
                    directories.add(filename.split('/')[0])
                else:
                    # Get file extension
                    if '.' in filename:
                        ext = filename.split('.')[-1]
                        directories.add(f"*.{ext}")

            for directory in directories:
                path_counts[directory] += 1

        # Return top paths
        sorted_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)
        return [path for path, count in sorted_paths[:5]]

    def get_hotspots(self, pull_requests: List[PullRequest]) -> List[tuple[str, int]]:
        """
        Identify hotspots (directories with most activity) in the given PRs.

        Args:
            pull_requests: List of PRs to analyze

        Returns:
            List of (directory, change_count) tuples sorted by activity
        """
        directory_activity = defaultdict(int)

        for pr in pull_requests:
            for file_stat in pr.file_stats:
                # Get directory path
                if '/' in file_stat.filename:
                    directory = '/'.join(file_stat.filename.split('/')[:-1])
                else:
                    directory = '<root>'

                # Count changes
                changes = file_stat.additions + file_stat.deletions
                directory_activity[directory] += changes

        # Sort by activity
        hotspots = sorted(directory_activity.items(), key=lambda x: x[1], reverse=True)
        return hotspots[:10]  # Top 10 hotspots

    def suggest_pr_themes(self, pr: PullRequest) -> List[str]:
        """
        Suggest possible themes for a PR for debugging/configuration purposes.

        Args:
            pr: PullRequest to analyze

        Returns:
            List of possible theme names
        """
        suggestions = []

        # Directory-based suggestions
        directory_theme = self._get_directory_theme(pr)
        if directory_theme:
            suggestions.append(f"Directory: {directory_theme}")

        # Label-based suggestions
        label_theme = self._get_label_theme(pr)
        if label_theme:
            suggestions.append(f"Label: {label_theme}")

        # Title-based suggestions
        title_theme = self._get_title_theme(pr)
        if title_theme:
            suggestions.append(f"Title: {title_theme}")

        # File pattern analysis
        extensions = set()
        directories = set()
        for file_stat in pr.file_stats:
            filename = file_stat.filename
            if '.' in filename:
                extensions.add(filename.split('.')[-1])
            if '/' in filename:
                directories.add(filename.split('/')[0])

        if extensions:
            suggestions.append(f"Extensions: {', '.join(sorted(extensions))}")
        if directories:
            suggestions.append(f"Directories: {', '.join(sorted(directories))}")

        return suggestions