# GitHubOracle Architecture

## Overview

GitHubOracle is a RAG (Retrieval-Augmented Generation) system that combines structured data queries with semantic search to answer natural language questions about GitHub repository activity.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                │
│              "What did Alice ship last week?"               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLI (cli.py)                             │
│                   Command Router                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHubOracle (github_oracle.py)                │
│                  Main Orchestrator                          │
│                                                             │
│  ask() → plan → execute → synthesize → answer              │
└──────┬───────────────────────────┬──────────────────────────┘
       │                           │
       ▼                           ▼
┌──────────────────┐      ┌───────────────────┐
│  QueryPlanner    │      │   DataSource      │
│ (query_planner)  │      │ (bq_data_source)  │
│                  │      │                   │
│ NL → QueryPlan   │      │ Execute Queries   │
└────┬─────────────┘      └────┬──────────────┘
     │                         │
     │ Uses LLM                │ Queries BigQuery
     │                         │
     ▼                         ▼
┌──────────────────┐      ┌───────────────────┐
│   LLMClient      │      │    BigQuery       │
│ (llm_client)     │      │                   │
│                  │      │  • gkabbz_gh_prs  │
│ Claude API       │      │  • reviews        │
└──────────────────┘      │  • files          │
                          │  • labels         │
                          └───────────────────┘
```

## Component Details

### 1. CLI Layer (`cli.py`)

**Purpose:** Command-line interface for user interaction

**Key Functions:**
- `ask` command - main entry point
- Argument parsing and validation
- Environment configuration

**Input:** Natural language question
**Output:** Natural language answer

---

### 2. GitHubOracle (`github_oracle.py`)

**Purpose:** Main orchestrator that coordinates all components

**Key Methods:**
- `ask(question)` - Main entry point
- `_execute_query(plan)` - Route query to data source
- `_synthesize_answer(question, prs, plan)` - Generate answer

**Flow:**
```python
def ask(question):
    plan = query_planner.plan(question)      # Step 1: Understand question
    prs = data_source.execute(plan)          # Step 2: Get data
    answer = llm_client.synthesize(prs)      # Step 3: Generate answer
    return answer
```

**Dependencies:**
- `QueryPlanner` - for understanding questions
- `DataSource` - for retrieving data
- `LLMClient` - for generating answers

---

### 3. QueryPlanner (`query_planner.py`)

**Purpose:** Convert natural language → structured query parameters

**Key Classes:**
- `QueryType` - Enum (STRUCTURED, SEMANTIC, HYBRID)
- `QueryPlan` - Dataclass with query parameters
- `LLMQueryPlanner` - Main planner class

**Process:**
1. Send question + system prompt to LLM
2. LLM returns JSON with query parameters
3. Parse JSON into `QueryPlan` object

**Example:**
```python
Input:  "What did Alice ship last week?"
Output: QueryPlan(
    query_type=STRUCTURED,
    author="alice",
    start_date=datetime(2024, 10, 15),
    end_date=datetime(2024, 10, 22),
    limit=10
)
```

---

### 4. Data Source Layer

#### Abstract Interface (`data_source.py`)

**Purpose:** Define contract for data access

**Methods:**
- `find_prs_by_author(author, repo, limit)`
- `find_prs_by_reviewer(reviewer, repo, limit)`
- `find_prs_by_date_range(start, end, repo, limit)`
- `find_prs_by_file(filename, repo, limit)`
- `find_prs_by_directory(directory, repo, limit)`
- `semantic_search(query, repo, limit)`
- `get_pr_detail(repo, pr_number)`

#### BigQuery Implementation (`bq_data_source.py`)

**Purpose:** Execute queries against BigQuery

**Key Features:**
- Parameterized queries (SQL injection prevention)
- Semantic search using `ML.DISTANCE()`
- JOIN operations for reviews/files/labels
- SELECT DISTINCT to prevent duplicates

**Example Query:**
```sql
SELECT DISTINCT
    repo_name, number, title, body, state, author, ...
FROM `mozdata-nonprod.analysis.gkabbz_gh_prs`
WHERE author = @author
  AND created_at BETWEEN @start_date AND @end_date
ORDER BY created_at DESC
LIMIT 10
```

---

### 5. LLM Client (`llm_client.py`)

**Purpose:** Interface for calling LLM APIs

**Key Classes:**
- `LLMClient` - Abstract interface
- `AnthropicLLMClient` - Claude implementation
- `LLMResponse` - Response dataclass

**Features:**
- Retry logic with exponential backoff
- Token usage tracking
- Cost calculation
- Temperature control

**Configuration:**
- Model selection in `config.py`
- Pricing in `config.py`
- API key in `.env`

---

### 6. Data Models (`models.py`)

**Purpose:** Type-safe data structures

**Key Models:**
- `PullRequest` - PR metadata
- `User` - Author/reviewer info
- `PRState` - Enum (OPEN, CLOSED, MERGED)

---

## Data Flow Example

### Question: "What did Alice ship last week?"

#### Step 1: Query Planning
```
User Question
    ↓
QueryPlanner.plan()
    ↓
LLM analyzes question
    ↓
Returns JSON:
{
  "query_type": "structured",
  "author": "alice",
  "start_date": "2024-10-15",
  "end_date": "2024-10-22"
}
    ↓
Parsed into QueryPlan object
```

#### Step 2: Query Execution
```
QueryPlan
    ↓
GitHubOracle._execute_query()
    ↓
Routes to: data_source.find_prs_by_author()
    ↓
BigQuery SQL:
SELECT * FROM prs
WHERE author = 'alice'
  AND created_at BETWEEN '2024-10-15' AND '2024-10-22'
    ↓
Returns: List[PullRequest]
```

#### Step 3: Answer Synthesis
```
List[PullRequest] + Original Question
    ↓
GitHubOracle._synthesize_answer()
    ↓
Build context from PRs:
  PR #123: Add auth feature
  PR #124: Fix login bug
  PR #125: Update docs
    ↓
LLM generates natural language answer:
"Alice shipped 3 PRs last week, including..."
    ↓
Return to user
```

---

## Query Type Routing

### Structured Queries
**When:** Filtering by metadata (author, date, reviewer, file)

**Route:**
- `find_prs_by_author()`
- `find_prs_by_reviewer()`
- `find_prs_by_date_range()`
- `find_prs_by_file()`
- `find_prs_by_directory()`

**Example:** "What did Alice ship last week?"

---

### Semantic Queries
**When:** Searching by concept/meaning

**Route:**
- `semantic_search()`

**How it works:**
1. Generate embedding for query (768 dims)
2. Calculate cosine distance to PR body embeddings
3. Return PRs with lowest distance (most similar)

**Example:** "Find PRs about database migrations"

---

### Hybrid Queries
**When:** Combining metadata filters + semantic search

**Route:**
- `semantic_search()` with author/date filters

**Example:** "What authentication changes did Bob make?"

**Note:** Currently implements semantic search; structured filters could be added to SQL WHERE clause in future enhancement.

---

## Database Schema

### Table: `gkabbz_gh_prs`
- Core PR metadata
- **Partitioned by:** `merged_at` (for query performance)
- **Vector column:** `body_embedding` (768 dims, REPEATED FLOAT64)

### Table: `gkabbz_gh_reviews`
- Review metadata (reviewer, state, body)
- **Partitioned by:** `submitted_at`

### Table: `gkabbz_gh_files`
- File changes per PR
- **Clustered by:** `repo_name`, `number`

### Table: `gkabbz_gh_labels`
- PR labels
- **Clustered by:** `repo_name`, `number`

---

## Configuration Management

### Project-level Config (`config.py`)
```python
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_PRICING = {...}
```

**Update here when:** New models are released

---

### Environment Config (`.env`)
```bash
ANTHROPIC_API_KEY=sk-ant-...
BQ_PROJECT_ID=mozdata-nonprod
BQ_DATASET_ID=analysis
TABLE_PREFIX=gkabbz_gh
GITHUB_REPOSITORY=mozilla/bigquery-etl
```

**Update here for:** Secrets, environment-specific settings

---

## Error Handling

### LLM Client
- **Retries:** 3 attempts with exponential backoff
- **Timeout:** Configurable per request
- **Errors:** API failures, rate limits, invalid responses

### Query Planner
- **JSON parsing:** Validates LLM response is valid JSON
- **Type validation:** Ensures all fields match expected types
- **Fallbacks:** Default to structured query if type unclear

### Data Source
- **SQL injection:** Prevented via parameterized queries
- **Empty results:** Returns empty list (not error)
- **BigQuery errors:** Propagate with context

---

## Performance Considerations

### Query Performance
- **Partitioning:** Queries filtered by date use partition pruning
- **Clustering:** File/label queries benefit from clustering
- **Limits:** Default limit=10 to prevent large result sets

### Token Usage
- **Context limits:** Truncate PR bodies to 200 chars in synthesis
- **Max PRs:** Only send top 10 PRs to LLM for answer
- **Temperature:** 0.0 for planning (deterministic), 0.3 for synthesis (creative)

### Cost Optimization
- **Caching:** Could add LRU cache for common queries
- **Batch processing:** Single LLM call per query (no back-and-forth)
- **Model selection:** Use Haiku for cheaper queries if quality acceptable

---

## Security

### SQL Injection Prevention
```python
# BAD - vulnerable
query = f"SELECT * FROM prs WHERE author = '{user_input}'"

# GOOD - safe
query = "SELECT * FROM prs WHERE author = @author"
params = [bigquery.ScalarQueryParameter("author", "STRING", user_input)]
```

### API Key Management
- Stored in `.env` (not committed)
- Loaded via `python-dotenv`
- Never logged or exposed in output

### Data Access
- Uses authenticated BigQuery client
- Respects existing IAM permissions
- No data modification (read-only)

---

## Testing Strategy

### Unit Tests
- `test_llm_client.py` - LLM API calls
- `test_query_planner.py` - NL → QueryPlan parsing
- `test_bq_data_source.py` - Individual query methods

### Integration Tests
- `test_github_oracle.py` - End-to-end flow
- Tests against real BigQuery data
- Validates LLM responses

### Manual Testing
- CLI testing with various question types
- Cost tracking for different query patterns
- Error scenario validation

---

## Future Enhancements

### Phase 2
- **User lookup table:** Map GitHub handles → real names
- **Enhanced hybrid queries:** Apply structured filters in SQL
- **Query caching:** Cache common query results
- **Streaming responses:** Return partial results as they come

### Phase 3
- **Web UI:** Browser-based interface
- **Slack integration:** Query via Slack bot
- **Multi-repo:** Support queries across multiple repositories
- **Trend analysis:** "How has velocity changed over time?"

---

## Dependencies

### Core
- `google-cloud-bigquery` - Data queries
- `google-cloud-aiplatform` - Embeddings
- `anthropic` - Claude API
- `python-dotenv` - Environment config

### Data Models
- `pydantic` - Type validation
- `dataclasses` - Simple data structures

### CLI
- `argparse` - Command-line parsing
- `click` (optional) - Enhanced CLI features

---

**Last Updated:** 2025-10-23
