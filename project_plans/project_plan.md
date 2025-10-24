# GitHub Delivery Visibility - Project Plan

**Version:** 1.0
**Date:** October 16, 2025
**Author:** George Kaberere
**Status:** Draft

---

## 1. Executive Summary

### 1.1 Project Overview

**Project Name:** GitHub Delivery Visibility - Second Brain System

**Duration:** 3 months (MVP in 1 week)

**Team Size:** 1 developer (George Kaberere)

**Budget:** $100/month operational cost

**Goal:** Build an LLM-powered system that provides intelligent insights about GitHub repository activity, reducing bi-weekly report time from 60 minutes to 10 minutes.

### 1.2 Success Criteria

**Week 1 (MVP):**
- Can query: "What shipped last week?" and get intelligent summary
- Can query: "Who reviewed PR #X?" and get accurate answer
- Data collection job running daily
- Cost < $50/month

**Month 1 (Production):**
- All P0 queries working
- Automated bi-weekly digest generation
- 2+ managers using regularly
- Cost < $100/month

**Month 3 (Scale):**
- 5+ users active
- Monthly organizational reports automated
- User satisfaction > 4/5
- Demonstrated 2+ hours/week time savings

---

## 2. Project Phases

### Phase 0: Setup & Planning (Days 1-2)
**Goal:** Environment setup and validation

**Duration:** 2 days

**Deliverables:**
- GCP project and permissions configured
- GitHub API access validated
- Development environment ready
- Architecture plan reviewed and approved

---

### Phase 1: MVP - Data Foundation (Days 3-7)
**Goal:** Prove data collection and basic querying works

**Duration:** 5 days

**Deliverables:**
- BigQuery schema created
- Data collection pipeline working
- Basic CLI queries functional
- LLM integration for 3 core queries

---

### Phase 2: Core Features (Weeks 2-4)
**Goal:** Production-ready system for 2-5 managers

**Duration:** 3 weeks

**Deliverables:**
- All P0 queries implemented
- Automated digest generation
- Error handling and monitoring
- Documentation

---

### Phase 3: Scale & Automation (Months 2-3)
**Goal:** Team-wide adoption and automation

**Duration:** 2 months

**Deliverables:**
- Monthly reports automated
- Team-wide access (10+ users)
- Slack/email integration
- Performance optimization

---

## 3. Detailed Phase Breakdown

## Phase 0: Setup & Planning ✅ COMPLETED

**Status:** Complete (Oct 20, 2025)

**Completed Tasks:**

**T0.1: GCP Project Configuration** ✅
- [x] Verified access to `mozdata-nonprod` project
- [x] Using existing `analysis` dataset
- [x] Tested BigQuery table creation permissions

**T0.2: Development Environment** ✅
- [x] Set up Python 3.12 virtual environment (`venv/`)
- [x] Installed dependencies:
  - `google-cloud-bigquery>=3.11.0`
  - `google-cloud-aiplatform>=1.38.0`
  - `anthropic>=0.7.0`
- [x] GitHub API connection validated

**T0.3: BigQuery Schema Creation** ✅
- [x] Created YAML schema definitions for all 4 tables
- [x] Built schema creation script (`create_schema.py`)
- [x] Created tables:
  - `gkabbz_gh_prs` (19 columns, partitioned by `merged_at`)
  - `gkabbz_gh_reviews` (10 columns, partitioned by `submitted_at`)
  - `gkabbz_gh_files` (11 columns, clustered)
  - `gkabbz_gh_labels` (5 columns, clustered)
- [x] Verified partitioning and clustering applied
- [x] Documented schemas in `src/github_delivery/schemas/`

**Deliverables:**
- ✅ BigQuery tables with vector embedding support
- ✅ Clean YAML schema definitions
- ✅ Development environment ready
- ✅ Dependencies installed

**Deferred to Later:**
- Service accounts (will use personal credentials for development)
- Secret Manager (will use local `.env` file)
- Cloud Run deployment (Phase 2)

---

## Phase 1: MVP - Data Foundation (Days 3-7)

### Day 3-4: Embedding & Loading ✅ COMPLETED

**T1.1: Build EmbeddingGenerator Component** ✅
- [x] Created `src/github_delivery/embeddings.py`
- [x] Implemented `EmbeddingGenerator` class using text-embedding-004
- [x] Integrated Vertex AI with mozdata project
- [x] Added batch embedding support (configurable batch size)
- [x] Added error handling for empty texts
- [x] Tested with real PR data

**Owner:** George
**Status:** Complete
**Success Criteria:** ✅ Can generate 768-dim embeddings for sample text

---

**T1.2: Build BigQueryLoader Component** ✅
- [x] Created `src/github_delivery/bigquery_loader.py`
- [x] Implemented `BigQueryLoader` class
- [x] Added methods for loading all tables with embeddings:
  - PRs with body embeddings
  - Reviews with body embeddings
  - Files with patch embeddings
  - Labels (no embeddings)
- [x] Tested with real mozilla/bigquery-etl PRs from cache
- [x] **Enhanced (Oct 23):** Added idempotent loading with duplicate detection
- [x] **Enhanced (Oct 23):** Added batch inserts to handle BigQuery request size limits

**Owner:** George
**Status:** Complete
**Success Criteria:** ✅ Can load PR data to BigQuery tables with embeddings (idempotent, resilient)

---

**T1.3: DataPipeline Orchestrator** ⚠️ DEFERRED TO PHASE 2

**Reason for deferral:** Will use Airflow for orchestration in production. The existing components (GitHubCollector, EmbeddingGenerator, BigQueryLoader) are already composable and can be called directly from Airflow tasks.

**Phase 2 Airflow approach:**
- Task 1: `collect_prs()` → Uses existing GitHubCollector
- Task 2: `load_to_bigquery()` → Uses EmbeddingGenerator + BigQueryLoader
- Airflow handles: scheduling, retries, logging, monitoring

**Decision:** Skip building a separate DataPipeline class. Move directly to Data Access Layer.

---

### Day 5: Data Access Layer ✅ COMPLETED

**T1.5: Build Abstract PRDataSource Interface** ✅
- [x] Create `src/github_delivery/data_source.py`
- [x] Define `PRDataSource` abstract class with methods:
  - `find_prs_by_author()`
  - `find_prs_by_reviewer()`
  - `find_prs_by_date_range()`
  - `find_prs_by_file()`
  - `find_prs_by_directory()`
  - `semantic_search()`
  - `get_pr_detail()`
- [x] Document interface with docstrings

**Owner:** George
**Status:** Complete
**Success Criteria:** ✅ Abstract interface defined and documented

---

**T1.6: Implement BigQueryDataSource** ✅
- [x] Create `src/github_delivery/bq_data_source.py`
- [x] Implement `BigQueryDataSource` class
- [x] Implement structured queries:
  - `find_prs_by_author()` → SQL query
  - `find_prs_by_reviewer()` → SQL with JOIN
  - `find_prs_by_date_range()` → SQL with date filter
  - `find_prs_by_file()` → SQL with file lookup
  - `find_prs_by_directory()` → SQL with LIKE pattern
- [x] Implement semantic search:
  - Generate query embedding
  - Use COSINE_DISTANCE with threshold
  - Return top N results
- [x] Add result transformation (BigQuery Row → PullRequest object)
- [x] Write integration tests

**Owner:** George
**Status:** Complete
**Success Criteria:** ✅ Can query BigQuery for PRs using Python interface

---

### Day 6: LLM Integration ✅ COMPLETED

**T1.7: Build LLMClient** ✅
- [x] Create `src/github_delivery/llm_client.py`
- [x] Define `LLMClient` abstract interface
- [x] Implement `AnthropicLLMClient` class
- [x] Add retry logic and error handling
- [x] Add token counting and cost tracking
- [x] Write unit tests with mocked API

**Owner:** George
**Status:** Complete
**Success Criteria:** ✅ Can call Claude API reliably

---

**T1.8: Build QueryPlanner** ✅
- [x] Create `src/github_delivery/query_planner.py`
- [x] Implement `QueryPlanner` class
- [x] Create prompt template for query planning
- [x] Parse LLM response into structured `QueryPlan`
- [x] Handle 3 query types:
  - Structured (metadata only)
  - Semantic (vector search)
  - Hybrid (both)
- [x] Test with sample questions

**Owner:** George
**Status:** Complete
**Success Criteria:** ✅ Can translate natural language to query plans

---

### Day 7: MVP Assembly & Testing ✅ COMPLETED

**T1.9: Build GitHubOracle Application** ✅
- [x] Create `src/github_delivery/github_oracle.py`
- [x] Implement `GitHubOracle` class (renamed from SecondBrain)
- [x] Wire together components:
  - DataSource
  - LLMClient
  - QueryPlanner
  - EmbeddingGenerator
- [x] Implement `ask()` method:
  - Plan query
  - Execute via DataSource
  - Synthesize answer with LLM
- [x] Test with multiple questions across all query types

**Owner:** George
**Status:** Complete
**Success Criteria:** ✅ Can answer questions end-to-end

---

**T1.10: Build MVP CLI** ✅
- [x] Create `src/github_delivery/cli.py`
- [x] Add command: `ghoracle ask "<question>"`
- [x] Add `--verbose` flag for debugging
- [x] Add `--repo` flag for repository selection
- [x] Add basic output formatting
- [x] Create convenience script: `ghoracle`
- [x] Test interactively with various queries

**Owner:** George
**Status:** Complete
**Success Criteria:** ✅ CLI works for basic queries

---

**T1.11: MVP Testing & Documentation** ✅
- [x] Run end-to-end test:
  - Created backfill script for loading historical data
  - Load PRs to BigQuery with embeddings
  - Query with CLI
- [x] Document MVP usage in README
- [x] Add comprehensive backfill documentation
- [x] Create test scripts for all components
- [x] Verified costs within budget

**Owner:** George
**Status:** Complete
**Success Criteria:** ✅ MVP works end-to-end, documented

---

**Phase 1 Milestone: MVP Complete ✅**
- [x] Can collect PRs and generate embeddings
- [x] Data loads to BigQuery successfully (idempotent, resilient)
- [x] Can ask questions via CLI (structured, semantic, hybrid queries)
- [x] Costs within budget
- [x] Comprehensive documentation and test scripts
- [x] Ready for production use

**Completion Date:** October 23, 2025

**Additional Achievements:**
- Idempotent backfill script with duplicate detection
- Batch insert handling for large datasets
- 7 query types implemented (exceeded initial goal of 3)
- Created `ghoracle` convenience command
- Built comprehensive test suite

---

## Phase 2: Core Features (Weeks 2-4)

### Week 2: Query Completeness

**T2.1: Create User Lookup Table**
- [ ] Design schema for `github_users` table:
  - `github_login` (primary key, e.g., "gkabbz")
  - `display_name` (e.g., "George Kaberere")
  - `aliases` (array of common name variations)
  - `email` (optional)
- [ ] Update `schemas/users.yaml`
- [ ] Create table in BigQuery
- [ ] Populate initial user data from existing PRs
- [ ] Update `BigQueryDataSource.find_prs_by_author()` to support name lookup
- [ ] Add `resolve_user_name()` helper method
- [ ] Test queries with both GitHub logins and display names

**Owner:** George
**Time Estimate:** 3 hours
**Dependencies:** Phase 1 complete
**Success Criteria:** Can query "George's PRs" and it resolves to "gkabbz"

**Motivation:** Users will naturally ask about people by their real names (e.g., "What did George ship?") rather than GitHub handles (e.g., "What did gkabbz ship?"). This lookup table enables natural language queries.

---

**T2.2: Implement All P0 Queries**
- [ ] PR Investigation queries:
  - "Who reviewed PR #X?"
  - "How long did PR #X take to merge?"
  - "How many change requests on PR #X?"
- [ ] File/Directory queries:
  - "What changed in [directory]?"
  - "What's the history of [file]?"
- [ ] Semantic queries:
  - "Find authentication-related PRs"
  - "What monitoring changes happened?"
- [ ] Test each query type
- [ ] Document query patterns

**Owner:** George
**Time Estimate:** 8 hours
**Dependencies:** T2.1
**Success Criteria:** All P0 queries from business requirements work

---

**T2.3: Build InsightSynthesizer**
- [ ] Create `src/github_delivery/llm_synthesizer.py`
- [ ] Implement `InsightSynthesizer` class
- [ ] Create prompt templates for:
  - Simple Q&A
  - Weekly digest
  - Analysis with insights
- [ ] Add insight extraction logic:
  - Parse table names from SQL diffs
  - Extract bug impact from PR descriptions
  - Identify patterns across PRs
- [ ] Test with sample data

**Owner:** George
**Time Estimate:** 6 hours
**Dependencies:** T2.1
**Success Criteria:** Answers include insights, not just raw data

---

**T2.3: Implement Digest Generation**
- [ ] Add `generate_weekly_digest()` to SecondBrain
- [ ] Create digest prompt template
- [ ] Implement logic to:
  - Fetch PRs from last week
  - Categorize by type (features, bugs, maintenance)
  - Extract key changes
  - Generate formatted summary
- [ ] Test with multiple weeks of data
- [ ] Add CLI command: `github-delivery digest weekly`

**Owner:** George
**Time Estimate:** 6 hours
**Dependencies:** T2.2
**Success Criteria:** Can generate weekly digest automatically

---

### Week 3: Production Readiness

**T2.4: Error Handling & Resilience**
- [ ] Add comprehensive error handling:
  - GitHub API failures
  - BigQuery errors
  - LLM API timeouts
  - Embedding generation failures
- [ ] Implement retry logic with exponential backoff
- [ ] Add graceful degradation (fallback responses)
- [ ] Test error scenarios
- [ ] Log errors with context

**Owner:** George
**Time Estimate:** 6 hours
**Dependencies:** T2.3
**Success Criteria:** System handles failures gracefully

---

**T2.5: Monitoring & Observability**
- [ ] Implement structured logging
- [ ] Add metrics tracking:
  - Query response times
  - LLM token usage
  - BigQuery bytes processed
  - Error rates
- [ ] Set up Cloud Monitoring dashboards
- [ ] Create alerts:
  - Collection job failures
  - High error rates
  - Cost exceeds threshold
- [ ] Test alerting

**Owner:** George
**Time Estimate:** 4 hours
**Dependencies:** T2.4
**Success Criteria:** Can monitor system health and costs

---

**T2.6: Cloud Run Deployment**
- [ ] Create Dockerfile for collector job
- [ ] Build container image
- [ ] Deploy to Cloud Run:
  - Configure service account
  - Mount secrets
  - Set memory/CPU limits
  - Set timeout to 30 minutes
- [ ] Test manual execution
- [ ] Configure Cloud Scheduler:
  - Daily trigger @ 2am UTC
  - Retry on failure
- [ ] Test scheduled execution

**Owner:** George
**Time Estimate:** 4 hours
**Dependencies:** T2.5
**Success Criteria:** Daily collection runs automatically

---

### Week 4: Documentation & Launch

**T2.7: User Documentation**
- [ ] Write user guide:
  - How to ask questions
  - Query patterns and examples
  - Interpreting results
  - Troubleshooting
- [ ] Create video walkthrough (5 min)
- [ ] Document CLI commands
- [ ] Add FAQ section

**Owner:** George
**Time Estimate:** 4 hours
**Dependencies:** T2.6
**Success Criteria:** Users can self-serve

---

**T2.8: Developer Documentation**
- [ ] Document architecture
- [ ] Code documentation (docstrings)
- [ ] Deployment guide
- [ ] Contribution guidelines
- [ ] API reference

**Owner:** George
**Time Estimate:** 3 hours
**Dependencies:** T2.7
**Success Criteria:** Future developers can understand and extend

---

**T2.9: User Onboarding**
- [ ] Onboard first 2 engineering managers
- [ ] Provide training session
- [ ] Collect initial feedback
- [ ] Create feedback mechanism (GitHub issues)
- [ ] Iterate based on feedback

**Owner:** George
**Time Estimate:** 4 hours
**Dependencies:** T2.7
**Success Criteria:** 2+ managers using regularly

---

**T2.10: Performance Optimization**
- [ ] Profile query performance
- [ ] Optimize slow queries
- [ ] Implement response caching (if needed)
- [ ] Optimize BigQuery query costs
- [ ] Test with large result sets

**Owner:** George
**Time Estimate:** 4 hours
**Dependencies:** T2.9
**Success Criteria:** Query times within targets

---

**Phase 2 Milestone: Production Launch ✅**
- [ ] All P0 queries working reliably
- [ ] Automated digest generation
- [ ] Daily collection job running
- [ ] Monitoring and alerts active
- [ ] 2+ managers using regularly
- [ ] Documentation complete
- [ ] Cost < $100/month

---

## Phase 3: Scale & Automation (Months 2-3)

### Month 2: Expanded Features

**T3.1: Monthly Report Generation**
- [ ] Design monthly report format
- [ ] Implement `generate_monthly_report()`
- [ ] Add analysis:
  - Month-over-month trends
  - Top contributors
  - Focus areas
  - Velocity metrics
- [ ] Format for organizational sharing
- [ ] Test with historical data
- [ ] Add CLI command: `github-delivery digest monthly`

**Owner:** George
**Time Estimate:** 8 hours
**Dependencies:** Phase 2 complete
**Success Criteria:** Can generate monthly report automatically

---

**T3.2: Contributor Analytics**
- [ ] Implement contributor-specific queries:
  - PRs authored by person
  - Review activity
  - PR size patterns
  - Turnaround times
- [ ] Add comparative analytics
- [ ] Create contributor profile view
- [ ] Test with multiple contributors

**Owner:** George
**Time Estimate:** 6 hours
**Dependencies:** T3.1
**Success Criteria:** Can analyze individual contributor patterns

---

**T3.3: Trend Analysis**
- [ ] Implement time-series queries:
  - Velocity over time
  - Review time trends
  - Change type distribution
- [ ] Add pattern detection
- [ ] Create visualization data (JSON for charting)
- [ ] Test with 3+ months of data

**Owner:** George
**Time Estimate:** 6 hours
**Dependencies:** T3.2
**Success Criteria:** Can identify trends over time

---

**T3.4: Query Optimization & Caching**
- [ ] Implement query result caching
- [ ] Cache common questions
- [ ] Add cache invalidation logic
- [ ] Measure cache hit rates
- [ ] Optimize for cost reduction

**Owner:** George
**Time Estimate:** 4 hours
**Dependencies:** T3.3
**Success Criteria:** 30%+ cache hit rate, reduced costs

---

### Month 3: Integration & Scale

**T3.5: Slack Integration**
- [ ] Create Slack bot
- [ ] Implement slash commands:
  - `/pr-digest weekly`
  - `/pr-ask <question>`
- [ ] Format responses for Slack
- [ ] Handle threaded conversations
- [ ] Deploy to Slack workspace
- [ ] Test with users

**Owner:** George
**Time Estimate:** 8 hours
**Dependencies:** T3.4
**Success Criteria:** Can query from Slack

---

**T3.6: Email Digest Automation**
- [ ] Set up email service (SendGrid or similar)
- [ ] Create email templates
- [ ] Implement scheduled digest delivery
- [ ] Add user preferences (frequency, format)
- [ ] Test email delivery
- [ ] Allow users to subscribe

**Owner:** George
**Time Estimate:** 6 hours
**Dependencies:** T3.5
**Success Criteria:** Automated emails sent reliably

---

**T3.7: Multi-Repository Support**
- [ ] Update schema to support multiple repos
- [ ] Modify collection pipeline for multiple repos
- [ ] Add repo selection to queries
- [ ] Test with 2+ repositories
- [ ] Update documentation

**Owner:** George
**Time Estimate:** 8 hours
**Dependencies:** T3.6
**Success Criteria:** Can query across multiple repositories

---

**T3.8: Team-Wide Rollout**
- [ ] Onboard remaining managers (3-5 total)
- [ ] Onboard team members (10+ total)
- [ ] Collect feedback
- [ ] Iterate on UX
- [ ] Measure adoption rates

**Owner:** George
**Time Estimate:** 4 hours (spread over weeks)
**Dependencies:** T3.7
**Success Criteria:** 10+ active users

---

**Phase 3 Milestone: Scale Complete ✅**
- [ ] Monthly reports automated
- [ ] 10+ active users
- [ ] Slack/email integration working
- [ ] Multi-repo support (if needed)
- [ ] User satisfaction > 4/5
- [ ] Time savings demonstrated

---

## 4. Timeline & Milestones

### Gantt Chart View

```
Week 1 (Oct 16-22):  [Phase 0: Setup][Phase 1: MVP Development        ]
Week 2 (Oct 23-29):  [Phase 2: Core Features - Query Completeness     ]
Week 3 (Oct 30-Nov5):[Phase 2: Core Features - Production Readiness   ]
Week 4 (Nov 6-12):   [Phase 2: Core Features - Documentation & Launch ]
Week 5-8 (Nov-Dec):  [Phase 3: Scale - Expanded Features              ]
Week 9-12 (Dec-Jan): [Phase 3: Scale - Integration & Rollout          ]
```

### Key Milestones

| Milestone | Date | Deliverables |
|-----------|------|-------------|
| **M1: MVP Complete** | Oct 22 | CLI working, 3 core queries, daily collection |
| **M2: Production Launch** | Nov 12 | All P0 queries, 2+ managers using, automated digests |
| **M3: Scale Complete** | Jan 15 | 10+ users, Slack integration, monthly reports |

---

## 5. Resource Requirements

### 5.1 Human Resources

**Developer:** George Kaberere (Full-time for Phase 1-2, Part-time for Phase 3)

**Phase 1 (Week 1):** 40 hours (full-time)
**Phase 2 (Weeks 2-4):** 60 hours (20 hours/week)
**Phase 3 (Months 2-3):** 40 hours (5 hours/week)

**Total Development Time:** 140 hours

### 5.2 Infrastructure Costs

**Development (Months 1-3):**
- BigQuery: $5-10/month
- Vertex AI Embeddings: $10-15/month
- Anthropic API: $15-30/month
- Cloud Run: $2-5/month
- **Total:** $32-60/month

**Production (Ongoing):**
- Same as above, may increase slightly with usage
- Budget: $100/month (comfortable headroom)

### 5.3 Third-Party Services

**Required:**
- Google Cloud Platform account
- GitHub account with API access
- Anthropic API account

**Optional (Phase 3):**
- Slack workspace access
- SendGrid account (or similar for email)

---

## 6. Risk Management

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **BigQuery vector search performance insufficient** | Low | Medium | Design allows migration to Vertex AI Vector Search |
| **LLM query quality poor** | Medium | High | Extensive prompt engineering, can switch providers |
| **Cost overruns** | Low | Medium | Implement caching, monitor costs daily |
| **Low user adoption** | Medium | High | Early user involvement, focus on time savings |
| **Data collection failures** | Low | Medium | Robust retry logic, monitoring alerts |
| **GitHub API rate limits** | Low | Low | Batch requests, respect rate limits |
| **Developer bandwidth** | Medium | Medium | Prioritize MVP, defer nice-to-haves |

### Risk Response Plans

**If BigQuery vector search is slow:**
- Phase 1: Accept slower responses (< 2 min OK for MVP)
- Phase 2: Optimize queries, add indexing
- Phase 3: Migrate to Vertex AI Vector Search (2-3 days effort)

**If LLM quality is poor:**
- Iterate on prompts (80% of quality issues)
- Add examples to prompts (few-shot learning)
- Switch to Claude Opus if needed (higher quality, higher cost)
- Last resort: Switch to manual SQL generation

**If costs exceed budget:**
- Implement aggressive caching (30-50% reduction)
- Reduce embedding frequency (weekly instead of daily)
- Switch from Claude to Gemini (75% cost reduction)
- Reduce query complexity

**If users don't adopt:**
- Conduct user interviews to understand barriers
- Simplify UX (reduce friction)
- Demonstrate time savings with metrics
- Provide more training/support

---

## 7. Quality Assurance

### 7.1 Testing Strategy

**Unit Tests:**
- Target: 70%+ code coverage
- Focus on business logic components
- Mock external APIs

**Integration Tests:**
- End-to-end data pipeline
- Query execution flow
- LLM integration

**User Acceptance Testing:**
- Test with 2 managers during Phase 2
- Collect feedback and iterate
- Validate time savings

### 7.2 Code Quality

**Standards:**
- Python type hints throughout
- Docstrings for all public methods
- Follow PEP 8 style guide
- Use Black for formatting
- Use mypy for type checking

**Code Review:**
- Self-review with checklist
- Periodic review with peers (if available)

### 7.3 Performance Testing

**Benchmarks:**
- Query response times (track against targets)
- Collection job duration
- Memory usage
- Cost per query

**Load Testing:**
- Test with 100+ PRs
- Test concurrent queries (5 users)
- Test large result sets

---

## 8. Success Metrics & KPIs

### 8.1 Development Metrics

**Phase 1 (Week 1):**
- [ ] All MVP tasks completed
- [ ] 0 critical bugs
- [ ] Costs < $20 for the week

**Phase 2 (Month 1):**
- [ ] All P0 queries implemented
- [ ] Query success rate > 95%
- [ ] Average response time < 30 seconds
- [ ] Costs < $100/month

**Phase 3 (Month 3):**
- [ ] All features complete
- [ ] 70%+ code coverage
- [ ] 0 open critical bugs

### 8.2 Business Metrics

**Usage:**
- Week 2: 1+ active user
- Week 4: 2+ active users
- Month 3: 5+ active users
- Target: 10+ users by end of Phase 3

**Efficiency:**
- Bi-weekly report time: 60 min → 10 min (target)
- Measure: User survey after 4 weeks

**Quality:**
- Answer accuracy: 95%+ (spot-check against GitHub)
- User satisfaction: 4/5+ average rating
- Measure: Quarterly survey

**Cost:**
- Week 1: < $20
- Month 1: < $60
- Month 3: < $100

---

## 9. Communication Plan

### 9.1 Stakeholder Updates

**Weekly (During Phase 1-2):**
- Progress update
- Blockers and risks
- Demo of new functionality

**Bi-weekly (During Phase 3):**
- Usage metrics
- User feedback summary
- Upcoming features

### 9.2 User Communication

**Launch Announcement:**
- When: End of Week 4 (Phase 2 complete)
- Format: Email + Slack message
- Include: Demo video, quick start guide

**Feature Announcements:**
- When: New features released
- Format: Release notes in Slack/email

**Feedback Collection:**
- Ongoing: GitHub issues for bugs/features
- Monthly: User satisfaction survey

---

## 10. Dependencies & Assumptions

### 10.1 External Dependencies

**Critical Path:**
- GCP project access (Day 1)
- GitHub API access (Day 1)
- Anthropic API key (Day 6)

**Non-blocking:**
- Slack workspace access (Month 3)
- Email service account (Month 3)

### 10.2 Assumptions

**Technical:**
- BigQuery vector search is performant enough
- Vertex AI embedding quality is sufficient
- Claude API remains available and affordable
- GitHub API rate limits don't block collection

**Organizational:**
- Users have BigQuery access
- Users comfortable with CLI (initially)
- GitHub PR data volume remains < 500/month
- Budget approved for $100/month

**User Behavior:**
- Managers willing to adopt new tool
- Natural language queries are intuitive
- Time savings are sufficient motivation

---

## 11. Post-Launch Plan

### Month 4+: Maintenance & Iteration

**Ongoing Activities:**
- Monitor system health and costs
- Respond to user feedback
- Fix bugs as reported
- Optimize performance

**Potential Enhancements:**
- Web UI for non-technical users
- Jira integration (pull ticket context)
- Deployment correlation (PRs → deploys → incidents)
- Custom dashboards
- Advanced analytics (velocity forecasting)

**Review Cycle:**
- Monthly: Review metrics and user satisfaction
- Quarterly: Assess ROI and plan next phase
- Annually: Major feature planning

---

## 12. Appendices

### Appendix A: Task Checklist

**Phase 0: Setup (Days 1-2)** ✅ COMPLETE
- [x] T0.1: GCP Project Configuration
- [x] T0.2: Development Environment
- [x] T0.3: Create BigQuery Tables

**Phase 1: MVP (Days 3-7)** ✅ COMPLETE
- [x] T1.1: Build EmbeddingGenerator
- [x] T1.2: Build BigQueryLoader (enhanced with idempotency & batching)
- [x] T1.3: Build DataPipeline (deferred - using Airflow in Phase 2)
- [x] T1.5: Build Abstract PRDataSource
- [x] T1.6: Implement BigQueryDataSource
- [x] T1.7: Build LLMClient
- [x] T1.8: Build QueryPlanner
- [x] T1.9: Build GitHubOracle (formerly SecondBrain)
- [x] T1.10: Build MVP CLI
- [x] T1.11: MVP Testing & Documentation

**Phase 2: Core Features (Weeks 2-4)**
- [ ] T2.1: Implement All P0 Queries
- [ ] T2.2: Build InsightSynthesizer
- [ ] T2.3: Implement Digest Generation
- [ ] T2.4: Error Handling & Resilience
- [ ] T2.5: Monitoring & Observability
- [ ] T2.6: Cloud Run Deployment
- [ ] T2.7: User Documentation
- [ ] T2.8: Developer Documentation
- [ ] T2.9: User Onboarding
- [ ] T2.10: Performance Optimization

**Phase 3: Scale (Months 2-3)**
- [ ] T3.1: Monthly Report Generation
- [ ] T3.2: Contributor Analytics
- [ ] T3.3: Trend Analysis
- [ ] T3.4: Query Optimization & Caching
- [ ] T3.5: Slack Integration
- [ ] T3.6: Email Digest Automation
- [ ] T3.7: Multi-Repository Support
- [ ] T3.8: Team-Wide Rollout

---

### Appendix B: Definition of Done

**For Each Task:**
- [ ] Code written and tested
- [ ] Unit tests passing (where applicable)
- [ ] Docstrings added
- [ ] Committed to git with clear message
- [ ] Manual testing completed
- [ ] No critical bugs

**For Each Phase:**
- [ ] All tasks completed
- [ ] Milestone deliverables met
- [ ] Demo prepared
- [ ] Documentation updated
- [ ] Stakeholder approval received

---

### Appendix C: Tools & Technologies

**Development:**
- Python 3.11+
- VS Code or PyCharm
- Git + GitHub

**Testing:**
- pytest (unit tests)
- pytest-mock (mocking)
- mypy (type checking)

**Infrastructure:**
- Google Cloud Platform
  - BigQuery
  - Cloud Run
  - Cloud Scheduler
  - Cloud Secret Manager
  - Cloud Monitoring
  - Vertex AI (embeddings)

**APIs:**
- GitHub REST API
- Anthropic Claude API
- Vertex AI API

**Libraries:**
- google-cloud-bigquery
- google-cloud-aiplatform
- anthropic
- requests (GitHub API)
- click (CLI)
- pydantic (data validation)

---

**Document End**

---

## Approval

| Name | Role | Approval | Date |
|------|------|----------|------|
| George Kaberere | Developer/EM | [ ] | |
| [Stakeholder] | Sponsor | [ ] | |

---

**Next Steps:**
1. Review and approve project plan
2. Begin Phase 0: Setup
3. Track progress against milestones
4. Adjust plan as needed based on learnings
