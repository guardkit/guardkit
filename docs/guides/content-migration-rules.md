# Content Migration Rules for Progressive Disclosure

This document defines the rules and patterns for migrating content from core agent files (`{agent}.md`) to extended files (`{agent}-ext.md`), achieving a 55%+ token reduction while maintaining comprehensive documentation.

## Overview

Progressive disclosure splits agent documentation into two tiers:
- **Core files**: Essential content always loaded (~15KB target)
- **Extended files**: Detailed reference loaded on-demand (~10-50KB)

## Core File Content (Keep in {agent}.md)

### Required Sections (in order)

| Section | Description | Size Target |
|---------|-------------|-------------|
| **Frontmatter** | All metadata (name, description, tools, tags, etc.) | As needed |
| **Title/Overview** | Agent name and 2-3 sentence description | ~200 bytes |
| **Quick Start** | 5-10 essential examples showing common usage | ~3-5KB |
| **Boundaries** | Complete ALWAYS/NEVER/ASK sections | ~2-3KB |
| **Capabilities Summary** | Bullet list of what agent can do | ~500 bytes |
| **Phase Integration** | When agent is invoked in workflow | ~500 bytes |
| **Extended Reference** | Loading instruction for ext file | ~200 bytes |

### Size Targets

```
Core file total: ≤15KB (warning at 20KB)
├── Frontmatter: Variable (typically 500-1500 bytes)
├── Overview: ~200 bytes
├── Quick Start: 3-5KB (5-10 examples max)
├── Boundaries: 2-3KB (5-7 rules per section)
├── Capabilities: ~500 bytes
├── Phase Integration: ~500 bytes
└── Extended Reference: ~200 bytes
```

### Section Patterns (Core)

Regex patterns to identify core content:

```python
CORE_SECTION_PATTERNS = [
    r'^---[\s\S]*?^---',           # Frontmatter block
    r'^# .*',                       # Title (H1)
    r'^## (?:Your )?(?:Core )?Responsibilities',
    r'^## Overview',
    r'^## Quick Start',
    r'^## Boundaries',
    r'^### ALWAYS',
    r'^### NEVER',
    r'^### ASK',
    r'^## Capabilities',
    r'^## Phase Integration',
    r'^## Extended Reference',
    r'^## Configuration',           # Essential for setup
    r'^## Security Considerations', # Critical safety info
    r'^## See Also',               # Navigation aids
    r'^## References',             # Navigation aids
]
```

## Extended File Content (Move to {agent}-ext.md)

### Sections to Move

| Section | Description | Typical Size |
|---------|-------------|--------------|
| **Additional Examples** | Quick Start overflow (examples 11+) | 2-5KB |
| **Detailed Examples** | Comprehensive code examples | 5-15KB |
| **Best Practices** | Full explanations with rationale | 3-8KB |
| **Anti-Patterns** | Code samples showing what NOT to do | 2-5KB |
| **Technology-Specific** | Stack-specific implementation details | 3-10KB |
| **Troubleshooting** | Common issues and solutions | 2-5KB |
| **Edge Cases** | Handling unusual scenarios | 2-4KB |
| **Integration Patterns** | How to work with other agents | 2-5KB |
| **Template Examples** | Framework-specific code samples | 5-15KB |

### Size Expectations

```
Extended file total: 10-50KB (no upper limit)
├── Additional Quick Start: 2-5KB (overflow examples)
├── Detailed Examples: 5-15KB (comprehensive samples)
├── Best Practices: 3-8KB (full explanations)
├── Anti-Patterns: 2-5KB (what NOT to do)
├── Technology-Specific: 3-10KB (stack details)
├── Troubleshooting: 2-5KB (issues/solutions)
├── Edge Cases: 2-4KB (unusual scenarios)
└── Integration: 2-5KB (agent collaboration)
```

### Section Patterns (Extended)

Regex patterns to identify extended content:

```python
EXTENDED_SECTION_PATTERNS = [
    r'^## (?:Additional |Detailed )?Examples?',
    r'^## Best Practices',
    r'^## Anti-?[Pp]atterns?',
    r'^## Template (?:Code )?Examples?',
    r'^## Technology',
    r'^## Stack-Specific',
    r'^## Troubleshooting',
    r'^## Edge Cases',
    r'^## Integration (?:Points|Patterns)',
    r'^## Advanced',
    r'^## Reference',
    r'^## Related Templates',
    r'^## Cross-Stack',
    r'^## Quality Gates',          # Detailed quality info
    r'^## Performance',            # Optimization details
    r'^## History',
    r'^## Changelog',
    r'^## Extended Documentation',
]
```

## Section Decision Matrix

For sections not explicitly categorized:

| Section Pattern | Decision | Rationale |
|-----------------|----------|-----------|
| Unknown section with <5 examples | **Keep in core** | Minimal token impact |
| Unknown section with ≥5 examples | **Move to extended** | Significant content |
| Nested subsections | **Follow parent** | Maintain coherence |
| `## Configuration` | **Keep in core** | Essential for setup |
| `## Security Considerations` | **Keep in core** | Critical safety info |
| `## Performance` | **Move to extended** | Optimization details |
| `## History`/`## Changelog` | **Move to extended** | Reference only |
| `## See Also`/`## References` | **Keep in core** | Navigation aids |
| `## Quick Commands` | **Keep in core** | Essential shortcuts |
| `## Error Response Template` | **Keep in core** | Error handling format |

### Handling Mixed Content Sections

When a section contains both essential and detailed content:

1. **Split the section**: Keep summary in core, move details to extended
2. **Add cross-reference**: Core section ends with reference to extended file
3. **Maintain logical flow**: Core content should be self-contained

**Example - Before (mixed Best Practices):**
```markdown
## Best Practices

1. Always validate input before processing
2. Use async/await for I/O operations
3. Implement proper error handling
4. Cache frequently accessed data
5. Log all critical operations
6. Use connection pooling for databases
7. Implement retry logic for transient failures
8. Use circuit breakers for external calls
... (20 more practices with detailed explanations)
```

**Example - After (split):**

*Core file:*
```markdown
## Best Practices

Essential practices for this agent:
1. Always validate input before processing
2. Use async/await for I/O operations
3. Implement proper error handling

See `{agent}-ext.md` for 20+ additional best practices with code examples.
```

*Extended file:*
```markdown
## Best Practices (Complete)

### Essential (also in core)
1. Always validate input before processing
2. Use async/await for I/O operations
3. Implement proper error handling

### Additional Practices
4. Cache frequently accessed data
5. Log all critical operations
... (full list with detailed explanations)
```

## Quick Start Selection Criteria

When reducing Quick Start from many examples to 5-10:

### Selection Priority (highest to lowest)

1. **Most common use case** - What users do 80% of the time
2. **Simplest working example** - Minimal code to demonstrate capability
3. **Boundary demonstration** - Shows ALWAYS/NEVER rules in action
4. **Error handling** - Common error and proper handling
5. **Integration example** - Working with other agents/tools

### Selection Process

```
1. Count existing Quick Start examples
2. If ≤10: Keep all in core
3. If >10:
   a. Tag each example with priority (1-5 from above)
   b. Keep top 5-7 highest priority in core
   c. Move remaining to extended file under "Additional Examples"
4. Ensure diversity (avoid 5 similar examples)
5. Ensure coverage of main capabilities
```

### Example Selection

For `task-manager` with 25 Quick Start examples:

**Keep in core (5):**
- Create task (priority 1 - most common)
- Work on task (priority 1 - most common)
- Complete task (priority 1 - most common)
- Task status check (priority 2 - simple)
- Error handling example (priority 4 - error handling)

**Move to extended (20):**
- Advanced filtering
- Bulk operations
- Design-first workflow details
- Integration with review workflow
- Edge cases and special scenarios

## Extended Reference Section Format

Every core file must include this section at the end:

```markdown
## Extended Reference

For detailed examples, best practices, and troubleshooting:

\`\`\`bash
cat agents/{agent-name}-ext.md
\`\`\`

The extended file includes:
- Additional Quick Start examples (X more)
- Detailed code examples with explanations
- Best practices with rationale
- Anti-patterns to avoid
- Technology-specific guidance
- Troubleshooting common issues
```

## Migration Process

### Per-Agent Steps

1. **Backup**
   ```bash
   cp installer/global/agents/{agent}.md installer/global/agents/{agent}.md.bak
   ```

2. **Analyze structure**
   ```bash
   grep "^##" installer/global/agents/{agent}.md
   wc -c installer/global/agents/{agent}.md
   ```

3. **Identify content to move**
   - Apply section patterns above
   - Use decision matrix for ambiguous cases

4. **Create/update extended file**
   - Add header with agent reference
   - Move identified content
   - Maintain section order

5. **Update core file**
   - Keep required sections
   - Add cross-references where content was removed
   - Add Extended Reference section

6. **Validate**
   ```bash
   wc -c installer/global/agents/{agent}.md      # Should be ≤15KB
   wc -c installer/global/agents/{agent}-ext.md  # Should have moved content
   ```

### Validation Checks

After migration, verify:

- [ ] Core file ≤ target size
- [ ] Extended file contains moved content
- [ ] Total content ≈ original (no loss)
- [ ] All required sections present in core
- [ ] Extended Reference section added
- [ ] Agent discovery still works
- [ ] No broken references

## Size Targets by Agent

Based on current sizes and 55%+ reduction target:

| Agent | Current | Core Target | Reduction |
|-------|---------|-------------|-----------|
| task-manager | 72KB | ≤25KB | 65% |
| devops-specialist | 57KB | ≤20KB | 65% |
| git-workflow-manager | 50KB | ≤18KB | 64% |
| security-specialist | 49KB | ≤18KB | 63% |
| database-specialist | 46KB | ≤17KB | 63% |
| architectural-reviewer | 44KB | ≤16KB | 64% |
| agent-content-enhancer | 33KB | ≤14KB | 58% |
| code-reviewer | 29KB | ≤12KB | 59% |
| debugging-specialist | 29KB | ≤12KB | 59% |
| test-verifier | 27KB | ≤11KB | 59% |
| test-orchestrator | 26KB | ≤11KB | 58% |
| pattern-advisor | 25KB | ≤10KB | 60% |
| complexity-evaluator | 18KB | ≤8KB | 56% |
| build-validator | 16KB | ≤7KB | 56% |

**Total**: 521KB → ≤199KB (**62% reduction**)

## Rollback Strategy

### Before Migration

```bash
# Create backup
cp installer/global/agents/{agent}.md installer/global/agents/{agent}.md.bak

# Verify backup
head -20 installer/global/agents/{agent}.md.bak
```

### If Issues Detected

```bash
# Restore from backup
cp installer/global/agents/{agent}.md.bak installer/global/agents/{agent}.md

# Verify restoration
wc -c installer/global/agents/{agent}.md
```

### Backup Cleanup (after TASK-PD-024)

Only after all validations pass:
```bash
./scripts/test-progressive-disclosure.sh
rm installer/global/agents/*.md.bak
```

**Important**: Retain backups until final validation completes.

## Related Documents

- [Progressive Disclosure Guide](progressive-disclosure.md)
- [Agent Enhancement Guide](agent-enhancement-decision-guide.md)
- [Implementation Report](../reports/progressive-disclosure-implementation-report.md)
