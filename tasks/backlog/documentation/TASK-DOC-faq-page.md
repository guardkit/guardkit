# Create Comprehensive FAQ Page

**Priority**: Enhancement
**Category**: Documentation - User Support
**Estimated Effort**: 2-3 hours

## Problem

Users have common questions about GuardKit's design decisions, capabilities, and comparison with other tools. A comprehensive FAQ page can reduce support burden and improve user understanding.

## FAQ Categories

### 1. Getting Started
- "What is GuardKit?"
- "How is it different from Linear/Jira?"
- "Do I need RequireKit?"
- "What tech stacks are supported?"
- "Can I use it for existing projects?"

### 2. Hash-Based Task IDs
- "Why hash-based instead of sequential?"
- "Will users hate typing TASK-a3f8?"
- "How do PM tools handle hash IDs?"
- "Can I still use sequential IDs?"
- "How long are the IDs?"
- "What about parallel development?"

### 3. Quality Gates
- "Why are quality gates mandatory?"
- "Can I skip architectural review?"
- "What if tests keep failing?"
- "Can I customize coverage thresholds?"
- "Why 80% line coverage requirement?"

### 4. Templates
- "Should I use reference templates?"
- "Why was guardkit-python removed?"
- "How do I create custom templates?"
- "Can templates be shared across teams?"
- "What makes a good template?"

### 5. AI Agents
- "How does agent discovery work?"
- "Can I create custom agents?"
- "What are boundary sections?"
- "Why use Haiku vs Sonnet agents?"
- "How accurate are AI implementations?"

### 6. Parallel Development
- "Do I need Conductor.build?"
- "How many tasks can run in parallel?"
- "Will states conflict?"
- "Is it safe for teams?"

### 7. Integration
- "Does it work with GitHub?"
- "Can I integrate with JIRA?"
- "What about CI/CD?"
- "MCP servers required?"
- "VS Code extension available?"

### 8. Troubleshooting
- "Installation fails, what now?"
- "Commands not found after install"
- "Wrong directory errors"
- "Agent not discovered"

## Acceptance Criteria

1. Create `docs/faq.md` page
2. Add to top-level navigation in MkDocs
3. Organize by categories (collapsible sections)
4. Each FAQ must include:
   - Clear question
   - Concise answer (2-4 sentences)
   - Link to detailed documentation if applicable
   - Code examples where helpful
5. Add table of contents for easy navigation
6. Include search-friendly keywords
7. Link from homepage and Getting Started

## Implementation Notes

- Extract hash ID FAQs from CLAUDE.md
- Use collapsible sections (MkDocs details/summary)
- Keep answers concise, link to deep dives
- Update as new common questions emerge
- Add "Didn't find your answer?" section with support links

## Example Format

```markdown
### Why hash-based IDs instead of sequential?

Hash-based IDs prevent duplicates in concurrent and distributed workflows. This is critical for Conductor.build support and parallel development across multiple worktrees. Sequential IDs would create conflicts when multiple developers or AI agents create tasks simultaneously.

**Learn more**: [Hash-Based Task IDs Guide](concepts/hash-based-task-ids.md)
```

## References

- CLAUDE.md hash ID FAQ section
- README.md "What Makes GuardKit Different?"
- Common support questions
- GitHub issues
