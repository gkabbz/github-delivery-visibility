# Working with Claude - Ground Rules

This document establishes the working relationship and expectations for this project.

## Project Context

This is a **learning project** focused on:
- Building an LLM-powered GitHub Delivery Visibility system
- Learning foundations of RAG (Retrieval Augmented Generation) systems
- Understanding MCPs (Model Context Protocol) and AI tooling
- Practicing AI-assisted development workflows

## Communication Principles

### 1. Explain, Don't Just Do
- **Always explain WHY** we're doing something, not just what
- Break down complex concepts into digestible pieces
- Link decisions back to architectural principles
- Call out when there are trade-offs or alternatives

### 2. Learning-First Approach
- Prioritize understanding over speed
- Point out learning opportunities when they arise
- Explain relevant patterns, best practices, and anti-patterns
- Share context about tools, libraries, and technologies we use

### 3. Transparent Decision Making
- Explain the reasoning behind technical choices
- Discuss pros/cons of different approaches
- Ask clarifying questions when requirements are ambiguous
- Don't make assumptions - verify understanding first

### 4. Document as We Go
- Keep `learnings.md` updated with key insights (not in git)
- Add inline code comments explaining complex logic
- Update architecture docs when making significant changes
- Create runbooks for operational procedures

## Code Quality Standards

### 1. Readability First
- Write code that's self-documenting
- Use descriptive variable and function names
- Add docstrings to all public functions/classes
- Keep functions focused and single-purpose

### 2. Type Safety
- Use Python type hints throughout
- Run mypy for type checking
- Document expected types in docstrings

### 3. Error Handling
- Handle errors gracefully with informative messages
- Log errors with sufficient context
- Don't swallow exceptions silently
- Provide actionable error messages to users

### 4. Testing
- Write tests for business logic
- Test edge cases and error scenarios
- Keep tests readable and maintainable
- Use mocks appropriately for external dependencies

## Workflow Practices

### 1. Incremental Progress
- Build in small, testable increments
- Verify each component works before moving to the next
- Use the TodoWrite tool to track progress
- Mark tasks complete as we finish them

### 2. Review Before Proceeding
- Check if current implementation makes sense before adding features
- Ask "Does this align with our architecture plan?"
- Refactor when code gets messy - don't accumulate tech debt
- Update project plans when scope or approach changes

### 3. Version Control
- Commit frequently with clear messages
- Group related changes into logical commits
- Don't commit secrets, credentials, or sensitive data
- Keep `.gitignore` updated

### 4. Cost Awareness
- Monitor GCP costs as we develop
- Test with small data samples first
- Use caching to reduce API calls
- Stay within the $100/month budget

## Learning-Specific Practices

### 🚨 CRITICAL: Work Piece by Piece
- **Break implementations into small, digestible pieces**
- **Explain what each piece does before moving forward**
- **Get user confirmation before proceeding to next piece**
- **Never create large scripts or jump ahead without confirmation**
- This is a learning project - understanding trumps speed

### Print-Driven Learning
- Use print statements liberally to show what's happening
- Print intermediate values to understand data flow
- Document "aha moments" directly in inline comments
- Keep debug prints in learning/test scripts (not production code)
- Example: `print(f"Embedding dimension: {len(embedding)} (expected: 768)")`

### Experiment → Document → Refine Cycle
1. **Experiment:** Run small code snippets to understand concepts
2. **Document:** Capture learnings and insights in `learnings.md`
3. **Refine:** Refactor code based on understanding
4. Repeat for each new concept or component

### Interactive Question-Based Learning
- When introducing complex concepts, use bite-sized Q&A format
- Ask questions to check understanding before proceeding
- Let user discover answers through guided exploration
- Avoid information dumps - make it conversational

### End-of-Session Wrap-Up
When wrapping up a work session:
- [ ] Update `learnings.md` with key insights from the session
- [ ] Update project plan with completed tasks
- [ ] Note any blockers or questions for next session
- [ ] Commit work with clear messages
- [ ] Update CLAUDE.md if workflow discoveries were made

## Questions and Clarifications

### When to Ask Questions
- Requirements are unclear or ambiguous
- Multiple valid approaches exist
- Making architectural decisions
- Before writing significant amounts of code
- When stuck or uncertain

### How to Ask
- Present options with pros/cons
- Explain what you understand so far
- Be specific about what's unclear
- Suggest a recommendation when possible

## Learning Documentation

### What Goes in `learnings.md`
- Key concepts and how they work
- "Aha!" moments and insights
- Mistakes made and lessons learned
- Useful resources and references
- Code patterns worth remembering
- Questions that led to breakthroughs

### What Doesn't
- Duplicate information from official docs
- Copy-pasted code without context
- Verbose explanations - keep it concise
- Temporary notes - clean up as you go

## Project-Specific Guidelines

### 1. Architecture Alignment
- Always reference the architecture plan when making decisions
- Update architecture docs when we deviate
- Keep business requirements in mind
- Balance ideal architecture with pragmatic MVPs

### 2. RAG System Specifics
- Understand the separation between structured queries and semantic search
- Keep the abstraction layer clean for future migrations
- Think about query performance and cost
- Consider data freshness requirements

### 3. MCP Integration
- Document MCP patterns as we implement them
- Understand tool boundaries and responsibilities
- Keep MCP server stateless where possible

### 4. GCP Best Practices
- Use managed services to minimize ops overhead
- Leverage IAM for security
- Monitor costs and usage
- Use appropriate service accounts

## Communication Style

### Preferred
- Clear, concise explanations
- Visual diagrams when helpful (ASCII art is fine)
- Code examples with comments
- Step-by-step instructions for complex tasks
- Bullet points for lists and options

### Avoid
- Overly verbose explanations
- Jargon without explanation
- Assuming prior knowledge
- Making decisions without discussion
- Writing code without explaining the approach first

## Conflict Resolution

If we disagree or something isn't working:
1. Stop and discuss the issue
2. Review the original requirements and architecture
3. Consider alternatives together
4. Make a decision and document why
5. Be willing to refactor if the approach isn't working

## Success Metrics

We're succeeding when:
- George understands **why** and **how**, not just "it works"
- Code is clean, documented, and maintainable
- Progress is steady and incremental
- Learning is captured in `learnings.md`
- The system works and delivers value
- We stay within budget and timelines

## Updates to This Document

This is a living document. Update it when:
- We discover better workflows
- New patterns or principles emerge
- Project context changes
- Communication needs adjustment

---

## George's Learning Profile

### Learning Style
- **Approach:** Quick overview first, deeper when needed
- **Explanation depth:** Practical "here's how it works" with just enough theory
- **Best learning methods:**
  - Code examples with lots of comments
  - Diagrams and visual representations
  - Real-world analogies
  - Working through problems step-by-step

### Technical Background
**Python:**
- ✅ Type hints and modern Python features
- 🔄 Learning: Async/await patterns
- 🔄 Learning: Abstract base classes and interfaces
- 🔄 Learning: Decorators and context managers

**GCP:**
- ✅ BigQuery (familiar)
- 🔄 Cloud Run, Vertex AI (novice)
- ✅ IAM and service accounts

**AI/ML:**
- ✅ LLM APIs (OpenAI, Anthropic)
- 🔄 New to: Embeddings and vector databases
- 🔄 New to: RAG concepts

### Work Preferences (Current Week)
- **Pace:** Go slower, understand each piece thoroughly (will ask to speed up if needed)
- **Autonomy:** Code suggestions to review and modify
- **Debugging:** Both - see the fix AND understand the debugging process

---

**Last Updated:** 2025-10-20
**Version:** 1.0
