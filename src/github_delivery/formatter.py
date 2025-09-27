"""
Markdown formatter for GitHub delivery visibility digests.

Generates well-formatted markdown reports for daily and weekly digests
with consistent styling and clear presentation of GitHub activity data.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .models import PullRequest, DigestTheme, DigestStats, User


class MarkdownFormatter:
    """
    Formats GitHub delivery visibility data into markdown reports.

    Provides methods for generating daily digests, weekly summaries,
    and review queue reports with consistent styling.
    """

    def __init__(self, config: Dict):
        """
        Initialize the formatter with configuration.

        Args:
            config: Configuration dictionary with formatting preferences
        """
        self.config = config
        self.show_contributors = config.get('formatting', {}).get('show_contributors', True)
        self.show_pr_sizes = config.get('formatting', {}).get('show_pr_sizes', True)
        self.include_raw_data = config.get('output', {}).get('include_raw_data', True)
        self.max_prs_per_theme = config.get('formatting', {}).get('max_prs_per_theme', 8)

    def format_daily_digest(self, themes: List[DigestTheme], stats: DigestStats,
                          date: datetime, repository: str) -> str:
        """
        Format a daily digest report.

        Args:
            themes: List of categorized themes with PRs
            stats: Summary statistics for the period
            date: Date of the digest
            repository: Repository name

        Returns:
            Formatted markdown string
        """
        lines = []

        # Header
        lines.append(f"# Daily Delivery Digest - {date.strftime('%B %d, %Y')}")
        lines.append("")
        lines.append(f"**Repository:** {repository}")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary statistics
        lines.append("## 📊 Summary")
        lines.append("")
        if stats.total_merged_prs == 0:
            lines.append("No pull requests were merged in the last 24 hours.")
            lines.append("")
        else:
            lines.append(f"- **{stats.total_merged_prs}** pull requests merged")
            lines.append(f"- **{stats.total_contributors}** contributors active")
            lines.append(f"- **{stats.total_additions:,}** lines added, **{stats.total_deletions:,}** lines deleted")
            lines.append(f"- **{stats.average_pr_size:.0f}** average lines changed per PR")
            lines.append("")

            # Top contributors
            if stats.most_active_contributors:
                lines.append("### Most Active Contributors")
                lines.append("")
                for contributor, pr_count in stats.most_active_contributors:
                    if pr_count == 1:
                        lines.append(f"- **{contributor}** (1 PR)")
                    else:
                        lines.append(f"- **{contributor}** ({pr_count} PRs)")
                lines.append("")

        # Themes
        if themes:
            lines.append("## 🎯 Activity by Theme")
            lines.append("")

            for theme in themes:
                lines.extend(self._format_theme_section(theme))

        # Raw data appendix
        if self.include_raw_data and themes:
            lines.append("---")
            lines.append("")
            lines.append("## 📋 Complete PR List")
            lines.append("")
            all_prs = []
            for theme in themes:
                all_prs.extend(theme.pull_requests)

            # Sort by merge time
            all_prs.sort(key=lambda pr: pr.merged_at or pr.created_at, reverse=True)

            lines.extend(self._format_pr_table(all_prs))

        return "\n".join(lines)

    def format_review_queue(self, review_prs: List[PullRequest], user: str,
                          repository: str) -> str:
        """
        Format a review queue report.

        Args:
            review_prs: List of PRs awaiting review
            user: Username for the review queue
            repository: Repository name

        Returns:
            Formatted markdown string
        """
        lines = []

        # Header
        lines.append(f"# Review Queue for @{user}")
        lines.append("")
        lines.append(f"**Repository:** {repository}")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        if not review_prs:
            lines.append("🎉 **No PRs awaiting your review!**")
            lines.append("")
            lines.append("You're all caught up. Great work!")
            return "\n".join(lines)

        # Summary
        lines.append(f"## 📋 {len(review_prs)} PRs Awaiting Your Review")
        lines.append("")

        # Categorize by urgency and age
        urgent_prs = []
        stale_prs = []
        recent_prs = []

        stale_days = self.config.get('review_queue', {}).get('stale_days', 3)
        urgent_keywords = self.config.get('review_queue', {}).get('urgent_keywords', [])

        for pr in review_prs:
            title_lower = pr.title.lower()
            is_urgent = any(keyword in title_lower for keyword in urgent_keywords)
            is_stale = pr.age_days >= stale_days

            if is_urgent:
                urgent_prs.append(pr)
            elif is_stale:
                stale_prs.append(pr)
            else:
                recent_prs.append(pr)

        # Urgent PRs
        if urgent_prs:
            lines.append("### 🚨 Urgent PRs")
            lines.append("")
            for pr in urgent_prs:
                lines.extend(self._format_review_pr(pr))
            lines.append("")

        # Stale PRs
        if stale_prs:
            lines.append(f"### ⏰ Stale PRs (>{stale_days} days old)")
            lines.append("")
            for pr in sorted(stale_prs, key=lambda p: p.age_days, reverse=True):
                lines.extend(self._format_review_pr(pr))
            lines.append("")

        # Recent PRs
        if recent_prs:
            lines.append("### 📝 Recent Review Requests")
            lines.append("")
            for pr in sorted(recent_prs, key=lambda p: p.created_at, reverse=True):
                lines.extend(self._format_review_pr(pr))

        return "\n".join(lines)

    def _format_theme_section(self, theme: DigestTheme) -> List[str]:
        """
        Format a single theme section.

        Args:
            theme: DigestTheme to format

        Returns:
            List of markdown lines
        """
        lines = []

        # Theme header
        lines.append(f"### {theme.name}")
        lines.append("")

        if theme.description:
            lines.append(f"*{theme.description}*")
            lines.append("")

        # List PRs
        prs_to_show = theme.pull_requests[:self.max_prs_per_theme]
        remaining_count = len(theme.pull_requests) - len(prs_to_show)

        for pr in prs_to_show:
            lines.append(f"- **[#{pr.number}]({pr.html_url})** {pr.title}")

            details = []
            if self.show_contributors:
                details.append(f"by @{pr.author.login}")

            if self.show_pr_sizes and (pr.additions > 0 or pr.deletions > 0):
                details.append(f"{pr.size_category} ({pr.additions + pr.deletions} lines)")

            if pr.labels:
                label_names = [label.name for label in pr.labels]
                details.append(f"labels: {', '.join(label_names)}")

            if details:
                lines.append(f"  *{' • '.join(details)}*")

        if remaining_count > 0:
            lines.append("")
            lines.append(f"*... and {remaining_count} more PRs in this theme*")

        lines.append("")
        return lines

    def _format_review_pr(self, pr: PullRequest) -> List[str]:
        """
        Format a single PR for the review queue.

        Args:
            pr: PullRequest to format

        Returns:
            List of markdown lines
        """
        lines = []

        # PR title with link
        lines.append(f"- **[#{pr.number}]({pr.html_url})** {pr.title}")

        # Details
        details = []
        details.append(f"by @{pr.author.login}")
        details.append(f"{pr.age_days} days old")

        if pr.additions > 0 or pr.deletions > 0:
            details.append(f"{pr.size_category} ({pr.additions + pr.deletions} lines)")

        if pr.draft:
            details.append("DRAFT")

        lines.append(f"  *{' • '.join(details)}*")

        # Show latest review status if available
        if pr.latest_review_state:
            status_text = {
                'APPROVED': '✅ Previously approved',
                'CHANGES_REQUESTED': '❌ Changes requested',
                'COMMENTED': '💬 Comments added'
            }.get(pr.latest_review_state.value, f'📝 {pr.latest_review_state.value}')
            lines.append(f"  *{status_text}*")

        lines.append("")
        return lines

    def _format_pr_table(self, prs: List[PullRequest]) -> List[str]:
        """
        Format PRs as a markdown table.

        Args:
            prs: List of PullRequest objects

        Returns:
            List of markdown lines
        """
        if not prs:
            return ["*No pull requests to display.*", ""]

        lines = []
        lines.append("| PR | Title | Author | Size | Labels |")
        lines.append("|---|---|---|---|---|")

        for pr in prs:
            # Format labels
            label_text = ""
            if pr.labels:
                label_names = [f"`{label.name}`" for label in pr.labels[:3]]
                label_text = " ".join(label_names)
                if len(pr.labels) > 3:
                    label_text += f" +{len(pr.labels) - 3}"

            # Size info
            size_info = f"{pr.size_category}"
            if pr.additions > 0 or pr.deletions > 0:
                size_info += f" ({pr.additions + pr.deletions})"

            lines.append(f"| [#{pr.number}]({pr.html_url}) | {pr.title[:50]}{'...' if len(pr.title) > 50 else ''} | @{pr.author.login} | {size_info} | {label_text} |")

        lines.append("")
        return lines

    def save_to_file(self, content: str, output_dir: str, filename: str) -> str:
        """
        Save markdown content to a file.

        Args:
            content: Markdown content to save
            output_dir: Output directory path
            filename: Output filename

        Returns:
            Full path to the saved file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Write content to file
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path

    def get_daily_output_path(self, base_dir: str, date: datetime) -> tuple[str, str]:
        """
        Get the output directory and filename for a daily digest.

        Args:
            base_dir: Base output directory
            date: Date for the digest

        Returns:
            Tuple of (output_dir, filename)
        """
        date_str = date.strftime(self.config.get('output', {}).get('date_format', '%Y-%m-%d'))
        output_dir = os.path.join(base_dir, date_str)
        filename = f"daily-digest-{date_str}.md"
        return output_dir, filename

    def get_review_queue_output_path(self, base_dir: str, user: str) -> tuple[str, str]:
        """
        Get the output directory and filename for a review queue.

        Args:
            base_dir: Base output directory
            user: Username for the review queue

        Returns:
            Tuple of (output_dir, filename)
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_dir = os.path.join(base_dir, date_str)
        filename = f"review-queue-{user}-{date_str}.md"
        return output_dir, filename