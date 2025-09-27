"""
MCP server integration for GitHub delivery visibility.

Provides MCP tools that can be used with Claude for enhanced summarization
and narrative generation capabilities.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .service import DeliveryVisibilityService


class GitHubDeliveryMCPTools:
    """
    MCP tools for GitHub delivery visibility.

    Provides tools that can be called by Claude through the MCP protocol
    to generate enhanced summaries and narratives.
    """

    def __init__(self, service: DeliveryVisibilityService):
        """
        Initialize MCP tools with a service instance.

        Args:
            service: DeliveryVisibilityService instance
        """
        self.service = service

    def get_daily_digest_data(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get structured data for daily digest generation.

        This tool provides Claude with structured PR data that can be used
        to generate enhanced summaries and narratives.

        Args:
            date: Target date in YYYY-MM-DD format (defaults to yesterday)

        Returns:
            Structured digest data
        """
        try:
            # Parse date
            target_date = None
            if date:
                target_date = datetime.strptime(date, '%Y-%m-%d')

            if target_date is None:
                target_date = datetime.now() - timedelta(days=1)

            # Define time window
            end_time = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            start_time = end_time - timedelta(hours=24)

            # Get merged PRs
            merged_prs = self.service.collector.get_merged_prs(start_time, end_time)

            # Categorize PRs
            themes = self.service.themer.categorize_pull_requests(merged_prs)

            # Prepare structured data for Claude
            structured_data = {
                'metadata': {
                    'repository': self.service.repository,
                    'date': target_date.strftime('%Y-%m-%d'),
                    'total_merged_prs': len(merged_prs),
                    'total_themes': len(themes)
                },
                'themes': []
            }

            for theme in themes:
                theme_data = {
                    'name': theme.name,
                    'pr_count': theme.pr_count,
                    'contributors': theme.contributors,
                    'total_changes': theme.total_changes,
                    'pull_requests': []
                }

                # Include PR metadata (no code content)
                for pr in theme.pull_requests:
                    pr_data = {
                        'number': pr.number,
                        'title': pr.title,
                        'author': pr.author.login,
                        'size_category': pr.size_category,
                        'additions': pr.additions,
                        'deletions': pr.deletions,
                        'labels': [label.name for label in pr.labels],
                        'directory_prefixes': pr.directory_prefixes,
                        'html_url': pr.html_url,
                        'merged_at': pr.merged_at.isoformat() if pr.merged_at else None
                    }
                    theme_data['pull_requests'].append(pr_data)

                structured_data['themes'].append(theme_data)

            return structured_data

        except Exception as e:
            return {'error': f'Failed to get daily digest data: {str(e)}'}

    def get_review_queue_data(self, username: Optional[str] = None) -> Dict[str, Any]:
        """
        Get structured data for review queue generation.

        Args:
            username: GitHub username (defaults to configured username)

        Returns:
            Structured review queue data
        """
        try:
            if username is None:
                username = self.service.username

            # Get review requests
            review_prs = self.service.collector.get_review_requests_for_user(username)

            # Categorize by urgency and age
            urgent_prs = []
            stale_prs = []
            recent_prs = []

            stale_days = self.service.config.get('review_queue', {}).get('stale_days', 3)
            urgent_keywords = self.service.config.get('review_queue', {}).get('urgent_keywords', [])

            for pr in review_prs:
                title_lower = pr.title.lower()
                is_urgent = any(keyword in title_lower for keyword in urgent_keywords)
                is_stale = pr.age_days >= stale_days

                pr_data = {
                    'number': pr.number,
                    'title': pr.title,
                    'author': pr.author.login,
                    'age_days': pr.age_days,
                    'size_category': pr.size_category,
                    'additions': pr.additions,
                    'deletions': pr.deletions,
                    'labels': [label.name for label in pr.labels],
                    'draft': pr.draft,
                    'html_url': pr.html_url,
                    'latest_review_state': pr.latest_review_state.value if pr.latest_review_state else None
                }

                if is_urgent:
                    urgent_prs.append(pr_data)
                elif is_stale:
                    stale_prs.append(pr_data)
                else:
                    recent_prs.append(pr_data)

            return {
                'metadata': {
                    'repository': self.service.repository,
                    'username': username,
                    'total_review_requests': len(review_prs),
                    'urgent_count': len(urgent_prs),
                    'stale_count': len(stale_prs),
                    'recent_count': len(recent_prs)
                },
                'categories': {
                    'urgent': urgent_prs,
                    'stale': stale_prs,
                    'recent': recent_prs
                }
            }

        except Exception as e:
            return {'error': f'Failed to get review queue data: {str(e)}'}

    def analyze_repository_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze repository trends over a time period.

        Args:
            days: Number of days to analyze

        Returns:
            Trend analysis data
        """
        try:
            analysis = self.service.analyze_repository_activity(days=days)

            # Enhance with trend indicators
            enhanced_analysis = analysis.copy()

            # Add trend context
            enhanced_analysis['insights'] = []

            # Activity level insights
            avg_prs_per_day = analysis['summary']['total_merged_prs'] / days
            if avg_prs_per_day > 5:
                enhanced_analysis['insights'].append({
                    'type': 'high_activity',
                    'message': f'High development velocity with {avg_prs_per_day:.1f} PRs merged per day'
                })
            elif avg_prs_per_day < 1:
                enhanced_analysis['insights'].append({
                    'type': 'low_activity',
                    'message': f'Lower development velocity with {avg_prs_per_day:.1f} PRs merged per day'
                })

            # Team size insights
            if analysis['summary']['total_contributors'] > 10:
                enhanced_analysis['insights'].append({
                    'type': 'large_team',
                    'message': f'Large active team with {analysis["summary"]["total_contributors"]} contributors'
                })
            elif analysis['summary']['total_contributors'] < 3:
                enhanced_analysis['insights'].append({
                    'type': 'small_team',
                    'message': f'Small focused team with {analysis["summary"]["total_contributors"]} contributors'
                })

            # Theme concentration insights
            if len(analysis['themes']) > 0:
                top_theme = analysis['themes'][0]
                theme_concentration = top_theme['pr_count'] / analysis['summary']['total_merged_prs']
                if theme_concentration > 0.5:
                    enhanced_analysis['insights'].append({
                        'type': 'focused_work',
                        'message': f'Highly focused on {top_theme["name"]} ({theme_concentration:.1%} of activity)'
                    })

            return enhanced_analysis

        except Exception as e:
            return {'error': f'Failed to analyze repository trends: {str(e)}'}

    def generate_narrative_prompt(self, data: Dict[str, Any], narrative_type: str = 'daily') -> str:
        """
        Generate a prompt for Claude to create narratives.

        Args:
            data: Structured data (from other tools)
            narrative_type: Type of narrative ('daily', 'weekly', 'review_queue')

        Returns:
            Formatted prompt for Claude
        """
        if narrative_type == 'daily':
            return self._generate_daily_narrative_prompt(data)
        elif narrative_type == 'review_queue':
            return self._generate_review_queue_narrative_prompt(data)
        else:
            return f"Generate a {narrative_type} narrative based on this GitHub activity data:\n\n{json.dumps(data, indent=2)}"

    def _generate_daily_narrative_prompt(self, data: Dict[str, Any]) -> str:
        """Generate prompt for daily narrative."""
        prompt = f"""Please analyze this GitHub repository activity data and create a concise daily summary.

Repository: {data.get('metadata', {}).get('repository', 'Unknown')}
Date: {data.get('metadata', {}).get('date', 'Unknown')}
Total PRs merged: {data.get('metadata', {}).get('total_merged_prs', 0)}

Activity data:
{json.dumps(data.get('themes', []), indent=2)}

Please provide:
1. A brief 2-3 sentence summary of the day's development activity
2. The top 2-3 themes/areas of focus
3. Any notable patterns or insights
4. Key contributors and their contributions

Keep the tone professional but engaging, suitable for an engineering manager's daily briefing. Focus on themes and patterns rather than individual PR details."""

        return prompt

    def _generate_review_queue_narrative_prompt(self, data: Dict[str, Any]) -> str:
        """Generate prompt for review queue narrative."""
        prompt = f"""Please analyze this review queue data and create a prioritized action summary.

Repository: {data.get('metadata', {}).get('repository', 'Unknown')}
User: @{data.get('metadata', {}).get('username', 'Unknown')}
Total review requests: {data.get('metadata', {}).get('total_review_requests', 0)}

Review queue breakdown:
- Urgent PRs: {data.get('metadata', {}).get('urgent_count', 0)}
- Stale PRs: {data.get('metadata', {}).get('stale_count', 0)}
- Recent PRs: {data.get('metadata', {}).get('recent_count', 0)}

Detailed data:
{json.dumps(data.get('categories', {}), indent=2)}

Please provide:
1. A priority assessment of what needs immediate attention
2. Recommendations for review order
3. Any patterns or concerns in the review queue
4. Estimated time investment needed

Keep the tone actionable and focused on helping prioritize review work effectively."""

        return prompt


# Example MCP server configuration (would need proper MCP protocol implementation)
def get_mcp_tools_config(service: DeliveryVisibilityService) -> Dict[str, Any]:
    """
    Get MCP tools configuration.

    This would be used by an MCP server implementation to expose
    these tools to Claude.

    Args:
        service: DeliveryVisibilityService instance

    Returns:
        MCP tools configuration
    """
    tools = GitHubDeliveryMCPTools(service)

    return {
        "tools": [
            {
                "name": "get_daily_digest_data",
                "description": "Get structured GitHub activity data for daily digest generation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Target date in YYYY-MM-DD format (optional, defaults to yesterday)"
                        }
                    }
                }
            },
            {
                "name": "get_review_queue_data",
                "description": "Get structured review queue data for a GitHub user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "GitHub username (optional, defaults to configured username)"
                        }
                    }
                }
            },
            {
                "name": "analyze_repository_trends",
                "description": "Analyze repository activity trends over a time period",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {
                            "type": "integer",
                            "description": "Number of days to analyze (default: 30)"
                        }
                    }
                }
            },
            {
                "name": "generate_narrative_prompt",
                "description": "Generate a prompt for creating narrative summaries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "description": "Structured data from other tools"
                        },
                        "narrative_type": {
                            "type": "string",
                            "description": "Type of narrative to generate (daily, weekly, review_queue)"
                        }
                    }
                }
            }
        ]
    }