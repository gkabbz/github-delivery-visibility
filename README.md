# GitHub Delivery Visibility

An AI-powered tool for querying GitHub repository activity using natural language. Ask questions like "What did Alice ship last week?" or "Find PRs about database migrations" and get intelligent answers powered by LLMs and vector search.

## Overview

**GitHubOracle** is your intelligent assistant for understanding GitHub repository activity. It combines:
- **BigQuery storage** for PR metadata and file changes
- **Vector embeddings** for semantic search
- **LLM-powered query planning** to understand natural language questions
- **Smart answer synthesis** with relevant context

### Key Questions You Can Ask

- "What did [person] ship last week?"
- "Tell me about PR #123"
- "Find PRs about database migrations"
- "What changed in the monitoring/ directory?"
- "Who reviewed PR #456?"
- "Find authentication-related changes"

## Quick Start

### 1. Prerequisites
- Python 3.12+
- Google Cloud access (BigQuery)
- Anthropic API key

### 2. Setup

```bash
# Clone/navigate to project
cd gh-del-visibility

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add:
#   - ANTHROPIC_API_KEY
#   - BQ_PROJECT_ID (optional, defaults to mozdata-nonprod)
#   - BQ_DATASET_ID (optional, defaults to analysis)
#   - TABLE_PREFIX (optional, defaults to gkabbz_gh)
```

### 3. Use the `ghoracle` Command

```bash
# Make sure ghoracle is in your PATH (see Installation section)
ghoracle "Tell me about PR #8127"
ghoracle "Find PRs about monitoring"
ghoracle "What did BenWu ship last week?"
```

## Installation

### Make `ghoracle` Available Globally

Add the project to your PATH by adding this line to `~/.zshrc` (or `~/.bashrc`):

```bash
export PATH="$PATH:/path/to/gh-del-visibility"
```

Then reload your shell:
```bash
source ~/.zshrc
```

Now you can use `ghoracle` from anywhere!

## Architecture

### Components

**1. Data Access Layer** (`bq_data_source.py`)
- Queries BigQuery for PR data
- Supports 7 query types:
  - Find by author
  - Find by reviewer
  - Find by date range
  - Find by file
  - Find by directory
  - Semantic search (vector similarity)
  - Get PR detail

**2. LLM Integration** (`llm_client.py`, `query_planner.py`)
- `LLMClient`: Abstract interface for calling LLMs (supports Anthropic Claude)
- `QueryPlanner`: Converts natural language → structured query plans
- Automatically determines query type (structured, semantic, or hybrid)

**3. GitHubOracle** (`github_oracle.py`)
- Main orchestrator that wires everything together
- Plans queries, executes them, and synthesizes natural language answers

**4. CLI** (`cli.py`)
- Simple command-line interface
- `ask` command for natural language queries

### Data Flow

```
User Question
    ↓
Query Planner (LLM)
    ↓
Query Plan (structured parameters)
    ↓
Data Source (BigQuery)
    ↓
PR Results
    ↓
Answer Synthesizer (LLM)
    ↓
Natural Language Answer
```

## Configuration

### Model Configuration

Update model versions in `src/github_delivery/config.py`:

```python
# Current model
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# Pricing (USD per 1M tokens)
ANTHROPIC_PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    ...}
```

### Environment Variables

Create `.env` file with:

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional (defaults shown)
BQ_PROJECT_ID=mozdata-nonprod
BQ_DATASET_ID=analysis
TABLE_PREFIX=gkabbz_gh
GITHUB_REPOSITORY=mozilla/bigquery-etl
```

## Usage Examples

### Basic Queries

```bash
# Ask about a specific PR
ghoracle "Tell me about PR #8127"

# Find PRs by author
ghoracle "What did gkabbz ship last week?"

# Semantic search
ghoracle "Find PRs about database migrations"
ghoracle "Find authentication changes"
ghoracle "What monitoring changes were made?"
```

### Advanced Queries

```bash
# Hybrid queries (author + semantic)
ghoracle "What authentication changes did scholtzan make?"

# Directory-based queries
ghoracle "What changed in the sql directory?"

# File-based queries
ghoracle "Show PRs that modified config.yaml"
```

### Verbose Output

```bash
# See what's happening under the hood
python -m src.github_delivery.cli ask "your question" --verbose
```

### Specify Repository

```bash
# Query a different repository
python -m src.github_delivery.cli ask "your question" --repo owner/repo-name
```

## Backfilling Historical Data

GitHubOracle requires PR data in BigQuery to answer questions. Use the backfill script to load historical PRs with embeddings.

### Basic Usage

```bash
# Backfill specific date range (recommended)
python scripts/backfill_data.py --start-date 2025-01-01 --end-date 2025-01-31

# Backfill with just start date (end date defaults to today)
python scripts/backfill_data.py --start-date 2025-01-01

# Test with dry-run first
python scripts/backfill_data.py --start-date 2025-01-01 --end-date 2025-01-07 --dry-run

# Verbose output for debugging
python scripts/backfill_data.py --start-date 2025-01-01 --end-date 2025-01-07 --verbose
```

### Examples

```bash
# Backfill January 2025
python scripts/backfill_data.py --start-date 2025-01-01 --end-date 2025-01-31

# Backfill last 3 months
python scripts/backfill_data.py --start-date 2025-07-01 --end-date 2025-10-01

# Backfill a specific week
python scripts/backfill_data.py --start-date 2025-01-01 --end-date 2025-01-07
```

### How It Works

The backfill uses a **staging table + MERGE pattern** for reliable, idempotent data loading:

1. **Collects PRs from GitHub** - Fetches merged PRs in date range + top 100 open PRs
2. **Generates embeddings** - Creates vector embeddings for PR bodies, review comments, and file patches
3. **Loads to staging tables** - Batch loads data to temporary staging tables (3-day auto-expiration)
4. **MERGE to production** - Uses BigQuery MERGE to upsert data:
   - **INSERT** new records that don't exist
   - **UPDATE** existing records (e.g., open PRs that got merged)
   - **Deduplicates** automatically using `ROW_NUMBER() OVER (PARTITION BY ...)`

### Safe Re-runs & Updates

The backfill script is **fully idempotent** - you can safely re-run it:

- **Handles duplicates**: MERGE automatically deduplicates based on primary keys
- **Updates existing data**: Open PRs get updated when they're merged
- **No streaming buffer errors**: Staging tables + batch loads avoid BigQuery limitations
- **Easy troubleshooting**: Staging tables persist for 3 days after failed runs

Example: If you backfill January, then run it again a week later:
- PRs that were open are now updated to merged status
- New PRs merged during the week are inserted
- No duplicate records are created

### Checking Status

```bash
# Check what's in your tables
python scripts/check_backfill_status.py
```

This shows row counts and recent entries for each table (PRs, reviews, files, labels).

### Important Notes

- **Date ranges**: Use specific start/end dates for precise control over what to backfill
- **Time required**: ~5-10 minutes per 100 PRs (embedding generation is the bottleneck)
- **Batch size**: Files are loaded in batches of 100 to avoid API limits
- **Required env vars**: `GITHUB_TOKEN`, `BQ_PROJECT_ID`, `BQ_DATASET_ID`, `TABLE_PREFIX`

## Testing

Test individual components:

```bash
# Test LLM client
python test_llm_client.py

# Test query planner
python test_query_planner.py

# Test data source methods
python test_bq_data_source.py
python test_bq_semantic.py
python test_bq_directory.py

# Test end-to-end
python test_github_oracle.py
```

## Project Structure

```
gh-del-visibility/
├── src/github_delivery/
│   ├── config.py              # Model configuration
│   ├── models.py              # Data models (PullRequest, etc.)
│   ├── data_source.py         # Abstract data source interface
│   ├── bq_data_source.py      # BigQuery implementation
│   ├── llm_client.py          # LLM client (Anthropic)
│   ├── query_planner.py       # Natural language → query plans
│   ├── github_oracle.py       # Main orchestrator
│   ├── cli.py                 # Command-line interface
│   ├── embeddings.py          # Vector embedding generation
│   └── bigquery_loader.py     # Load data to BigQuery
├── schemas/                   # BigQuery table schemas
├── test_*.py                  # Test scripts
├── ghoracle                   # Shortcut script
└── README.md                  # This file
```

## How It Works

### 1. Query Planning

The LLM analyzes your question and creates a structured query plan:

**Question:** "What did Alice ship last week?"

**Query Plan:**
```json
{
  "query_type": "structured",
  "author": "alice",
  "start_date": "2024-10-15",
  "end_date": "2024-10-22",
  "limit": 10
}
```

### 2. Query Execution

The query plan is executed against BigQuery using the appropriate method:
- Structured queries use SQL filters (author, date, file, etc.)
- Semantic queries use vector similarity search (cosine distance)
- Hybrid queries combine both approaches

### 3. Answer Synthesis

The LLM receives the PR results and generates a natural language answer:

**Input:** List of PRs with metadata

**Output:** "Alice shipped 3 PRs last week, including PR #123 which added new authentication features..."

## Privacy & Security

- **Local execution**: All processing happens in your environment
- **API keys**: Store securely in `.env` (not committed to git)
- **Data access**: Only queries BigQuery data you have access to
- **LLM calls**: Only PR metadata sent to Claude API (no secrets)

## Cost Estimates

**Anthropic API (Claude Sonnet 4):**
- Input: $3/million tokens
- Output: $15/million tokens
- Typical query: ~$0.001-0.003 per question

**BigQuery:**
- Storage: ~$20/TB/month
- Queries: ~$5/TB scanned
- Typical query: <$0.01

**Total:** ~$10-20/month for regular use

## Troubleshooting

### Command not found: ghoracle
- Make sure project directory is in your PATH
- Reload your shell: `source ~/.zshrc`

### API key errors
- Check `.env` has `ANTHROPIC_API_KEY`
- Make sure `load_dotenv()` is working
- Try: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('ANTHROPIC_API_KEY'))"`

### BigQuery permission errors
- Verify you have access to the project/dataset
- Check service account permissions if using one
- Try: `gcloud auth application-default login`

### No results found
- Verify data exists in BigQuery tables
- Check table prefix matches your configuration
- Try: `SELECT COUNT(*) FROM \`project.dataset.prefix_prs\``

## Development

### Adding New Query Types

1. Add method to `PRDataSource` abstract interface
2. Implement in `BigQueryDataSource`
3. Update `QueryPlan` with new parameters
4. Update `QueryPlanner` system prompt
5. Update `GitHubOracle._execute_query()` routing

### Adding New LLM Providers

1. Create new class implementing `LLMClient`
2. Implement `generate()` method
3. Add pricing to config
4. Update CLI to support new provider

### Running Tests

```bash
# Run all component tests
python test_llm_client.py
python test_query_planner.py
python test_bq_data_source.py
python test_github_oracle.py
```

## Roadmap

### Phase 1: MVP ✅ (Complete)
- [x] Data collection pipeline
- [x] BigQuery schema with embeddings
- [x] LLM integration (query planning + synthesis)
- [x] GitHubOracle orchestrator
- [x] CLI with `ask` command

### Phase 2: Enhanced Queries (Next)
- [ ] User lookup table (GitHub handle → real name)
- [ ] Weekly/monthly digest generation
- [ ] Trend analysis over time
- [ ] Contributor analytics

### Phase 3: Scale & Integration
- [ ] Slack bot integration
- [ ] Email digest automation
- [ ] Multi-repository support
- [ ] Web UI

## Contributing

This is a personal project, but suggestions welcome! See `project_plans/project_plan.md` for detailed implementation plans.

## License

Personal project - not licensed for distribution.

---

**Built with:** Python, BigQuery, Anthropic Claude, Vertex AI Embeddings
