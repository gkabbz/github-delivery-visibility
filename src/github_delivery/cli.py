"""
Command-line interface for GitHub delivery visibility tool.

Main command: ask - Ask natural language questions about PRs
Legacy commands (daily-digest, review-queue, etc.) require old service.py (removed)
"""

import argparse
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# Note: Old DeliveryVisibilityService removed - legacy commands disabled


def create_parser() -> argparse.ArgumentParser:
    """
    Create the main argument parser.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog='github-delivery',
        description='GitHub Delivery Visibility - Get situational awareness of repository activity',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate daily digest for yesterday
  python -m src.github_delivery.cli daily-digest

  # Generate digest for specific date
  python -m src.github_delivery.cli daily-digest --date 2025-01-15

  # Generate biweekly digest for last 2 weeks
  python -m src.github_delivery.cli biweekly-digest

  # Generate review queue for yourself
  python -m src.github_delivery.cli review-queue

  # Generate review queue for another user
  python -m src.github_delivery.cli review-queue --user octocat

  # Analyze repository activity
  python -m src.github_delivery.cli analyze --days 30

  # Test GitHub API connection
  python -m src.github_delivery.cli test-connection

  # Debug PR categorization
  python -m src.github_delivery.cli debug-pr --pr-number 123
        """
    )

    # Global options
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--no-file',
        action='store_true',
        help='Print output to stdout instead of saving to file'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        metavar='COMMAND'
    )

    # Daily digest command
    digest_parser = subparsers.add_parser(
        'daily-digest',
        help='Generate daily delivery digest',
        description='Generate a daily digest of merged PRs with intelligent categorization'
    )
    digest_parser.add_argument(
        '--date',
        type=str,
        help='Target date for digest (YYYY-MM-DD, defaults to yesterday)'
    )

    # Biweekly digest command
    biweekly_parser = subparsers.add_parser(
        'biweekly-digest',
        help='Generate biweekly delivery digest',
        description='Generate a digest of merged PRs from the last 2 weeks'
    )
    biweekly_parser.add_argument(
        '--end-date',
        type=str,
        help='End date for digest (YYYY-MM-DD, defaults to today)'
    )

    # Review queue command
    review_parser = subparsers.add_parser(
        'review-queue',
        help='Generate review queue report',
        description='Generate a report of PRs awaiting your review'
    )
    review_parser.add_argument(
        '--user',
        type=str,
        help='GitHub username (defaults to configured username)'
    )

    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze repository activity',
        description='Analyze repository activity patterns over a time period'
    )
    analyze_parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to analyze (default: 30)'
    )
    analyze_parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    # Test connection command
    subparsers.add_parser(
        'test-connection',
        help='Test GitHub API connection',
        description='Verify that the GitHub API connection is working'
    )

    # Debug PR command
    debug_parser = subparsers.add_parser(
        'debug-pr',
        help='Debug PR categorization',
        description='Show how a specific PR would be categorized'
    )
    debug_parser.add_argument(
        '--pr-number',
        type=int,
        required=True,
        help='PR number to debug'
    )

    # Repository info command
    subparsers.add_parser(
        'repo-info',
        help='Show repository information',
        description='Display basic information about the configured repository'
    )

    # Ask command (NEW - uses GitHubOracle)
    ask_parser = subparsers.add_parser(
        'ask',
        help='Ask a natural language question about PRs',
        description='Ask questions like "What did Alice ship last week?" or "Tell me about PR #123"'
    )
    ask_parser.add_argument(
        'question',
        type=str,
        help='Natural language question to ask'
    )
    ask_parser.add_argument(
        '--repo',
        type=str,
        help='Repository name (e.g., mozilla/bigquery-etl)'
    )
    ask_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed query plan, SQL, and cost information'
    )

    return parser


def parse_date(date_str: str) -> datetime:
    """
    Parse a date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If date string is invalid
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD format.")


def handle_daily_digest(service, args) -> int:
    """
    Handle the daily-digest command.

    Args:
        service: DeliveryVisibilityService instance
        args: Parsed command arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        # Parse target date
        target_date = None
        if args.date:
            target_date = parse_date(args.date)

        # Generate digest
        markdown_content, file_path = service.generate_daily_digest(
            target_date=target_date,
            output_to_file=not args.no_file
        )

        if args.no_file:
            print(markdown_content)
        else:
            print(f"Daily digest generated successfully!")
            if file_path:
                print(f"Output saved to: {file_path}")

        return 0

    except Exception as e:
        print(f"Error generating daily digest: {e}", file=sys.stderr)
        return 1


def handle_biweekly_digest(service, args) -> int:
    """
    Handle the biweekly-digest command.

    Args:
        service: DeliveryVisibilityService instance
        args: Parsed command arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        # Parse end date
        end_date = None
        if args.end_date:
            end_date = parse_date(args.end_date)

        # Generate digest
        markdown_content, file_path = service.generate_biweekly_digest(
            end_date=end_date,
            output_to_file=not args.no_file
        )

        if args.no_file:
            print(markdown_content)
        else:
            print(f"Biweekly digest generated successfully!")
            if file_path:
                print(f"Output saved to: {file_path}")

        return 0

    except Exception as e:
        print(f"Error generating biweekly digest: {e}", file=sys.stderr)
        return 1


def handle_review_queue(service, args) -> int:
    """
    Handle the review-queue command.

    Args:
        service: DeliveryVisibilityService instance
        args: Parsed command arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        # Generate review queue
        markdown_content, file_path = service.generate_review_queue(
            username=args.user,
            output_to_file=not args.no_file
        )

        if args.no_file:
            print(markdown_content)
        else:
            print(f"Review queue generated successfully!")
            if file_path:
                print(f"Output saved to: {file_path}")

        return 0

    except Exception as e:
        print(f"Error generating review queue: {e}", file=sys.stderr)
        return 1


def handle_analyze(service, args) -> int:
    """
    Handle the analyze command.

    Args:
        service: DeliveryVisibilityService instance
        args: Parsed command arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        # Analyze repository activity
        analysis = service.analyze_repository_activity(days=args.days)

        if args.json:
            print(json.dumps(analysis, indent=2, default=str))
        else:
            # Format as human-readable text
            print(f"Repository Activity Analysis")
            print(f"=" * 40)
            print(f"Repository: {service.repository}")
            print(f"Period: {analysis['period']['start_date']} to {analysis['period']['end_date']} ({analysis['period']['days']} days)")
            print()

            summary = analysis['summary']
            print(f"Summary:")
            print(f"  Total merged PRs: {summary['total_merged_prs']}")
            print(f"  Total contributors: {summary['total_contributors']}")
            print(f"  Lines added: {summary['total_additions']:,}")
            print(f"  Lines deleted: {summary['total_deletions']:,}")
            print(f"  Average PR size: {summary['average_pr_size']:.0f} lines")
            print()

            if analysis['themes']:
                print(f"Top Themes:")
                for i, theme in enumerate(analysis['themes'][:5], 1):
                    print(f"  {i}. {theme['name']} ({theme['pr_count']} PRs, {theme['total_changes']} lines)")
                print()

            if analysis['top_contributors']:
                print(f"Top Contributors:")
                for i, contributor in enumerate(analysis['top_contributors'][:5], 1):
                    print(f"  {i}. @{contributor['username']} ({contributor['pr_count']} PRs)")
                print()

            if analysis['hotspots']:
                print(f"Activity Hotspots:")
                for i, hotspot in enumerate(analysis['hotspots'][:5], 1):
                    print(f"  {i}. {hotspot['directory']} ({hotspot['changes']} lines changed)")

        return 0

    except Exception as e:
        print(f"Error analyzing repository: {e}", file=sys.stderr)
        return 1


def handle_test_connection(service, args) -> int:
    """
    Handle the test-connection command.

    Args:
        service: DeliveryVisibilityService instance
        args: Parsed command arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        success, message = service.test_connection()
        print(message)
        return 0 if success else 1

    except Exception as e:
        print(f"Error testing connection: {e}", file=sys.stderr)
        return 1


def handle_debug_pr(service, args) -> int:
    """
    Handle the debug-pr command.

    Args:
        service: DeliveryVisibilityService instance
        args: Parsed command arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        debug_info = service.debug_pr_categorization(args.pr_number)

        print(f"PR Categorization Debug - #{debug_info['pr_number']}")
        print(f"=" * 50)
        print(f"Title: {debug_info['title']}")
        print(f"Author: @{debug_info['author']}")
        print(f"Files changed: {debug_info['files_changed']}")
        print(f"Changes: +{debug_info['additions']} -{debug_info['deletions']}")
        print(f"Labels: {', '.join(debug_info['labels']) if debug_info['labels'] else 'None'}")
        print(f"Directory prefixes: {', '.join(debug_info['directory_prefixes']) if debug_info['directory_prefixes'] else 'None'}")
        print()
        print(f"Categorized as: {debug_info['actual_theme']}")
        print()

        if debug_info['theme_suggestions']:
            print("Theme suggestions:")
            for suggestion in debug_info['theme_suggestions']:
                print(f"  - {suggestion}")

        print()
        print("File details:")
        for file_detail in debug_info['file_details'][:10]:  # Limit to first 10 files
            print(f"  {file_detail['status']}: {file_detail['filename']} (+{file_detail['additions']} -{file_detail['deletions']})")

        if len(debug_info['file_details']) > 10:
            print(f"  ... and {len(debug_info['file_details']) - 10} more files")

        return 0

    except Exception as e:
        print(f"Error debugging PR: {e}", file=sys.stderr)
        return 1


def handle_repo_info(service, args) -> int:
    """
    Handle the repo-info command.

    Args:
        service: DeliveryVisibilityService instance
        args: Parsed command arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        info = service.get_repository_info()

        print(f"Repository Information")
        print(f"=" * 30)
        print(f"Name: {info['full_name']}")
        print(f"Description: {info['description'] or 'No description'}")
        print(f"Primary language: {info['language'] or 'Unknown'}")
        print(f"Stars: {info['stars']:,}")
        print(f"Forks: {info['forks']:,}")
        print(f"Open issues: {info['open_issues']:,}")
        print(f"Default branch: {info['default_branch']}")
        print(f"Last updated: {info['last_updated']}")

        return 0

    except Exception as e:
        print(f"Error getting repository info: {e}", file=sys.stderr)
        return 1


def handle_ask(args) -> int:
    """
    Handle the ask command using GitHubOracle.

    Args:
        args: Parsed command arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        from dotenv import load_dotenv
        from .llm_client import AnthropicLLMClient
        from .bq_data_source import BigQueryDataSource
        from .github_oracle import GitHubOracle

        # Load environment
        load_dotenv()

        # Get config from environment or args
        project_id = os.getenv("BQ_PROJECT_ID", "mozdata-nonprod")
        dataset_id = os.getenv("BQ_DATASET_ID", "analysis")
        table_prefix = os.getenv("TABLE_PREFIX", "gkabbz_gh")
        repo_name = args.repo or os.getenv("GITHUB_REPOSITORY", "mozilla/bigquery-etl")

        # Initialize components
        if args.verbose:
            print("🔮 Initializing GitHubOracle...")
            print(f"  Project: {project_id}")
            print(f"  Dataset: {dataset_id}")
            print(f"  Table prefix: {table_prefix}")
            print(f"  Repository: {repo_name}")
            print()

        data_source = BigQueryDataSource(
            project_id=project_id,
            dataset_id=dataset_id,
            table_prefix=table_prefix
        )
        llm_client = AnthropicLLMClient()
        oracle = GitHubOracle(data_source, llm_client)

        # Ask question
        if args.verbose:
            print(f"❓ Question: {args.question}\n")

        answer = oracle.ask(args.question, repo_name=repo_name)

        # Print answer
        print(answer)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        return 1

    try:
        # Route to command handlers
        if args.command == 'ask':
            # Main GitHubOracle command
            return handle_ask(args)
        elif args.command in ['daily-digest', 'biweekly-digest', 'review-queue',
                              'analyze', 'test-connection', 'debug-pr', 'repo-info']:
            # Legacy commands - service.py was removed
            print(f"⚠️  '{args.command}' command requires old service.py (removed in MVP)", file=sys.stderr)
            print(f"Use 'ask' command instead:", file=sys.stderr)
            print(f"  ghoracle \"What PRs were merged yesterday?\"", file=sys.stderr)
            return 1
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            print(f"Available command: ask", file=sys.stderr)
            return 1

    except FileNotFoundError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("Make sure config.yaml exists and is properly formatted.")
        return 1
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("Check your environment variables and configuration.")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())