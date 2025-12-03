# Create GuardKit vs Alternatives Comparison Guide

**Priority**: Enhancement
**Category**: Documentation - Decision Support
**Estimated Effort**: 3-4 hours

## Problem

Users evaluating GuardKit need clear comparisons with alternative tools (Linear, JIRA, GitHub Projects, Spec-Kit, Kiro, Tessl) to make informed decisions. Currently, this information is scattered across README.md and CLAUDE.md.

## Comparison Dimensions

### 1. GuardKit vs Linear
- AI assistance vs manual task management
- Quality gates vs no enforcement
- Parallel development vs sequential
- Self-hosted vs SaaS
- Markdown vs proprietary
- Complexity awareness vs reactive

### 2. GuardKit vs JIRA
- Lightweight vs heavyweight
- AI-assisted vs manual
- Zero ceremony vs process-heavy
- Solo/small teams vs enterprise
- Free vs licensed

### 3. GuardKit vs GitHub Projects
- Workflow enforcement vs kanban board
- Quality gates vs manual review
- Parallel development vs basic tracking
- AI agents vs manual work

### 4. GuardKit vs Spec-Kit/Kiro/Tessl
- Spec-Oriented vs Spec-Driven
- Task descriptions vs formal specifications
- 1-2 min setup vs 30+ min specs
- Solo/small teams vs large teams/regulated
- Optional upgrade path to SDD

### 5. GuardKit vs RequireKit
- SOD vs SDD
- When to use each
- How they integrate
- Migration path

### 6. GuardKit + Conductor vs Alternatives
- True parallel development
- State preservation
- Context switching elimination
- Productivity claims (3-5x)

## Acceptance Criteria

1. Create `docs/guides/comparison.md` page
2. Add to "Getting Started" navigation
3. Include comparison tables for each tool
4. Content must include:
   - Feature comparison matrix
   - Use case recommendations
   - Pros/cons for each alternative
   - Migration considerations
   - Cost comparison (free vs paid)
   - When NOT to use GuardKit
5. Be fair and objective (no FUD)
6. Link to tool websites for more info

## Feature Comparison Matrix

| Feature | GuardKit | Linear | JIRA | GitHub Projects |
|---------|-----------|--------|------|-----------------|
| AI-Assisted | ✅ | ❌ | ❌ | ❌ |
| Quality Gates | ✅ | ❌ | Partial | ❌ |
| Parallel Dev | ✅ (Conductor) | ❌ | ❌ | ❌ |
| Self-Hosted | ✅ | ❌ | ✅ | ❌ |
| Cost | Free | $8-19/mo | $8-16/mo | Free |
| Setup Time | 5 min | 30 min | 2-4 hours | 15 min |
| Complexity | Simple | Medium | Complex | Simple |

## Implementation Notes

- Extract from README.md competitive positioning
- Be factual and evidence-based
- Update as alternatives evolve
- Include links to official websites
- Add "Last updated" date

## References

- README.md lines 187-220 (What Makes GuardKit Different)
- README.md lines 33-39 (SOD vs SDD table)
- README.md lines 73-96 (Parallel Development competitive gaps)
- Official websites: Linear, JIRA, GitHub, Spec-Kit, Kiro, Tessl
