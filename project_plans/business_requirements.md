# GitHub Delivery Visibility - Business Requirements Document

**Version:** 1.0
**Date:** October 16, 2025
**Author:** George Kaberere
**Status:** Draft

---

## 1. Executive Summary

### 1.1 Purpose
Build a system that provides intelligent insights about GitHub repository activity. The system will enable engineering managers to quickly understand team delivery, generate reports, and answer leadership questions without manual PR review or requiring the team to send updates.

### 1.2 Problem Statement
Engineering managers currently spend time:
- Manually reviewing PRs to understand what shipped
- Aggregating data for bi-weekly/monthly reports
- Aggregating inputs from Jira tickets, engineer updates for bi-weekly / monthly reports
- Investigating review bottlenecks and process issues
- Answering ad-hoc questions about team activity

**Time Cost:** 60-90 minutes per bi-weekly report, multiple hours for monthly organizational updates

- Currently not proactive about reporting what has been shipped for the organization leading to a black box feeling of data engineering outputs.

### 1.3 Proposed Solution
A natural language query system that:
- Answers questions about GitHub activity in plain English
- Extracts insights from PR data automatically
- Generates bi-weekly/monthly reports with minimal manual effort
- Provides deep context about specific PRs and review processes

**Key Innovation:** Don't just return data - extract intelligence and generate actionable insights.

### 1.4 Success Definition
- **Time Savings:** Reduce bi-weekly report time from 60 min → 10 min
- **Adoption:** 80%+ of engineering managers use regularly
- **Satisfaction:** "This saves me 2+ hours every week"
- **Visibility:** Organization has better understanding of team impact through monthly digest

---

## 2. Business Context

### 2.1 Target Users

**Primary Users: Engineering Managers (2-5 people)**
- Need executive summaries for leadership
- Track team velocity and delivery patterns
- Generate organizational visibility reports
- Investigate process bottlenecks
- Answer leadership questions quickly

**Secondary Users: Team Members (12+ people)**
- Track personal contributions
- Understand team focus areas
- Prepare for performance reviews
- Collaborate more effectively

### 2.2 Current State

**How Managers Work Today:**
1. Not currently using the PR information in a regular way
2. Click through each PR to read description, review comments, code changes
3. Take notes on key changes and themes
4. Categorize work types (features, bugs, maintenance)
5. Ask ICs to provide an update of what they've shipped in past two weeks.
6. Review done Jira tickets
7. Write summary in email/document format
8. Send to leadership or organization

**Pain Points:**
- Time-consuming (60-90 min per bi-weekly report)
- Context switching breaks focus
- Involves too many people
- Easy to miss important details
- Hard to identify patterns across multiple PRs
- Manual categorization is subjective
- Difficult to answer historical questions ("What changed in Q3?")
- Not data driven 

### 2.3 Desired Future State

**How Managers Will Work:**
1. Ask: "What shipped last week?"
2. Receive formatted summary with:
   - Key features and their impact
   - Bugs fixed with context
   - Emerging themes
   - Velocity metrics
   - Or other relevant information
3. Forward to leadership or edit as needed

**For Ad-hoc Questions:**
- "Who reviewed PR #8244?" → Instant answer
- "What authentication work happened this month?" → Contextual summary
- "Why are PRs taking longer to merge?" → Analysis with insights

**Benefits:**
- 90% time reduction for routine reports
- Faster answers to leadership questions
- Better visibility into team patterns
- Data-driven process improvements

---

## 3. Business Requirements

### 3.1 Core Capabilities (Must Have)

#### BR-1: Natural Language Query Interface
**Requirement:** Users must be able to ask questions in plain English without SQL or technical knowledge.

**Examples:**
- "What shipped last week?"
- "Who reviewed PR #8244?"
- "What changed in the monitoring_derived directory?"
- "Why did PR #8199 take so long to merge?"

**Business Value:** Removes technical barrier, enables quick answers without context switching

#### BR-2: Automated bi-weekly Digest
**Requirement:** System automatically generates bi-weekly summary of shipped work every Monday morning.

**Output Includes (where relevant):**
- List of merged PRs with high-level categorization
- Key features created (with specific names extracted from code)
- Bugs fixed (with impact and reason)
- Emerging themes and patterns
- Team velocity metrics (PR count, size, review time)
- Format suitable for engineering manager to have a good view of what has happened
- Engineering manager will then summarize from there to generate the leadership update

**Business Value:** Eliminates 30+ minutes of manual work per week per manager

#### BR-3: PR Investigation Capabilities
**Requirement:** Users can investigate specific PRs to understand review process and outcomes.

**Must Answer:**
- Who reviewed this PR?
- How long did the review process take?
- How many change requests were made?
- What was the nature of the feedback?
- Could issues have been prevented?

**Business Value:** Enables process improvement and mentoring opportunities

#### BR-4: Codebase Activity Tracking
**Requirement:** Users can understand what areas of codebase are changing and why.

**Must Support:**
- What PRs touched [specific directory or file]?
- What's the change history of [component]?
- When was [area] last modified?

**Business Value:** Understand team focus, identify hot spots, track technical debt

#### BR-5: Semantic Search
**Requirement:** Users can find PRs by topic/theme, not just metadata.

**Examples:**
- "Find all authentication-related PRs"
- "What monitoring improvements happened?"
- "Show me performance optimization work"

**Business Value:** Find related work even when naming/labeling is inconsistent

#### BR-6: Insight Extraction
**Requirement:** System must extract actionable insights, not just return raw data.

**Examples of Insight Extraction:**
- From code diffs → "Created 5 new tables: users_v2, events_v3..."
- From PR descriptions → "Fixed bug causing $X revenue misreporting"
- From patterns → "60% of delayed PRs touched auth code - consider earlier security review"

**Business Value:** Transform data into actionable intelligence

### 3.2 Important Capabilities (Should Have)

#### BR-7: Monthly Organizational Reports
**Requirement:** Generate monthly summary suitable for sharing across organization.

**Output Must Include:**
- Executive summary (2-3 paragraphs)
- Key accomplishments with business impact
- Metrics: velocity trends, focus areas
- Distribution of work types
- Ready-to-send format with minimal editing

**Business Value:** Increase organizational visibility, demonstrate team impact

#### BR-8: Contributor Analytics
**Requirement:** Track individual and team contribution patterns.

**Must Support:**
- What did [person] work on in [timeframe]?
- What's [person]'s typical PR size and review turnaround?
- Review participation metrics

**Business Value:** Support performance reviews, identify workload imbalances, recognize contributions

#### BR-9: Review Process Analytics
**Requirement:** Provide insights into review efficiency and bottlenecks.

**Must Track:**
- Average time to first review
- Average total review cycle time
- Number of changes requested per PR
- Change requests by reviewer
- Number of review rounds per PR
- Review request patterns

**Business Value:** Identify process bottlenecks, improve team efficiency

#### BR-10: Trend Analysis
**Requirement:** Identify patterns over time.

**Must Support:**
- Is velocity increasing or decreasing?
- What are common themes in recent work?
- What types of changes are most frequent?
- Are certain areas getting more attention?

**Business Value:** Strategic planning, proactive issue identification

### 3.3 Nice to Have (Future Enhancements)

#### BR-11: Proactive Alerts
**Requirement:** System flags unusual patterns without being asked.

**Examples:**
- "Review times doubled this week"
- "Unusual spike in monitoring_derived changes"
- "3 PRs had 5+ change requests"

**Business Value:** Catch issues early, maintain quality

#### BR-12: Multi-Repository Support
**Requirement:** Support queries across multiple repositories.

**Business Value:** Managers often oversee multiple projects

#### BR-13: Integration with External Tools
**Requirement:** Pull context from Jira, deployment systems, incident management.

**Business Value:** Complete picture of delivery and impact

---

## 4. User Stories

### Story 1: bi-weekly Executive Update
**As an** engineering manager
**I want** an automated summary of what shipped last week
**So that** I can quickly brief my VP and SVP without spending 90+ minutes on manual review

**Acceptance Criteria:**
- Receives summary every Monday morning
- Takes < 10 minutes to review and forward
- Includes key features, bugs, themes, and metrics
- Format suitable for me to have a good understanding of what shipped and then use this as an input for summarizing for leadership

**Priority:** P0 (Must Have)

### Story 2: Leadership Question Response
**As an** engineering manager
**I want** to quickly answer "What's the status of [project]?" in meetings
**So that** I don't have to say "Let me get back to you" and manually research later

**Acceptance Criteria:**
- Can get answer in < 30 seconds during meeting
- Answer includes context and current state
- Can share answer immediately

**Priority:** P0 (Must Have)

### Story 3: Process Improvement Investigation
**As an** engineering manager
**I want** to understand why certain PRs take longer to merge
**So that** I can identify and fix process bottlenecks

**Acceptance Criteria:**
- Can query: "Why did PR #X take so long?"
- Returns timeline and bottleneck analysis
- Identifies patterns if they exist
- Suggests improvements

**Priority:** P0 (Must Have)

### Story 4: Monthly Organization Report
**As an** engineering manager
**I want** an automated monthly report of team accomplishments
**So that** I can share our impact with the broader organization

**Acceptance Criteria:**
- Generated automatically first of month
- Executive-level language
- Highlights impact, not just activity
- Ready to send with < 10 minutes of editing

**Priority:** P1 (Should Have)

### Story 5: Contribution History for Reviews
**As a** team member
**I want** to see what I worked on this quarter
**So that** I can prepare for my performance review

**Acceptance Criteria:**
- Query: "What did I work on in Q3?"
- Returns PR list with impact summaries
- Shows review participation
- Includes relevant metrics

**Priority:** P1 (Should Have)

### Story 6: Codebase Change Tracking
**As an** engineering manager
**I want** to know what changed in critical codebase areas
**So that** I can assess risk and understand focus areas

**Acceptance Criteria:**
- Query: "What changed in [directory] recently?"
- Returns PR list with context
- Shows why changes were made
- Identifies if area needs attention

**Priority:** P0 (Must Have)

---

## 5. Non-Functional Requirements

### 5.1 Performance

**NFR-1: Query Response Time**
- Simple queries (who, what, when): < 30 seconds
- Complex analysis (why, trends): < 2 minutes
- bi-weekly digest generation: < 5 minutes

**Business Impact:** Users won't adopt if too slow

**NFR-2: Data Freshness**
- Data must refresh daily
- PRs merged yesterday must be queryable today
- No real-time requirement (daily batch acceptable)

**Business Impact:** bi-weekly reports need current data

### 5.2 Availability

**NFR-3: Uptime**
- Query interface: 99% uptime (best effort)
- Daily data collection must complete reliably
- Graceful degradation if external services unavailable

**Business Impact:** System must be dependable enough to rely on

### 5.3 Usability

**NFR-4: No Technical Knowledge Required**
- Users should not need SQL knowledge
- Users should not need to understand database schema
- Natural language queries should "just work"

**Business Impact:** Broad adoption across technical levels

**NFR-5: Response Quality**
- Answers must be accurate (verifiable against GitHub)
- Summaries must be coherent and professional
- Output suitable for forwarding to leadership

**Business Impact:** Trust is critical for adoption

### 5.4 Cost

**NFR-6: Budget Constraint**
- Total operating cost: < $100/month
- No significant upfront infrastructure costs
- Use GCP managed services (serverless where possible)

**Business Impact:** Must be cost-effective at scale

### 5.5 Security & Privacy

**NFR-7: Data Access Control**
- Users can only query repositories they have access to
- No exposure of sensitive data in logs
- Comply with Mozilla data handling policies

**Business Impact:** Maintain security posture

**NFR-8: Public Repository Priority**
- Initial support for public repositories only
- Private repository support: content must stay within GCP

**Business Impact:** Reduce compliance complexity initially

### 5.6 Scalability

**NFR-9: User Capacity**
- Support 2-5 primary users initially
- Scale to 10+ secondary users within 3 months
- Support 300-400 PRs/month data volume

**Business Impact:** System must grow with adoption

---

## 6. Constraints

### 6.1 Technical Constraints
- **Platform:** Must use Google Cloud Platform (GCP)
- **Integration:** Must work with existing Mozilla GCP infrastructure
- **Repository:** Initial focus on mozilla/bigquery-etl repository

### 6.2 Timeline Constraints
- **MVP:** Must deliver working prototype within 1 week
- **Production:** Must be production-ready within 1 month
- **Adoption:** Must achieve 50% manager adoption within 2 months

### 6.3 Budget Constraints
- **Operating Cost:** < $100/month
- **Development Time:** Limited engineering resources (1 developer)

### 6.4 Organizational Constraints
- Must align with Mozilla's open-source values
- Should be extensible to other teams/repositories
- Documentation must enable self-service

---

## 7. Success Metrics

### 7.1 Usage Metrics

**Metric:** Active Users
- **Target:** 80% of engineering managers (4/5) using bi-weekly
- **Measurement:** Query logs, CLI usage analytics

**Metric:** Query Volume
- **Target:** 50+ queries per week across all users
- **Measurement:** System logs

**Metric:** Automated Report Usage
- **Target:** 100% of managers using automated bi-weekly digest
- **Measurement:** Survey, email forwarding tracking

### 7.2 Efficiency Metrics

**Metric:** Time Saved per bi-weekly Report
- **Baseline:** 30 minutes manual process
- **Target:** 5 minutes with system (83% reduction)
- **Measurement:** User survey

**Metric:** Time to Answer Leadership Questions
- **Baseline:** 15+ minutes (research + respond later)
- **Target:** < 1 minute (answer in meeting)
- **Measurement:** User survey

### 7.3 Quality Metrics

**Metric:** Answer Accuracy
- **Target:** 95%+ answers are factually correct
- **Measurement:** Spot-check against GitHub, user feedback

**Metric:** User Satisfaction
- **Target:** 4.5/5 average rating
- **Measurement:** Quarterly user survey

**Metric:** Report Quality
- **Target:** 90%+ of automated reports forwarded with < 5 min editing
- **Measurement:** User survey

### 7.4 Business Impact Metrics

**Metric:** Organizational Visibility
- **Target:** 2x increase in teams aware of data engineering work
- **Measurement:** Qualitative feedback, survey

**Metric:** Process Improvements Identified
- **Target:** 2+ actionable improvements per quarter
- **Measurement:** Track insights leading to process changes

**Metric:** Manager Workload
- **Target:** "Saves me 2+ hours per week" (user feedback)
- **Measurement:** User survey

---

## 8. Assumptions

1. **GitHub API Access:** Assume continued access to GitHub API with current rate limits
2. **GCP Resources:** Assume access to necessary GCP services (BigQuery, Cloud Run, etc.)
3. **LLM API Access:** Assume Anthropic API or Vertex AI available and performant
4. **User Behavior:** Assume managers will adapt to natural language interface
5. **Data Volume:** Assume PR volume remains < 500/month for first year
6. **Repository Access:** Assume users have appropriate GitHub permissions

---

## 9. Dependencies

### 9.1 Technical Dependencies
- GitHub API availability and stability
- GCP services (BigQuery, Cloud Run, Cloud Scheduler)
- LLM API (Anthropic Claude or Google Vertex AI)
- Embedding models (textembedding-gecko or similar)

### 9.2 Organizational Dependencies
- GCP project and billing account access
- GitHub Personal Access Token with appropriate scopes
- User buy-in and willingness to adopt new tool
- Engineering time for development (1-2 developers)

### 9.3 External Dependencies
- GitHub service uptime
- Anthropic/Google API uptime
- GCP service availability

---

## 10. Risks

### Risk 1: Low User Adoption
**Description:** Managers don't change workflow, continue manual process
**Impact:** High - project fails if not used
**Probability:** Medium
**Mitigation:** Involve managers in design, make MVP immediately useful, demonstrate time savings

### Risk 2: LLM Query Quality
**Description:** Natural language queries produce incorrect or irrelevant results
**Impact:** High - breaks trust, users abandon tool
**Probability:** Medium
**Mitigation:** Extensive testing, human review initially, feedback mechanism

### Risk 3: Cost Overruns
**Description:** LLM API costs exceed budget
**Impact:** Medium - may need to reduce usage or change providers
**Probability:** Low
**Mitigation:** Monitor costs closely, implement caching, have cheaper fallback (Gemini)

### Risk 4: Data Quality Issues
**Description:** Missing or incomplete PR data
**Impact:** Medium - reduces answer quality
**Probability:** Low
**Mitigation:** Robust error handling, data validation, monitoring

### Risk 5: Scope Creep
**Description:** Adding features delays MVP
**Impact:** Medium - delays time-to-value
**Probability:** High
**Mitigation:** Strict MVP scope, defer nice-to-haves to later phases

---

## 11. Out of Scope

The following are explicitly **not** included in this project:

- Real-time data updates (daily batch is sufficient)
- Multiple repository support in MVP (can add later)
- GitHub Actions or CI/CD integration
- Code quality analysis or linting
- Deployment tracking
- Incident management integration
- Custom web dashboards (CLI sufficient for MVP)
- Mobile app
- Integration with Slack/email (defer to Phase 2)
- Historical data beyond 6 months (initially)

---

## 12. Approval & Sign-off

### Stakeholders

| Name | Role | Approval | Date |
|------|------|----------|------|
| [Manager Name] | Engineering Manager | [ ] | |
| [Director Name] | Engineering Director | [ ] | |
| [Team Lead] | Technical Lead | [ ] | |

### Review History

| Version | Date | Reviewer | Comments |
|---------|------|----------|----------|
| 1.0 | 2025-10-16 | Initial Draft | First version based on requirements gathering |

---

**Document End**
