# GitHub Delivery Visibility - Quick Start Guide

Get up and running with GitHub delivery visibility in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- GitHub Personal Access Token with `repo` read permissions
- Access to the repository you want to monitor (mozilla/bigquery-etl by default)

## Quick Setup

### 1. Install Dependencies

```bash
cd github-delivery-visibility
pip install -r requirements.txt
```

### 2. Configure GitHub Token

1. Create a GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scope: `repo` (read access)
   - Copy the token

2. Set up environment:
   ```bash
   cp .env.example .env
   # Edit .env and add your token:
   # GITHUB_TOKEN=your_token_here
   ```

### 3. Test Connection

```bash
python -m src.github_delivery.cli test-connection
```

You should see: `Connected to mozilla/bigquery-etl successfully`

### 4. Generate Your First Daily Digest

```bash
python -m src.github_delivery.cli daily-digest
```

This will:
- Fetch PRs merged in the last 24 hours
- Categorize them by theme (SQL, Airflow, ETL tooling, etc.)
- Generate a markdown report in `out/YYYY-MM-DD/daily-digest-YYYY-MM-DD.md`
- Print the file location

### 5. Check Your Review Queue

```bash
python -m src.github_delivery.cli review-queue
```

This will show PRs awaiting your review, categorized by urgency and age.

## Configuration

The tool is pre-configured for `mozilla/bigquery-etl` with intelligent categorization:

- **Firefox Data Products**: `sql/moz-fx-data-shared-prod/`
- **Marketing Analytics**: `sql/moz-fx-data-marketing/`
- **Experiments**: `sql/moz-fx-data-experiments/`
- **Airflow Pipelines**: `dags/`
- **ETL Tooling**: `bigquery_etl/`
- **Testing**: `tests/`

To monitor a different repository, edit `config.yaml`:

```yaml
github:
  repository: "your-org/your-repo"
  username: "your-github-username"
```

## Common Commands

```bash
# Daily digest for specific date
python -m src.github_delivery.cli daily-digest --date 2025-01-15

# Review queue for another user
python -m src.github_delivery.cli review-queue --user octocat

# Repository activity analysis
python -m src.github_delivery.cli analyze --days 30

# Debug how a specific PR is categorized
python -m src.github_delivery.cli debug-pr --pr-number 123

# Print output to terminal instead of files
python -m src.github_delivery.cli daily-digest --no-file
```

## Output Structure

The tool creates organized output in the `out/` directory:

```
out/
├── 2025-01-15/
│   ├── daily-digest-2025-01-15.md
│   └── review-queue-username-2025-01-15.md
├── 2025-01-16/
│   └── daily-digest-2025-01-16.md
└── ...
```

Each digest includes:
- **Summary statistics** (PRs merged, contributors, lines changed)
- **Themed sections** (categorized PR groups)
- **Review queue** (PRs needing attention)
- **Complete PR table** (full details with links)

## What's Next?

- Set up a daily cron job to automate digest generation
- Customize categorization rules in `config.yaml`
- Explore the MCP integration for Claude-powered summaries
- Add weekly digest functionality (coming soon)

## Troubleshooting

**"Configuration file not found"**: Make sure you're running from the project directory with `config.yaml`

**"GITHUB_TOKEN environment variable is required"**: Check that your `.env` file exists and contains your token

**"GitHub API access forbidden"**: Verify your token has `repo` read permissions for the target repository

**Empty digest**: Check that PRs were actually merged in the target time window

## Support

- Check existing issues: Look for common problems and solutions
- Debug PR categorization: Use `debug-pr` command to understand how PRs are categorized
- Verbose output: Add `-v` flag to any command for detailed logging