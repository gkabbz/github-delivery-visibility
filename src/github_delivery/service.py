"""
Core service for GitHub delivery visibility.

Orchestrates data collection, categorization, and report generation
for daily digests and review queues.
"""

import os
import yaml
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from .collector import GitHubCollector, GitHubAPIError
from .themer import Themer
from .formatter import MarkdownFormatter
from .models import PullRequest, DigestTheme, DigestStats


class DeliveryVisibilityService:
    """
    Main service for GitHub delivery visibility.

    Coordinates all components to generate daily digests, review queues,
    and other visibility reports.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the service with configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        # Load environment variables
        load_dotenv()

        # Load configuration
        self.config = self._load_config(config_path)
        self.repository = self.config['github']['repository']
        self.username = self.config['github']['username']

        # Initialize components
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")

        self.collector = GitHubCollector(
            token=github_token,
            repository=self.repository,
            api_base_url=self.config['github']['api_base_url']
        )
        self.themer = Themer(self.config)
        self.formatter = MarkdownFormatter(self.config)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Override with environment variables if present
        if os.getenv('GITHUB_REPOSITORY'):
            config['github']['repository'] = os.getenv('GITHUB_REPOSITORY')
        if os.getenv('GITHUB_USERNAME'):
            config['github']['username'] = os.getenv('GITHUB_USERNAME')

        return config

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to GitHub API.

        Returns:
            Tuple of (success, message)
        """
        return self.collector.test_connection()

    def generate_daily_digest(self, target_date: Optional[datetime] = None,
                            output_to_file: bool = True) -> Tuple[str, Optional[str]]:
        """
        Generate a daily digest report.

        Args:
            target_date: Date for the digest (defaults to yesterday)
            output_to_file: Whether to save to file

        Returns:
            Tuple of (markdown_content, file_path)
        """
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)

        print(f"Generating daily digest for {target_date.strftime('%Y-%m-%d')}...")

        # Define time window (last 24 hours from target date)
        end_time = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_time = end_time - timedelta(hours=24)

        try:
            # Collect merged PRs
            merged_prs = self.collector.get_merged_prs(start_time, end_time)

            # Categorize PRs into themes
            themes = self.themer.categorize_pull_requests(merged_prs)

            # Calculate statistics
            stats = DigestStats.from_pull_requests(merged_prs)

            # Generate markdown report
            markdown_content = self.formatter.format_daily_digest(
                themes=themes,
                stats=stats,
                date=target_date,
                repository=self.repository
            )

            # Save to file if requested
            file_path = None
            if output_to_file:
                base_dir = self.config['output']['base_dir']
                output_dir, filename = self.formatter.get_daily_output_path(base_dir, target_date)
                file_path = self.formatter.save_to_file(markdown_content, output_dir, filename)
                print(f"Daily digest saved to: {file_path}")

            return markdown_content, file_path

        except GitHubAPIError as e:
            raise RuntimeError(f"Failed to generate daily digest: {e}")

    def generate_biweekly_digest(self, end_date: Optional[datetime] = None,
                                output_to_file: bool = True) -> Tuple[str, Optional[str]]:
        """
        Generate a biweekly digest report.

        Args:
            end_date: End date for the digest (defaults to today)
            output_to_file: Whether to save to file

        Returns:
            Tuple of (markdown_content, file_path)
        """
        if end_date is None:
            end_date = datetime.now()

        print(f"Generating biweekly digest ending {end_date.strftime('%Y-%m-%d')}...")

        # Define time window (14 days ending at end_date)
        end_time = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_time = end_time - timedelta(days=14)

        try:
            # Collect merged PRs
            merged_prs = self.collector.get_merged_prs(start_time, end_time)

            # Categorize PRs into themes
            themes = self.themer.categorize_pull_requests(merged_prs)

            # Calculate statistics
            stats = DigestStats.from_pull_requests(merged_prs)

            # Generate markdown report
            markdown_content = self.formatter.format_biweekly_digest(
                themes=themes,
                stats=stats,
                start_date=start_time,
                end_date=end_date,
                repository=self.repository
            )

            # Save to file if requested
            file_path = None
            if output_to_file:
                base_dir = self.config['output']['base_dir']
                output_dir, filename = self.formatter.get_biweekly_output_path(base_dir, end_date)
                file_path = self.formatter.save_to_file(markdown_content, output_dir, filename)
                print(f"Biweekly digest saved to: {file_path}")

            return markdown_content, file_path

        except GitHubAPIError as e:
            raise RuntimeError(f"Failed to generate biweekly digest: {e}")

    def generate_review_queue(self, username: Optional[str] = None,
                            output_to_file: bool = True) -> Tuple[str, Optional[str]]:
        """
        Generate a review queue report.

        Args:
            username: GitHub username (defaults to configured username)
            output_to_file: Whether to save to file

        Returns:
            Tuple of (markdown_content, file_path)
        """
        if username is None:
            username = self.username

        print(f"Generating review queue for @{username}...")

        try:
            # Get PRs awaiting review from the user
            review_prs = self.collector.get_review_requests_for_user(username)

            # Generate markdown report
            markdown_content = self.formatter.format_review_queue(
                review_prs=review_prs,
                user=username,
                repository=self.repository
            )

            # Save to file if requested
            file_path = None
            if output_to_file:
                base_dir = self.config['output']['base_dir']
                output_dir, filename = self.formatter.get_review_queue_output_path(base_dir, username)
                file_path = self.formatter.save_to_file(markdown_content, output_dir, filename)
                print(f"Review queue saved to: {file_path}")

            return markdown_content, file_path

        except GitHubAPIError as e:
            raise RuntimeError(f"Failed to generate review queue: {e}")

    def analyze_repository_activity(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze repository activity over a period.

        Args:
            days: Number of days to analyze

        Returns:
            Analysis results dictionary
        """
        print(f"Analyzing repository activity for last {days} days...")

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        try:
            # Get merged PRs for the period
            merged_prs = self.collector.get_merged_prs(start_time, end_time)

            # Get themes
            themes = self.themer.categorize_pull_requests(merged_prs)

            # Get hotspots
            hotspots = self.themer.get_hotspots(merged_prs)

            # Calculate statistics
            stats = DigestStats.from_pull_requests(merged_prs)

            return {
                'period': {
                    'start_date': start_time.strftime('%Y-%m-%d'),
                    'end_date': end_time.strftime('%Y-%m-%d'),
                    'days': days
                },
                'summary': {
                    'total_merged_prs': stats.total_merged_prs,
                    'total_contributors': stats.total_contributors,
                    'total_additions': stats.total_additions,
                    'total_deletions': stats.total_deletions,
                    'average_pr_size': stats.average_pr_size
                },
                'themes': [
                    {
                        'name': theme.name,
                        'pr_count': theme.pr_count,
                        'contributors': theme.contributors,
                        'total_changes': theme.total_changes,
                        'description': theme.description
                    }
                    for theme in themes
                ],
                'hotspots': [
                    {'directory': directory, 'changes': changes}
                    for directory, changes in hotspots
                ],
                'top_contributors': [
                    {'username': username, 'pr_count': pr_count}
                    for username, pr_count in stats.most_active_contributors
                ]
            }

        except GitHubAPIError as e:
            raise RuntimeError(f"Failed to analyze repository activity: {e}")

    def debug_pr_categorization(self, pr_number: int) -> Dict[str, Any]:
        """
        Debug how a specific PR would be categorized.

        Args:
            pr_number: PR number to analyze

        Returns:
            Categorization debug information
        """
        print(f"Debugging categorization for PR #{pr_number}...")

        try:
            # Fetch the specific PR
            # Note: This is a simplified version - in a real implementation,
            # we'd need to add a method to fetch a single PR
            open_prs = self.collector.get_open_prs(limit=100)
            pr = None
            for p in open_prs:
                if p.number == pr_number:
                    pr = p
                    break

            if not pr:
                # Try merged PRs from recent history
                recent_prs = self.collector.get_merged_prs(
                    datetime.now() - timedelta(days=30)
                )
                for p in recent_prs:
                    if p.number == pr_number:
                        pr = p
                        break

            if not pr:
                raise ValueError(f"PR #{pr_number} not found in recent activity")

            # Get categorization suggestions
            suggestions = self.themer.suggest_pr_themes(pr)

            # Get actual theme
            actual_theme = self.themer._determine_theme(pr)

            return {
                'pr_number': pr_number,
                'title': pr.title,
                'author': pr.author.login,
                'files_changed': len(pr.file_stats),
                'additions': pr.additions,
                'deletions': pr.deletions,
                'labels': [label.name for label in pr.labels],
                'directory_prefixes': pr.directory_prefixes,
                'actual_theme': actual_theme,
                'theme_suggestions': suggestions,
                'file_details': [
                    {
                        'filename': fs.filename,
                        'status': fs.status,
                        'additions': fs.additions,
                        'deletions': fs.deletions,
                        'directory_prefix': fs.directory_prefix
                    }
                    for fs in pr.file_stats
                ]
            }

        except (GitHubAPIError, ValueError) as e:
            raise RuntimeError(f"Failed to debug PR categorization: {e}")

    def get_repository_info(self) -> Dict[str, Any]:
        """
        Get basic information about the configured repository.

        Returns:
            Repository information dictionary
        """
        try:
            repo_info = self.collector.get_repository_info()
            return {
                'name': repo_info['name'],
                'full_name': repo_info['full_name'],
                'description': repo_info.get('description'),
                'language': repo_info.get('language'),
                'stars': repo_info.get('stargazers_count'),
                'forks': repo_info.get('forks_count'),
                'open_issues': repo_info.get('open_issues_count'),
                'default_branch': repo_info.get('default_branch'),
                'last_updated': repo_info.get('updated_at')
            }
        except GitHubAPIError as e:
            raise RuntimeError(f"Failed to get repository info: {e}")