# Add Agent Boundary Sections Documentation to MkDocs

**Priority**: Important
**Category**: Documentation Gap - Agent System
**Estimated Effort**: 2-3 hours

## Problem

CLAUDE.md extensively covers agent boundary sections (ALWAYS/NEVER/ASK framework) as a critical quality improvement, but this is not documented in README.md or the MkDocs site.

## Current State

**CLAUDE.md includes**:
- ALWAYS/NEVER/ASK framework explanation
- GitHub best practices analysis reference
- Rule format and emoji usage
- Validation during enhancement
- Interpretation guidelines
- Examples for testing and repository agents

**MkDocs site**: No coverage of boundary sections

## Acceptance Criteria

1. Create new page: `docs/agents/boundary-sections.md`
2. Add to MkDocs navigation under "Agent System"
3. Content must include:
   - What are boundary sections and why they exist
   - ALWAYS rules (5-7 non-negotiable actions)
   - NEVER rules (5-7 prohibited actions)
   - ASK scenarios (3-5 human escalation triggers)
   - Rule format: `[emoji] [action] ([rationale])`
   - How to interpret boundary rules
   - Validation during `/agent-enhance`
   - Real-world examples from testing-agent, repository-agent
4. Link from Agent Discovery and Agent Enhancement pages

## Implementation Notes

- Extract from CLAUDE.md agent enhancement section
- Use concrete examples (testing, repository, API agents)
- Explain GitHub best practices analysis context
- Show before/after agent quality improvement

## References

- CLAUDE.md (Agent Enhancement with Boundary Sections)
- docs/analysis/github-agent-best-practices-analysis.md
- installer/core/agents/agent-content-enhancer.md
