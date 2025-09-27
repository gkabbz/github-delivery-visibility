# GitHub Delivery Visibility

A focused tool for getting daily and weekly visibility into GitHub repository activity, specifically designed for engineering managers who want quick situational awareness without constant context switching.

## Overview

This tool generates automated digests that answer key questions:
- What shipped in the last 24 hours?
- What PRs need my review?
- Where is development activity concentrated?
- What themes are emerging in our work?

Initially configured for monitoring `mozilla/bigquery-etl` with smart categorization for data engineering workflows.

## Quick Start

1. **Setup**:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env and add your GitHub token
   ```

2. **Generate daily digest**:
   ```bash
   python -m src.github_delivery.cli daily-digest
   ```

3. **Check review queue**:
   ```bash
   python -m src.github_delivery.cli review-queue
   ```

## Configuration

Edit `config.yaml` to customize:
- Repository to monitor
- Categorization rules for different file paths
- Output formatting preferences
- Review queue settings

## Features

### Daily Digest
- Merged PRs from last 24 hours
- Intelligent categorization by file paths and labels
- Contributor activity summary
- Links to all PRs for detailed review

### Review Queue
- PRs awaiting your review
- Stale PRs that need attention
- Urgency indicators for critical changes

### Smart Categorization for BigQuery-ETL
- **Firefox Data Products**: `sql/moz-fx-data-shared-prod/`
- **Airflow Pipelines**: `dags/`
- **ETL Tooling**: `bigquery_etl/`
- **Testing**: `tests/`
- And more...

## Privacy & Security

- Uses GitHub Personal Access Token with read-only repository scope
- No code content is ever sent to external services
- Only PR metadata (titles, labels, file paths) used for categorization
- All outputs stored locally

## Roadmap

- [x] Daily digest generation
- [x] Review queue functionality
- [ ] Weekly narrative reports
- [ ] MCP integration for Claude summarization
- [ ] Slack integration for notifications
- [ ] Multiple repository support

## Requirements

- Python 3.8+
- GitHub Personal Access Token with `repo` read permissions
- Internet connection for GitHub API access