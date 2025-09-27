"""
GitHub API collector for fetching repository data.

Handles interaction with the GitHub API to retrieve pull requests, reviews,
and related metadata with proper error handling and rate limiting.
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from .models import PullRequest, Review, FileStat, PRState
from .cache import PRCache


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    pass


class RateLimitError(GitHubAPIError):
    """Exception raised when rate limit is exceeded."""
    pass


class GitHubCollector:
    """
    Collects data from GitHub API with rate limiting and error handling.

    Designed to work with the GitHub REST API using only Python standard library
    to minimize dependencies.
    """

    def __init__(self, token: str, repository: str, api_base_url: str = "https://api.github.com",
                 cache_dir: str = "cache"):
        """
        Initialize the GitHub collector.

        Args:
            token: GitHub Personal Access Token
            repository: Repository in format "owner/repo"
            api_base_url: Base URL for GitHub API
            cache_dir: Directory for persistent PR cache
        """
        self.token = token
        self.repository = repository
        self.api_base_url = api_base_url.rstrip('/')
        self.session_headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Delivery-Visibility/0.1.0'
        }
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = datetime.now()
        self._is_public_repo = None  # Cache repository visibility
        self.cache = PRCache(cache_dir)  # PR caching system

    def _make_request(self, url: str, params: Optional[Dict[str, str]] = None,
                      max_retries: int = 3, timeout: int = None) -> Dict[str, Any]:
        """
        Make a request to the GitHub API with error handling, rate limiting, and retries.

        Args:
            url: API endpoint URL
            params: Query parameters
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds (auto-calculated if None)

        Returns:
            JSON response data

        Raises:
            RateLimitError: When rate limit is exceeded
            GitHubAPIError: For other API errors
        """
        # Auto-calculate timeout based on request type and repository visibility
        if timeout is None:
            is_diff_request = '/files' in url or '/pulls' in url
            try:
                if is_diff_request and self.is_public_repository():
                    timeout = 90  # Longer timeout for diff-heavy requests on public repos
                else:
                    timeout = 30  # Standard timeout
            except Exception:
                timeout = 30  # Fallback timeout if repo check fails

        # Check rate limit
        if self.rate_limit_remaining <= 1 and datetime.now() < self.rate_limit_reset:
            sleep_time = (self.rate_limit_reset - datetime.now()).total_seconds()
            print(f"Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
            time.sleep(sleep_time + 1)

        # Build URL with parameters
        if params:
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"
        else:
            full_url = url

        # Create request
        req = urllib.request.Request(full_url, headers=self.session_headers)

        # Retry logic
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                # Make request with dynamic timeout
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    # Update rate limit info
                    self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
                    reset_timestamp = int(response.headers.get('X-RateLimit-Reset', time.time()))
                    self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)

                    # Parse response
                    data = json.loads(response.read().decode('utf-8'))
                    return data

            except urllib.error.HTTPError as e:
                if e.code == 403:
                    # Check if it's a rate limit error
                    try:
                        error_data = json.loads(e.read().decode('utf-8'))
                        if 'rate limit' in error_data.get('message', '').lower():
                            raise RateLimitError("GitHub API rate limit exceeded")
                    except json.JSONDecodeError:
                        pass
                    raise GitHubAPIError(f"GitHub API access forbidden: {e}")
                elif e.code == 404:
                    raise GitHubAPIError(f"GitHub API endpoint not found: {url}")
                else:
                    last_exception = e

            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_exception = e

            except json.JSONDecodeError as e:
                last_exception = e

            # If we get here, the request failed - retry with exponential backoff
            if attempt < max_retries:
                wait_time = (2 ** attempt) + 1  # 2, 3, 5 seconds
                print(f"Request failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Final attempt failed
                if isinstance(last_exception, urllib.error.HTTPError):
                    raise GitHubAPIError(f"GitHub API error {last_exception.code}: {last_exception}")
                elif isinstance(last_exception, (urllib.error.URLError, TimeoutError, OSError)):
                    raise GitHubAPIError(f"Network/timeout error: {last_exception}")
                else:
                    raise GitHubAPIError(f"Invalid JSON response: {last_exception}")

        # Should never reach here
        raise GitHubAPIError("Unexpected error in request retry logic")

    def _get_all_pages(self, url: str, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch all pages of a paginated API response.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            List of all items across all pages
        """
        all_items = []
        current_params = params.copy() if params else {}
        current_params.setdefault('per_page', '100')  # Max items per page

        page = 1
        while True:
            current_params['page'] = str(page)
            data = self._make_request(url, current_params)

            if not isinstance(data, list):
                # Single item response, not paginated
                return [data] if data else []

            all_items.extend(data)

            # Check if we got fewer items than requested (last page)
            if len(data) < int(current_params['per_page']):
                break

            page += 1

            # Safety check to avoid infinite loops
            if page > 100:  # Max 10,000 items
                print(f"Warning: Stopped pagination at page {page} to avoid infinite loop")
                break

        return all_items

    def get_merged_prs(self, since: datetime, until: Optional[datetime] = None) -> List[PullRequest]:
        """
        Get all PRs merged within a time window.

        Args:
            since: Start datetime for the window
            until: End datetime for the window (defaults to now)

        Returns:
            List of merged PullRequest objects
        """
        if until is None:
            until = datetime.now()

        # GitHub API expects ISO format
        since_str = since.strftime('%Y-%m-%dT%H:%M:%SZ')
        until_str = until.strftime('%Y-%m-%dT%H:%M:%SZ')

        url = f"{self.api_base_url}/repos/{self.repository}/pulls"
        params = {
            'state': 'closed',
            'sort': 'updated',
            'direction': 'desc',
            'since': since_str
        }

        print(f"Fetching merged PRs from {since_str} to {until_str}...")
        pr_data = self._get_all_pages(url, params)

        merged_prs = []
        for pr_item in pr_data:
            # Skip if not merged or outside time window
            if not pr_item.get('merged_at'):
                continue

            merged_at = datetime.fromisoformat(pr_item['merged_at'].replace('Z', '+00:00'))
            if merged_at < since or merged_at > until:
                continue

            pr_number = pr_item['number']

            # Check cache first
            cached_pr = self.cache.get_pr(self.repository, pr_number)
            if cached_pr:
                print(f"Using cached data for PR #{pr_number}")
                merged_prs.append(cached_pr)
                continue

            # Create PR object from API data
            pr = PullRequest.from_github_data(pr_item)

            # Fetch additional data (files, reviews) if needed
            pr = self._enrich_pull_request(pr)

            # Cache the enriched PR
            self.cache.store_pr(self.repository, pr)

            merged_prs.append(pr)

        print(f"Found {len(merged_prs)} merged PRs")
        return merged_prs

    def get_open_prs(self, limit: int = 100) -> List[PullRequest]:
        """
        Get all open PRs.

        Args:
            limit: Maximum number of PRs to fetch

        Returns:
            List of open PullRequest objects
        """
        url = f"{self.api_base_url}/repos/{self.repository}/pulls"
        params = {
            'state': 'open',
            'sort': 'updated',
            'direction': 'desc',
            'per_page': str(min(limit, 100))
        }

        print("Fetching open PRs...")
        pr_data = self._get_all_pages(url, params)

        # Limit results
        pr_data = pr_data[:limit]

        open_prs = []
        for pr_item in pr_data:
            pr_number = pr_item['number']

            # Check cache first (but still enrich open PRs since they change frequently)
            cached_pr = self.cache.get_pr(self.repository, pr_number)
            if cached_pr and cached_pr.state.value == 'open':
                # For open PRs, we still want fresh review data, so re-enrich
                pr = self._enrich_pull_request(cached_pr)
                self.cache.store_pr(self.repository, pr)  # Update cache
            else:
                # Create new PR object
                pr = PullRequest.from_github_data(pr_item)
                pr = self._enrich_pull_request(pr)
                self.cache.store_pr(self.repository, pr)

            open_prs.append(pr)

        print(f"Found {len(open_prs)} open PRs")
        return open_prs

    def get_review_requests_for_user(self, username: str, limit: int = 50) -> List[PullRequest]:
        """
        Get PRs where a specific user is requested as reviewer.

        Args:
            username: GitHub username to check for review requests
            limit: Maximum number of PRs to check

        Returns:
            List of PullRequest objects awaiting review from the user
        """
        # Get open PRs and filter for review requests
        open_prs = self.get_open_prs(limit)

        review_requests = []
        for pr in open_prs:
            if pr.is_waiting_for_user(username):
                review_requests.append(pr)

        print(f"Found {len(review_requests)} PRs awaiting review from {username}")
        return review_requests

    def _enrich_pull_request(self, pr: PullRequest) -> PullRequest:
        """
        Enrich a pull request with additional data (files, reviews).

        Args:
            pr: Base PullRequest object

        Returns:
            Enriched PullRequest object
        """
        # Fetch file changes
        try:
            files_url = f"{self.api_base_url}/repos/{self.repository}/pulls/{pr.number}/files"
            # For public repos, we can safely include patch content for LLM analysis
            if self.is_public_repository():
                print(f"Fetching diff content for public repo PR #{pr.number}")
            files_data = self._get_all_pages(files_url)
            pr.file_stats = [FileStat.from_github_data(file_data) for file_data in files_data]
        except GitHubAPIError as e:
            print(f"Warning: Could not fetch files for PR #{pr.number}: {e}")

        # Fetch reviews
        try:
            reviews_url = f"{self.api_base_url}/repos/{self.repository}/pulls/{pr.number}/reviews"
            reviews_data = self._get_all_pages(reviews_url)
            pr.reviews = [Review.from_github_data(review_data) for review_data in reviews_data]
        except GitHubAPIError as e:
            print(f"Warning: Could not fetch reviews for PR #{pr.number}: {e}")

        return pr

    def get_repository_info(self) -> Dict[str, Any]:
        """
        Get basic repository information.

        Returns:
            Repository metadata
        """
        url = f"{self.api_base_url}/repos/{self.repository}"
        return self._make_request(url)

    def is_public_repository(self) -> bool:
        """
        Check if the repository is public.

        Returns:
            True if repository is public, False if private
        """
        if self._is_public_repo is None:
            repo_info = self.get_repository_info()
            self._is_public_repo = not repo_info.get('private', True)
        return self._is_public_repo

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the connection to GitHub API.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            repo_info = self.get_repository_info()
            return True, f"Connected to {repo_info['full_name']} successfully"
        except GitHubAPIError as e:
            return False, f"Connection failed: {e}"