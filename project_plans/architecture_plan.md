# GitHub Delivery Visibility - Architecture Plan

**Version:** 1.0
**Date:** October 16, 2025
**Author:** Technical Team
**Status:** Draft

---

## 1. Executive Summary

### 1.1 Architecture Overview

This document defines the technical architecture for the GitHub Delivery Visibility system - a hybrid RAG (Retrieval Augmented Generation) system that combines structured metadata queries with semantic search to enable natural language insights about GitHub activity.

**Architecture Pattern:** Hybrid RAG with LLM orchestration
- **Structured data** (metadata) → BigQuery tables for filtering
- **Unstructured content** (text) → Vector embeddings for semantic search
- **LLM layer** → Query translation and insight synthesis

### 1.2 Key Design Principles

1. **Separation of Concerns:** Structured queries vs. semantic search
2. **Abstraction:** Data access layer decoupled from storage implementation
3. **Extensibility:** Easy migration to alternative storage/search solutions
4. **Serverless-First:** Minimize operational overhead with managed services
5. **Cost-Effective:** Stay within $100/month budget
6. **GCP-Native:** Leverage existing Mozilla GCP infrastructure

### 1.3 Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Data Collection** | Cloud Run (scheduled job) | Serverless, cost-effective, easy deployment |
| **Data Storage** | BigQuery | Structured + vector columns, SQL familiarity, scalable |
| **Vector Search** | BigQuery vector columns | Single system, no additional service needed |
| **LLM** | Anthropic Claude API | Superior reasoning, can migrate to Vertex AI later |
| **Embeddings** | textembedding-gecko@003 (768-dim) | Better semantic understanding, upgrade from 384-dim prototype |
| **Query Interface** | Python CLI + API | Fast to build, easy to extend |
| **Orchestration** | Cloud Scheduler | Trigger daily data collection |

---

## 2. System Architecture

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub API                               │
│              (Source: mozilla/bigquery-etl)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Daily collection
                           │
                 ┌─────────▼─────────┐
                 │   Cloud Run Job   │
                 │   (Collector)     │
                 │                   │
                 │ - Fetch PRs       │
                 │ - Enrich metadata │
                 │ - Generate embeds │
                 └─────────┬─────────┘
                           │
                           │ Load data
                           │
          ┌────────────────▼────────────────┐
          │        BigQuery                 │
          │                                 │
          │  ┌──────────────────────────┐  │
          │  │ Structured Metadata      │  │
          │  │ - prs (dates, authors)   │  │
          │  │ - reviews (reviewers)    │  │
          │  │ - files (paths)          │  │
          │  └──────────────────────────┘  │
          │                                 │
          │  ┌──────────────────────────┐  │
          │  │ Vector Embeddings        │  │
          │  │ - body_embedding         │  │
          │  │ - review_embedding       │  │
          │  │ - patch_embedding        │  │
          │  └──────────────────────────┘  │
          └────────────────┬────────────────┘
                           │
                           │ Query
                           │
                 ┌─────────▼─────────┐
                 │  Query Engine     │
                 │  (Python)         │
                 │                   │
                 │ - SQL generation  │
                 │ - Vector search   │
                 │ - Result merging  │
                 └─────────┬─────────┘
                           │
                           │ Context + Query
                           │
                 ┌─────────▼─────────┐
                 │   LLM Layer       │
                 │   (Claude API)    │
                 │                   │
                 │ - Query planning  │
                 │ - Synthesis       │
                 │ - Insight extract │
                 └─────────┬─────────┘
                           │
                           │ Natural language
                           │
                 ┌─────────▼─────────┐
                 │   User Interface  │
                 │                   │
                 │ - CLI             │
                 │ - Python API      │
                 │ - (Future: Web)   │
                 └───────────────────┘
```

### 2.2 Data Flow

#### 2.2.1 Collection Flow (Daily)

```
1. Cloud Scheduler triggers Cloud Run job (daily @ 2am)
   ↓
2. GitHubCollector fetches merged PRs from last 48 hours
   ↓
3. For each PR:
   - Extract metadata (dates, authors, reviewers)
   - Fetch file changes with patches
   - Fetch review comments
   ↓
4. Generate embeddings:
   - PR body → body_embedding
   - Review comments → review_embedding
   - File patches → patch_embedding
   ↓
5. Load to BigQuery:
   - INSERT/MERGE into prs table
   - INSERT into reviews table
   - INSERT into files table
   ↓
6. Log completion, send monitoring alert if failed
```

#### 2.2.2 Query Flow (User-Initiated)

```
1. User asks natural language question
   "What authentication changes happened last month?"
   ↓
2. LLM analyzes question, determines:
   - Intent: semantic search
   - Filters: date range = last month
   - Semantic query: "authentication changes"
   ↓
3. Query Engine generates hybrid query:
   - SQL filter: WHERE merged_at >= '2025-09-16'
   - Vector search: VECTOR_SEARCH(body_embedding, 'authentication')
   ↓
4. BigQuery executes query, returns:
   - 8 PRs matching filters + semantic similarity
   - Includes: titles, bodies, review comments
   ↓
5. LLM receives context:
   - User question
   - 8 PR records with full content
   - Database schema
   ↓
6. LLM synthesizes answer:
   - Reads PR content
   - Identifies patterns
   - Extracts key changes
   - Generates narrative summary
   ↓
7. User receives formatted response
```

---

## 3. Data Model

### 3.1 BigQuery Schema

#### Table: `github_prs.prs`

**Purpose:** Core PR metadata and content

```sql
CREATE TABLE `github_prs.prs` (
  -- Identity
  repo_name STRING NOT NULL,
  number INT64 NOT NULL,

  -- Content (for RAG)
  title STRING NOT NULL,
  body STRING,
  body_embedding ARRAY<FLOAT64>,  -- 768-dimensional vector

  -- Metadata
  state STRING NOT NULL,  -- 'open', 'closed', 'merged'
  author STRING NOT NULL,
  html_url STRING NOT NULL,

  -- Timestamps
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  merged_at TIMESTAMP,
  closed_at TIMESTAMP,

  -- Branch info
  base_branch STRING,
  head_branch STRING,

  -- Size metrics
  additions INT64,
  deletions INT64,
  changed_files INT64,

  -- Flags
  draft BOOL,

  -- Cache tracking
  cached_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(merged_at)
CLUSTER BY repo_name, author, merged_at
OPTIONS (
  description = "Core PR metadata with vector embeddings for semantic search"
);

-- Primary key constraint (not enforced, but documented)
-- PRIMARY KEY: (repo_name, number)
```

#### Table: `github_prs.reviews`

**Purpose:** PR review data with sentiment/feedback analysis

```sql
CREATE TABLE `github_prs.reviews` (
  -- Identity
  review_id INT64 NOT NULL,
  repo_name STRING NOT NULL,
  pr_number INT64 NOT NULL,

  -- Reviewer
  reviewer STRING NOT NULL,

  -- Review content (for RAG)
  body STRING,
  body_embedding ARRAY<FLOAT64>,  -- 768-dimensional vector

  -- Review metadata
  state STRING NOT NULL,  -- 'APPROVED', 'CHANGES_REQUESTED', 'COMMENTED'
  submitted_at TIMESTAMP NOT NULL,
  html_url STRING,

  -- Cache tracking
  cached_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(submitted_at)
CLUSTER BY repo_name, reviewer, pr_number
OPTIONS (
  description = "PR reviews with vector embeddings for feedback analysis"
);

-- PRIMARY KEY: (review_id)
-- FOREIGN KEY: (repo_name, pr_number) REFERENCES prs(repo_name, number)
```

#### Table: `github_prs.files`

**Purpose:** File changes with code diffs

```sql
CREATE TABLE `github_prs.files` (
  -- Identity
  id INT64 NOT NULL,  -- Auto-generated
  repo_name STRING NOT NULL,
  pr_number INT64 NOT NULL,

  -- File info
  filename STRING NOT NULL,

  -- Change metrics
  additions INT64,
  deletions INT64,
  status STRING,  -- 'added', 'deleted', 'modified', 'renamed'

  -- Code diff (for RAG)
  patch STRING,
  patch_embedding ARRAY<FLOAT64>,  -- 768-dimensional vector
  patch_truncated BOOL DEFAULT FALSE,

  -- Cache tracking
  cached_at TIMESTAMP NOT NULL
)
CLUSTER BY repo_name, pr_number
OPTIONS (
  description = "File changes with patch embeddings for code analysis"
);

-- PRIMARY KEY: (id)
-- FOREIGN KEY: (repo_name, pr_number) REFERENCES prs(repo_name, number)
```

#### Table: `github_prs.labels`

**Purpose:** PR labels for categorization

```sql
CREATE TABLE `github_prs.labels` (
  repo_name STRING NOT NULL,
  pr_number INT64 NOT NULL,
  label_name STRING NOT NULL,
  label_color STRING,
  label_description STRING
)
CLUSTER BY repo_name, pr_number
OPTIONS (
  description = "PR labels for categorization"
);

-- PRIMARY KEY: (repo_name, pr_number, label_name)
-- FOREIGN KEY: (repo_name, pr_number) REFERENCES prs(repo_name, number)
```

### 3.2 Indexes and Partitioning

**Partitioning Strategy:**
- `prs`: Partitioned by `DATE(merged_at)` for time-based queries
- `reviews`: Partitioned by `DATE(submitted_at)` for time-based filtering

**Clustering Strategy:**
- `prs`: Clustered by `(repo_name, author, merged_at)` for common access patterns
- `reviews`: Clustered by `(repo_name, reviewer, pr_number)` for reviewer queries
- `files`: Clustered by `(repo_name, pr_number)` for PR-based access

**Benefits:**
- Time-based partitioning reduces scan costs
- Clustering optimizes for common query patterns
- Supports efficient filtering + vector search

### 3.3 Data Retention

**Policy:**
- Keep all PR data indefinitely (storage is cheap)
- Partition pruning keeps query costs low
- Consider archiving PRs > 2 years to cold storage (future)

---

## 4. Component Architecture

### 4.1 Data Collection Layer

#### Component: `GitHubCollector`

**Responsibility:** Fetch PR data from GitHub API

**Location:** `src/github_delivery/collector.py` (existing)

**Key Methods:**
- `get_merged_prs(since, until)` - Fetch merged PRs in time range
- `_enrich_pull_request(pr)` - Add files and reviews
- `_make_request(url)` - API call with retry logic

**Enhancements Needed:**
- Generate embeddings for PR content
- Handle rate limiting more gracefully
- Add progress tracking for large batches

#### Component: `EmbeddingGenerator`

**Responsibility:** Generate vector embeddings for text content

**Location:** `src/github_delivery/embeddings.py` (new)

**Interface:**
```
class EmbeddingGenerator:
    def generate_embedding(text: str) -> List[float]
    def generate_batch_embeddings(texts: List[str]) -> List[List[float]]
```

**Implementation Options:**

**Option A: Vertex AI Text Embeddings (Recommended)**
- Model: `textembedding-gecko@003`
- Dimension: 768
- Cost: ~$0.025 per 1000 texts
- Integration: Native GCP API
- Quality: Better semantic understanding than 384-dim models

**Option B: Sentence Transformers (Fallback)**
- Model: `all-mpnet-base-v2` (768-dim, better quality)
- Alternate: `all-MiniLM-L6-v2` (384-dim, faster but less accurate)
- Cost: Free (run locally)
- Integration: Python library

**Decision:** Use Vertex AI textembedding-gecko@003 (768 dimensions) for production. This provides better semantic understanding than the 384-dim model used in the Firestore prototype, which will improve query relevance for complex questions about PR content, change requests, and themes.

#### Component: `BigQueryLoader`

**Responsibility:** Load data into BigQuery tables

**Location:** `src/github_delivery/bq_loader.py` (new)

**Key Methods:**
```
class BigQueryLoader:
    def load_prs(prs: List[PullRequest]) -> None
    def load_reviews(reviews: List[Review]) -> None
    def load_files(files: List[FileStat]) -> None
    def upsert_pr(pr: PullRequest) -> None  # For updates
```

**Write Strategy:**
- Use `MERGE` statements for idempotency (handle re-runs)
- Batch inserts for efficiency (100-500 rows per batch)
- Handle schema evolution gracefully

#### Component: `DataPipeline`

**Responsibility:** Orchestrate collection → embedding → loading

**Location:** `src/github_delivery/pipeline.py` (new)

**Main Flow:**
```
class DataPipeline:
    def run_daily_collection(repo: str, since_hours: int = 48):
        1. Fetch PRs from GitHub
        2. Generate embeddings for all text content
        3. Load to BigQuery
        4. Log metrics and status
```

**Deployment:** Cloud Run job triggered by Cloud Scheduler

### 4.2 Data Access Layer

#### Component: `PRDataSource` (Abstract Interface)

**Responsibility:** Define data access contract

**Location:** `src/github_delivery/data_source.py` (new)

**Interface:**
```python
class PRDataSource(ABC):
    """Abstract interface for PR data access"""

    @abstractmethod
    def find_prs_by_author(
        self,
        repo: str,
        author: str,
        since: datetime = None,
        until: datetime = None
    ) -> List[PullRequest]:
        pass

    @abstractmethod
    def find_prs_by_reviewer(
        self,
        repo: str,
        reviewer: str,
        since: datetime = None
    ) -> List[PullRequest]:
        pass

    @abstractmethod
    def find_prs_by_date_range(
        self,
        repo: str,
        since: datetime,
        until: datetime
    ) -> List[PullRequest]:
        pass

    @abstractmethod
    def semantic_search(
        self,
        repo: str,
        query_text: str,
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[PullRequest]:
        pass

    @abstractmethod
    def get_pr_detail(
        self,
        repo: str,
        pr_number: int
    ) -> PullRequest:
        pass

    @abstractmethod
    def get_file_changes(
        self,
        repo: str,
        directory_prefix: str,
        since: datetime = None
    ) -> List[FileStat]:
        pass
```

**Why Abstract Interface:**
- Enables testing with mock implementations
- Allows migration to different storage backends
- Decouples application logic from storage details

#### Component: `BigQueryDataSource`

**Responsibility:** Implement data access using BigQuery

**Location:** `src/github_delivery/bq_data_source.py` (new)

**Implementation:**
```python
class BigQueryDataSource(PRDataSource):
    """BigQuery implementation of data access"""

    def __init__(self, project_id: str, dataset_id: str):
        self.client = bigquery.Client(project=project_id)
        self.dataset_id = dataset_id

    def find_prs_by_author(self, repo, author, since=None, until=None):
        # Generate SQL query
        # Execute in BigQuery
        # Transform results to PullRequest objects
        pass

    def semantic_search(self, repo, query_text, limit=10, filters=None):
        # Generate embedding for query_text
        # Build SQL with VECTOR_SEARCH
        # Apply filters (date, author, etc.)
        # Execute and return results
        pass
```

**Key Features:**
- SQL query generation from parameters
- Result transformation to domain objects
- Connection pooling and error handling
- Query logging for debugging

### 4.3 LLM Integration Layer

#### Component: `LLMQueryPlanner`

**Responsibility:** Translate natural language to structured queries

**Location:** `src/github_delivery/llm_planner.py` (new)

**Interface:**
```python
class LLMQueryPlanner:
    """Translates natural language questions to query plans"""

    def plan_query(self, question: str) -> QueryPlan:
        """
        Analyze question and generate query plan

        Returns QueryPlan with:
        - query_type: 'structured', 'semantic', 'hybrid'
        - filters: Dict of field filters
        - semantic_query: Optional text for vector search
        - aggregations: List of aggregations needed
        """
        pass
```

**Query Plan Types:**

**Structured:** Pure metadata filtering
- Example: "Who reviewed PR #8244?"
- Plan: `{type: 'structured', filters: {pr_number: 8244}, get: 'reviewers'}`

**Semantic:** Content-based search
- Example: "Find authentication-related PRs"
- Plan: `{type: 'semantic', semantic_query: 'authentication', limit: 10}`

**Hybrid:** Filter + semantic
- Example: "What auth changes happened last month?"
- Plan: `{type: 'hybrid', filters: {since: '2025-09-16'}, semantic_query: 'authentication'}`

#### Component: `InsightSynthesizer`

**Responsibility:** Transform query results into insights

**Location:** `src/github_delivery/llm_synthesizer.py` (new)

**Interface:**
```python
class InsightSynthesizer:
    """Synthesizes insights from query results"""

    def synthesize_answer(
        self,
        question: str,
        results: List[Dict],
        context: Dict = None
    ) -> str:
        """
        Generate natural language answer from results

        Args:
            question: Original user question
            results: Query results (PRs, reviews, etc.)
            context: Additional context (user preferences, etc.)

        Returns:
            Natural language answer with insights
        """
        pass

    def generate_digest(
        self,
        prs: List[PullRequest],
        period: str = 'week'
    ) -> str:
        """Generate formatted digest of PR activity"""
        pass
```

**Key Responsibilities:**
- Extract specific info from PR content (table names, bug impacts)
- Identify patterns across multiple PRs
- Format output appropriately for audience
- Cite sources (link back to PRs)

#### Component: `LLMClient`

**Responsibility:** Manage LLM API interactions

**Location:** `src/github_delivery/llm_client.py` (new)

**Interface:**
```python
class LLMClient:
    """Abstract interface for LLM providers"""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        pass

class AnthropicLLMClient(LLMClient):
    """Anthropic Claude implementation"""
    pass

class VertexAILLMClient(LLMClient):
    """Google Vertex AI Gemini implementation"""
    pass
```

**Features:**
- Retry logic with exponential backoff
- Rate limiting
- Cost tracking
- Response caching
- Error handling

### 4.4 Application Layer

#### Component: `SecondBrain`

**Responsibility:** Main application interface

**Location:** `src/github_delivery/second_brain.py` (new)

**Interface:**
```python
class SecondBrain:
    """
    Main interface for GitHub delivery insights
    """

    def __init__(
        self,
        data_source: PRDataSource,
        llm_client: LLMClient,
        embedding_generator: EmbeddingGenerator
    ):
        self.data_source = data_source
        self.planner = LLMQueryPlanner(llm_client)
        self.synthesizer = InsightSynthesizer(llm_client)
        self.embeddings = embedding_generator

    def ask(self, question: str, repo: str = None) -> str:
        """
        Ask a question in natural language

        Examples:
            brain.ask("What shipped last week?")
            brain.ask("Who reviewed PR #8244?")
            brain.ask("What auth changes happened?")
        """
        # 1. Plan the query
        plan = self.planner.plan_query(question)

        # 2. Execute query via data source
        results = self._execute_plan(plan, repo)

        # 3. Synthesize answer
        answer = self.synthesizer.synthesize_answer(
            question, results
        )

        return answer

    def generate_weekly_digest(
        self,
        repo: str,
        weeks_back: int = 1
    ) -> str:
        """Generate automated weekly digest"""
        pass

    def generate_monthly_report(
        self,
        repo: str,
        month: str = None
    ) -> str:
        """Generate monthly organizational report"""
        pass
```

#### Component: CLI Interface

**Location:** `src/github_delivery/cli.py` (enhance existing)

**Commands:**
```bash
# Interactive query
github-delivery ask "What shipped last week?"

# Generate digest
github-delivery digest weekly
github-delivery digest monthly

# Specific queries
github-delivery pr-detail 8244
github-delivery author-activity benwu --since 2w

# Admin commands
github-delivery collect --repo mozilla/bigquery-etl
github-delivery sync  # Run data collection manually
```

---

## 5. Deployment Architecture

### 5.1 GCP Project Structure

```
GCP Project: moz-fx-data-shared-prod
│
├── BigQuery Dataset: github_prs
│   ├── Table: prs
│   ├── Table: reviews
│   ├── Table: files
│   └── Table: labels
│
├── Cloud Run Services
│   ├── pr-collector (scheduled job)
│   └── query-api (future: REST API)
│
├── Cloud Scheduler
│   └── daily-collection (trigger @ 2am UTC)
│
├── Cloud Storage
│   └── gs://github-pr-cache/
│       └── backup/ (JSON backups, optional)
│
└── Service Accounts
    ├── collector-sa (GitHub API → BigQuery write)
    └── query-sa (BigQuery read only)
```

### 5.2 Cloud Run Job: PR Collector

**Container Spec:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY config.yaml .

CMD ["python", "-m", "src.github_delivery.pipeline"]
```

**Environment Variables:**
```
GITHUB_TOKEN=<secret>
GCP_PROJECT=moz-fx-data-shared-prod
BQ_DATASET=github_prs
REPO_NAME=mozilla/bigquery-etl
ANTHROPIC_API_KEY=<secret>
```

**Resource Allocation:**
- Memory: 1 GB
- CPU: 1 vCPU
- Timeout: 30 minutes
- Concurrency: 1 (no parallel jobs)

**Scheduling:**
- Trigger: Cloud Scheduler
- Schedule: `0 2 * * *` (daily @ 2am UTC)
- Timezone: UTC

### 5.3 Access Control (IAM)

**Service Account: `collector-sa`**
```
Roles:
- bigquery.dataEditor (write to github_prs dataset)
- bigquery.jobUser (run queries)
- aiplatform.user (generate embeddings)
```

**Service Account: `query-sa`**
```
Roles:
- bigquery.dataViewer (read from github_prs dataset)
- bigquery.jobUser (run queries)
- aiplatform.user (generate embeddings for queries)
```

**User Access:**
```
Engineering Managers:
- bigquery.dataViewer on github_prs dataset
- Can run CLI with their own credentials
```

### 5.4 Secrets Management

**Cloud Secret Manager:**
```
secrets/
├── github-token          # GitHub PAT
├── anthropic-api-key     # Claude API key
└── (future) slack-token  # For notifications
```

**Access:**
- Mounted as environment variables in Cloud Run
- Rotation policy: 90 days
- Audit logging enabled

---

## 6. Technology Decisions & Rationale

### 6.1 Storage: BigQuery with Vector Columns

**Decision:** Use BigQuery as primary storage with vector columns for embeddings

**Alternatives Considered:**
- Firestore (tried, querying was difficult)
- PostgreSQL + pgvector (more operational overhead)
- Separate vector DB (additional complexity)

**Rationale:**
- ✅ Single system for structured + unstructured data
- ✅ SQL familiarity for debugging/verification
- ✅ Automatic scaling and partitioning
- ✅ Cost-effective at this scale
- ✅ Native GCP integration
- ✅ Vector search recently GA (proven at scale)

**Trade-offs:**
- ⚠️ Vector search less mature than Pinecone/Weaviate
- ⚠️ Migration to better vector DB requires effort
- ✅ But: abstraction layer makes migration feasible

### 6.2 LLM: Anthropic Claude

**Decision:** Use Anthropic Claude API (start), migrate to Vertex AI if needed

**Alternatives Considered:**
- Vertex AI Gemini (cheaper, GCP-native)
- OpenAI GPT-4 (powerful, but separate vendor)
- Local models (free, but limited capability)

**Rationale:**
- ✅ Best reasoning capability for complex queries
- ✅ Better at SQL generation than Gemini
- ✅ Can migrate to Vertex AI later (abstraction layer)
- ✅ Cost reasonable at expected scale (~$10-30/month)

**Migration Path:**
- If Claude costs too high → switch to Gemini via `VertexAILLMClient`
- Interface abstraction makes this straightforward

### 6.3 Embeddings: Vertex AI Text Embeddings

**Decision:** Use Vertex AI textembedding-gecko for embedding generation

**Alternatives Considered:**
- Sentence Transformers (local, free)
- OpenAI embeddings (separate vendor)
- BGE embeddings (newer, potentially better)

**Rationale:**
- ✅ GCP-native, unified billing
- ✅ 768 dimensions provides better semantic understanding than 384-dim
- ✅ Upgrade from Firestore prototype (used 384-dim all-MiniLM-L6-v2)
- ✅ Better at capturing nuance in technical content (PR descriptions, code reviews)
- ✅ Cost-effective (~$0.025 per 1000 = ~$0.75/month for 30K embeddings)
- ✅ Managed service (no ops)
- ✅ Storage cost difference negligible (300 PRs × 768 dims = ~1MB)

**Why 768 vs 384 dimensions:**
- Previous Firestore prototype used 384-dim embeddings
- For your use case (understanding "nature of change requests", themes, impact), need richer semantic representation
- At your data volume, storage cost difference is ~$0.50/month
- Worth the investment for better query quality

**Fallback:**
- Can use Sentence Transformers `all-mpnet-base-v2` (768-dim) locally if cost becomes issue
- Would need to regenerate embeddings (migration cost)

### 6.4 Orchestration: Cloud Scheduler + Cloud Run

**Decision:** Use Cloud Scheduler to trigger Cloud Run job daily

**Alternatives Considered:**
- Kubernetes CronJob (operational overhead)
- Cloud Functions (15min timeout too short)
- Airflow (overkill for single job)

**Rationale:**
- ✅ Serverless, no infrastructure to manage
- ✅ Sufficient timeout (30 min)
- ✅ Easy to deploy and monitor
- ✅ Cost-effective (pay per execution)
- ✅ Native GCP integration

---

## 7. Query Patterns & Examples

### 7.1 Structured Queries

**Query:** "Who reviewed PR #8244?"

**Execution Plan:**
```sql
SELECT r.reviewer, r.state, r.submitted_at
FROM github_prs.reviews r
WHERE r.repo_name = 'mozilla/bigquery-etl'
  AND r.pr_number = 8244
ORDER BY r.submitted_at
```

**Response:** "BenWu reviewed PR #8244 and approved it on Oct 9 at 22:02 UTC."

---

**Query:** "What PRs did benwu author last month?"

**Execution Plan:**
```sql
SELECT number, title, merged_at, additions, deletions
FROM github_prs.prs
WHERE repo_name = 'mozilla/bigquery-etl'
  AND author = 'BenWu'
  AND merged_at BETWEEN '2025-09-01' AND '2025-09-30'
ORDER BY merged_at DESC
```

**Response:** "BenWu authored 12 PRs last month, including..."

### 7.2 Semantic Queries

**Query:** "Find authentication-related PRs"

**Execution Plan:**
```sql
-- 1. Generate embedding for "authentication"
-- embedding = [0.123, 0.456, ...]

-- 2. Vector search
SELECT
  number,
  title,
  body,
  merged_at,
  -- Calculate similarity
  (1 - COSINE_DISTANCE(body_embedding, query_embedding)) AS similarity
FROM github_prs.prs
WHERE repo_name = 'mozilla/bigquery-etl'
  AND body_embedding IS NOT NULL
ORDER BY similarity DESC
LIMIT 10
```

**Response:** "Found 8 authentication-related PRs:
1. PR #8201: Added OIDC authentication for API
2. PR #7988: Fixed auth token expiration handling
..."

### 7.3 Hybrid Queries

**Query:** "What monitoring_derived changes happened last week?"

**Execution Plan:**
```sql
-- Step 1: Filter by directory and date
WITH filtered_prs AS (
  SELECT DISTINCT pr_number
  FROM github_prs.files
  WHERE repo_name = 'mozilla/bigquery-etl'
    AND filename LIKE 'sql/%/monitoring_derived/%'
    AND cached_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
)

-- Step 2: Get PR details with vector similarity
SELECT
  p.number,
  p.title,
  p.body,
  p.merged_at,
  p.author
FROM github_prs.prs p
JOIN filtered_prs f ON p.number = f.pr_number
WHERE p.repo_name = 'mozilla/bigquery-etl'
ORDER BY p.merged_at DESC
```

**Response:** "3 PRs touched monitoring_derived last week:
1. PR #8244: Added dataViewer access for chicory poc
2. PR #8088: Added Bigeye metric service schema
..."

### 7.4 Analytical Queries

**Query:** "What's our average PR cycle time this month?"

**Execution Plan:**
```sql
WITH pr_metrics AS (
  SELECT
    p.number,
    p.created_at,
    p.merged_at,
    TIMESTAMP_DIFF(p.merged_at, p.created_at, HOUR) AS cycle_hours,
    MIN(r.submitted_at) AS first_review_at
  FROM github_prs.prs p
  LEFT JOIN github_prs.reviews r
    ON p.repo_name = r.repo_name
    AND p.number = r.pr_number
  WHERE p.repo_name = 'mozilla/bigquery-etl'
    AND p.merged_at >= TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), MONTH)
  GROUP BY p.number, p.created_at, p.merged_at
)

SELECT
  COUNT(*) as total_prs,
  ROUND(AVG(cycle_hours), 1) as avg_cycle_hours,
  ROUND(AVG(TIMESTAMP_DIFF(first_review_at, created_at, HOUR)), 1) as avg_time_to_first_review
FROM pr_metrics
```

**Response:** "This month's PR metrics:
- 23 PRs merged
- Average cycle time: 8.4 hours
- Average time to first review: 2.1 hours"

---

## 8. Performance & Scalability

### 8.1 Expected Performance

**Query Response Times:**

| Query Type | Target | Expected |
|------------|--------|----------|
| Simple metadata | < 30 sec | < 5 sec |
| Semantic search | < 30 sec | 10-15 sec |
| Hybrid query | < 2 min | 15-30 sec |
| Digest generation | < 5 min | 2-3 min |

**Data Collection:**
- Daily job runtime: 10-15 minutes for 300 PRs/month
- Scales linearly with PR count

### 8.2 Scalability Limits

**Current Scale:**
- 75 PRs/month (current)
- 300-400 PRs/month (expected)
- 5-10 concurrent users

**System Limits:**
- BigQuery: Petabyte scale (no concern)
- Vector search: Millions of vectors (no concern)
- LLM API: Rate limits (~500 req/min)

**Bottlenecks:**
- LLM API calls (slowest part)
- Vector search on large result sets
- Embedding generation for large batches

**Mitigation:**
- Cache common queries
- Batch embedding generation
- Use streaming results for large outputs

### 8.3 Cost Projections

**Monthly Operating Costs:**

| Service | Usage | Cost |
|---------|-------|------|
| **BigQuery Storage** | ~1.5 GB (768-dim vectors) | $0.03 |
| **BigQuery Queries** | ~50 queries/day | $5-10 |
| **Cloud Run** | ~30 executions/month | $2-5 |
| **Vertex AI Embeddings** | ~1000 embeddings/day (768-dim) | $10-15 |
| **Anthropic API** | ~300 queries/month | $15-30 |
| **Total** | | **$32-60/month** |

**Well within $100/month budget**

**Cost Optimization:**
- Use query result caching (reduces BQ query costs)
- Batch embedding generation (reduces API calls)
- Implement response caching for common questions

---

## 9. Monitoring & Observability

### 9.1 Metrics to Track

**Data Collection Metrics:**
- PRs collected per run
- Embeddings generated per run
- Job duration
- Failure rate
- GitHub API rate limit remaining

**Query Metrics:**
- Queries per day
- Average response time
- Query success/failure rate
- LLM API usage and cost
- Cache hit rate

**Data Quality Metrics:**
- PRs with missing embeddings
- Failed embedding generations
- Data freshness (last collection timestamp)

### 9.2 Logging

**Structured Logging:**
```json
{
  "timestamp": "2025-10-16T12:00:00Z",
  "component": "SecondBrain",
  "action": "query",
  "user": "gkatre",
  "question": "What shipped last week?",
  "query_type": "hybrid",
  "response_time_ms": 12500,
  "llm_tokens_used": 2500,
  "bq_bytes_processed": 150000,
  "status": "success"
}
```

**Log Levels:**
- DEBUG: SQL queries, API calls
- INFO: User queries, job completions
- WARN: Slow queries, rate limit warnings
- ERROR: Failed queries, job failures

### 9.3 Alerting

**Critical Alerts:**
- Daily collection job failed
- BigQuery query error rate > 10%
- LLM API unavailable

**Warning Alerts:**
- Query response time > 2 minutes
- Cost exceeds $80/month
- Data freshness > 36 hours

**Monitoring Tools:**
- Cloud Monitoring (metrics and alerts)
- Cloud Logging (log analysis)
- BigQuery INFORMATION_SCHEMA (query stats)

---

## 10. Security & Privacy

### 10.1 Data Security

**Access Control:**
- Use IAM service accounts with least privilege
- BigQuery dataset-level permissions
- Row-level security (future: filter by repository access)

**Data Encryption:**
- BigQuery encrypts data at rest (default)
- TLS for all API calls
- Secrets in Cloud Secret Manager

**Audit Logging:**
- Log all data access (BigQuery audit logs)
- Track who queries what
- Retention: 30 days

### 10.2 Privacy Considerations

**Public Repository Data:**
- All PR content is already public
- No additional privacy concerns
- Can include in embeddings and LLM context

**Private Repository Data (Future):**
- PR content must stay in GCP (no external LLM APIs)
- Use Vertex AI for embeddings and LLM
- Additional access controls

**PII Handling:**
- GitHub usernames are public
- No email addresses or sensitive data
- Review comments may contain sensitive info → flag in future

---

## 11. Testing Strategy

### 11.1 Unit Tests

**Components to Test:**
- `EmbeddingGenerator`: Embedding generation accuracy
- `BigQueryLoader`: Data loading correctness
- `LLMQueryPlanner`: Query plan generation
- `BigQueryDataSource`: SQL generation and execution

**Test Coverage Target:** 80%+

### 11.2 Integration Tests

**End-to-End Scenarios:**
- Data collection pipeline (GitHub → BigQuery)
- Query execution (natural language → results)
- Digest generation

**Test Data:**
- Use cached PR JSON files as fixtures
- Mock GitHub API responses
- Test database with sample data

### 11.3 Performance Tests

**Load Tests:**
- Concurrent queries (5-10 users)
- Large result sets (100+ PRs)
- Digest generation under load

**Benchmarks:**
- Query response time targets
- Collection job duration
- Embedding generation throughput

---

## 12. Migration & Extensibility

### 12.1 Abstraction Layer Benefits

**Easy Migrations:**

| Migration Path | Effort | Timeline |
|----------------|--------|----------|
| BigQuery → Vertex AI Vector Search | Medium | 2-3 days |
| Claude → Gemini | Easy | 4-6 hours |
| Add Firestore (hybrid) | Easy | 1 day |
| Full Firestore migration | Hard | 1-2 weeks |

**Implementation Pattern:**
```python
# Application code
data_source = get_data_source()  # Factory pattern
brain = SecondBrain(data_source, llm_client, embeddings)

# Configuration determines implementation
if config.storage == 'bigquery':
    data_source = BigQueryDataSource(...)
elif config.storage == 'firestore':
    data_source = FirestoreDataSource(...)
elif config.storage == 'hybrid':
    data_source = HybridDataSource(...)
```

### 12.2 Future Enhancements

**Phase 2 (Month 2-3):**
- Web UI for non-technical users
- Slack bot integration
- Email digest automation
- Multi-repository support

**Phase 3 (Month 4-6):**
- Jira integration (pull ticket context)
- Deployment correlation (PRs → deploys → incidents)
- Proactive anomaly detection
- Custom dashboards

**Phase 4 (Long-term):**
- Code quality analysis
- Review quality scoring
- Automated PR categorization
- Predictive analytics (velocity forecasting)

---

## 13. Open Technical Questions

1. **Embedding Model:** Stick with textembedding-gecko or explore newer models (BGE, E5)?
2. **Vector Dimensions:** 768 (current) vs. 384 (smaller, faster) vs. 1536 (larger, more accurate)?
3. **Chunking Strategy:** How to handle very large PRs (> 10K lines changed)?
4. **Cache Strategy:** Redis for query results or rely on BigQuery result caching?
5. **Real-time Updates:** Keep daily batch or add webhook-based updates for recent PRs?
6. **Multi-tenant:** How to efficiently support multiple repositories in same dataset?

**Resolution Process:** Prototype and benchmark during MVP development

---

## 14. Success Criteria

### MVP (Week 1)
- [ ] BigQuery tables created with vector columns
- [ ] Cloud Run job deployed and scheduled
- [ ] Can collect PRs and generate embeddings
- [ ] Can execute structured queries via CLI
- [ ] Can execute semantic queries via CLI
- [ ] LLM integration works for 3+ query types

### Production (Month 1)
- [ ] All P0 queries working reliably
- [ ] Automated digest generation
- [ ] Cost < $100/month
- [ ] Query response time within targets
- [ ] 2+ managers using regularly

### Scale (Month 3)
- [ ] 5+ users active weekly
- [ ] Cost remains < $100/month
- [ ] Query accuracy > 95%
- [ ] User satisfaction > 4/5

---

## Appendix A: BigQuery DDL Scripts

```sql
-- Create dataset
CREATE SCHEMA IF NOT EXISTS `github_prs`
OPTIONS (
  description = "GitHub PR data with vector embeddings for semantic search",
  location = "US"
);

-- Create prs table
CREATE TABLE IF NOT EXISTS `github_prs.prs` (
  repo_name STRING NOT NULL OPTIONS(description="Repository name (e.g. mozilla/bigquery-etl)"),
  number INT64 NOT NULL OPTIONS(description="PR number"),
  title STRING NOT NULL OPTIONS(description="PR title"),
  body STRING OPTIONS(description="PR description/body text"),
  body_embedding ARRAY<FLOAT64> OPTIONS(description="Vector embedding of PR body (768-dim)"),
  state STRING NOT NULL OPTIONS(description="PR state: open, closed, merged"),
  author STRING NOT NULL OPTIONS(description="PR author GitHub username"),
  html_url STRING NOT NULL OPTIONS(description="GitHub URL for this PR"),
  created_at TIMESTAMP NOT NULL OPTIONS(description="When PR was created"),
  updated_at TIMESTAMP NOT NULL OPTIONS(description="When PR was last updated"),
  merged_at TIMESTAMP OPTIONS(description="When PR was merged (null if not merged)"),
  closed_at TIMESTAMP OPTIONS(description="When PR was closed"),
  base_branch STRING OPTIONS(description="Target branch"),
  head_branch STRING OPTIONS(description="Source branch"),
  additions INT64 OPTIONS(description="Lines added"),
  deletions INT64 OPTIONS(description="Lines deleted"),
  changed_files INT64 OPTIONS(description="Number of files changed"),
  draft BOOL OPTIONS(description="Whether PR is a draft"),
  cached_at TIMESTAMP NOT NULL OPTIONS(description="When data was cached")
)
PARTITION BY DATE(merged_at)
CLUSTER BY repo_name, author, merged_at
OPTIONS (
  description = "Core PR metadata with vector embeddings"
);

-- Create reviews table
CREATE TABLE IF NOT EXISTS `github_prs.reviews` (
  review_id INT64 NOT NULL OPTIONS(description="Unique review ID"),
  repo_name STRING NOT NULL OPTIONS(description="Repository name"),
  pr_number INT64 NOT NULL OPTIONS(description="PR number"),
  reviewer STRING NOT NULL OPTIONS(description="Reviewer GitHub username"),
  body STRING OPTIONS(description="Review comment text"),
  body_embedding ARRAY<FLOAT64> OPTIONS(description="Vector embedding of review body"),
  state STRING NOT NULL OPTIONS(description="Review state: APPROVED, CHANGES_REQUESTED, COMMENTED"),
  submitted_at TIMESTAMP NOT NULL OPTIONS(description="When review was submitted"),
  html_url STRING OPTIONS(description="GitHub URL for this review"),
  cached_at TIMESTAMP NOT NULL OPTIONS(description="When data was cached")
)
PARTITION BY DATE(submitted_at)
CLUSTER BY repo_name, reviewer, pr_number
OPTIONS (
  description = "PR reviews with vector embeddings"
);

-- Create files table
CREATE TABLE IF NOT EXISTS `github_prs.files` (
  id INT64 NOT NULL OPTIONS(description="Unique file change ID"),
  repo_name STRING NOT NULL OPTIONS(description="Repository name"),
  pr_number INT64 NOT NULL OPTIONS(description="PR number"),
  filename STRING NOT NULL OPTIONS(description="File path"),
  additions INT64 OPTIONS(description="Lines added in this file"),
  deletions INT64 OPTIONS(description="Lines deleted in this file"),
  status STRING OPTIONS(description="Change status: added, deleted, modified, renamed"),
  patch STRING OPTIONS(description="Code diff/patch content"),
  patch_embedding ARRAY<FLOAT64> OPTIONS(description="Vector embedding of patch"),
  patch_truncated BOOL DEFAULT FALSE OPTIONS(description="Whether patch was truncated by GitHub API"),
  cached_at TIMESTAMP NOT NULL OPTIONS(description="When data was cached")
)
CLUSTER BY repo_name, pr_number
OPTIONS (
  description = "File changes with patch embeddings"
);

-- Create labels table
CREATE TABLE IF NOT EXISTS `github_prs.labels` (
  repo_name STRING NOT NULL OPTIONS(description="Repository name"),
  pr_number INT64 NOT NULL OPTIONS(description="PR number"),
  label_name STRING NOT NULL OPTIONS(description="Label name"),
  label_color STRING OPTIONS(description="Label color hex code"),
  label_description STRING OPTIONS(description="Label description")
)
CLUSTER BY repo_name, pr_number
OPTIONS (
  description = "PR labels for categorization"
);
```

---

**Document End**

