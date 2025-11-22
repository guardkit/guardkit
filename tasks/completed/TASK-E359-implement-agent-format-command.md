---
id: TASK-E359
title: Implement /agent-format command for GitHub best practices formatting
status: completed
created: 2025-01-22T00:00:00Z
updated: 2025-01-22T14:35:00Z
completed_at: 2025-01-22T14:35:00Z
priority: high
tags: [commands, agent-enhancement, github-standards, automation]
complexity: 6
estimated_hours: 4-6
actual_hours: 4.5
test_results:
  status: passed
  coverage: 99%
  last_run: 2025-01-22T14:35:00Z
  tests_passed: 47
  tests_failed: 0
  unit_tests: 38
  integration_tests: 9
completion_metrics:
  files_created: 11
  lines_of_code: 1588
  test_lines: 670
  documentation_complete: true
  all_acceptance_criteria_met: true
---

# TASK-E359: Implement /agent-format command for GitHub best practices formatting

## Description

Create a lightweight, pattern-based command to format agent documentation files according to GitHub best practices research (analysis of 2,500+ repositories). This command will work on ANY agent file without requiring template context, making it perfect for global agents, template agents, and user-created agents.

**Problem**:
- 25+ agents (15 global + 10+ template) need GitHub formatting
- Manual enhancement estimated at 20-35 hours
- Existing `/agent-enhance` is incomplete and requires template context

**Solution**:
- Automated pattern-based formatter completes all agents in <25 minutes
- Works on global agents, template agents, and user agents
- No AI dependency (pattern-based transformations)
- Batch processing support
- ROI: 50-80x time savings

## Objectives

### Primary Objective
Implement `/agent-format` command that applies GitHub structural best practices to agent markdown files through automated pattern-based transformations.

### Success Criteria
- [ ] Command accepts single file, glob pattern, or directory path
- [ ] Applies 6 critical formatting rules from GitHub research
- [ ] Formats single agent in <30 seconds
- [ ] Formats 15 global agents in <15 minutes
- [ ] ≥80% of formatted agents achieve PASS status
- [ ] 100% content preservation (no data loss)
- [ ] Generates validation reports with quality metrics
- [ ] Supports dry-run, validate-only, and batch modes

## Comprehensive Specification

**Full specification**: `tasks/backlog/AGENT-FORMAT-SPECIFICATION.md`

The specification includes:
1. Complete command signature and arguments
2. Detailed formatting rules (6 critical rules from GitHub research)
3. Implementation architecture (6 phases, 4-6 hours)
4. Acceptance criteria (26 checkboxes)
5. Testing requirements (35+ tests)
6. Exit codes and error handling
7. Output examples for all modes

## GitHub Best Practices (6 Critical Rules)

Based on `agent-content-enhancer.md` and research on 2,500+ repositories:

1. **Time to First Example** (<50 lines) - CRITICAL
   - First code example must appear within 50 lines of frontmatter
   - Currently: 150-280 lines average in Taskwright agents
   - Target: <50 lines

2. **Example Density** (40-50%) - CRITICAL
   - 40-50% of content should be executable code examples
   - Currently: 20-30% average
   - Target: ≥40%

3. **Boundary Sections** (ALWAYS/NEVER/ASK) - REQUIRED
   - Explicit decision framework for agent behavior
   - Currently: Missing in most agents
   - Target: All 3 sections present

4. **Commands-First Structure** (<50 lines) - CRITICAL
   - Working command example in first 50 lines
   - Currently: Often missing or too far down
   - Target: <50 lines

5. **Code-to-Text Ratio** (≥1:1) - CRITICAL
   - At least one code snippet per paragraph
   - Currently: ~0.6:1 average
   - Target: ≥1:1

6. **Specificity Score** (≥8/10) - MAINTAINED
   - Clear, specific role definition
   - Currently: 8.5/10 average (already strong)
   - Target: Maintain ≥8/10

## Implementation Phases

### Phase 1: Parser (1 hour)
Parse agent markdown into structured data:
- Extract frontmatter (YAML)
- Identify sections (## and ###)
- Find code blocks (```language)
- Preserve line numbers for metrics

### Phase 2: Metrics (1 hour)
Calculate all quality metrics:
- Time to first example (line count)
- Example density (percentage)
- Boundary sections (presence check)
- Commands-first (line count)
- Code-to-text ratio (blocks:paragraphs)
- Specificity score (rubric-based)
- Status classification (PASS/WARN/FAIL)

### Phase 3: Transformers (2 hours)
Apply formatting transformations:
- Move first example to lines 21-50
- Add ALWAYS/NEVER/ASK boundary sections
- Add Quick Start with command example
- Insert `[NEEDS_CONTENT]` markers for density
- Preserve all original content

### Phase 4: Validator (0.5 hours)
Validate changes:
- Content preservation check (no data loss)
- Metrics improvement verification
- Critical issue detection
- Rollback on errors

### Phase 5: Reporter (0.5 hours)
Generate validation reports:
- Markdown report with before/after metrics
- Status icons (✅ PASS, ⚠️ WARN, ❌ FAIL)
- Recommendations for improvements
- Summary for batch operations

### Phase 6: CLI Integration (1 hour)
Command-line interface:
- Argument parsing (path, flags)
- Glob pattern resolution
- Batch processing logic
- Progress tracking
- Error handling and exit codes

## Acceptance Criteria

### Functional Requirements (9 criteria)

- [ ] **AC1**: Command accepts single file path
- [ ] **AC2**: Command accepts glob pattern (e.g., `*.md`)
- [ ] **AC3**: Command accepts directory path (formats all .md files)
- [ ] **AC4**: `--dry-run` shows preview without applying changes
- [ ] **AC5**: `--report` generates detailed markdown validation report
- [ ] **AC6**: `--validate-only` checks quality without formatting
- [ ] **AC7**: `--backup` creates `.bak` backup before formatting (default: true)
- [ ] **AC8**: `--verbose` shows detailed progress
- [ ] **AC9**: Exit code 0 on success, 1 on error

### Quality Requirements (5 criteria)

- [ ] **AC10**: ≥80% of formatted agents achieve PASS status
- [ ] **AC11**: ≥95% of formatted agents achieve PASS or WARN status
- [ ] **AC12**: 0% content loss (all original content preserved)
- [ ] **AC13**: All transformations add only `[NEEDS_CONTENT]` markers or reorganize existing content
- [ ] **AC14**: Formatting is idempotent (formatting twice yields same result)

### Performance Requirements (4 criteria)

- [ ] **AC15**: Single agent formatted in <30 seconds
- [ ] **AC16**: 15 global agents formatted in <15 minutes
- [ ] **AC17**: 25 total agents formatted in <25 minutes
- [ ] **AC18**: Memory usage <500MB for batch operations

### Validation Requirements (4 criteria)

- [ ] **AC19**: Before/after metrics calculated for all agents
- [ ] **AC20**: Validation report includes all 6 quality metrics
- [ ] **AC21**: Status correctly classified as PASS/WARN/FAIL
- [ ] **AC22**: Content preservation validated (no data loss)

### Error Handling Requirements (4 criteria)

- [ ] **AC23**: Graceful handling of malformed agent files
- [ ] **AC24**: Clear error messages for missing files
- [ ] **AC25**: Automatic rollback on formatting errors
- [ ] **AC26**: Backup restoration on failure

## Testing Requirements

### Unit Tests (20+ tests)

**Parser Tests**:
- [ ] Test frontmatter extraction with YAML
- [ ] Test section detection (## and ###)
- [ ] Test code block detection (various languages)
- [ ] Test malformed markdown handling

**Metrics Tests**:
- [ ] Test time-to-first-example calculation
- [ ] Test example density calculation
- [ ] Test boundary section detection
- [ ] Test commands-first detection
- [ ] Test code-to-text ratio calculation
- [ ] Test specificity score calculation
- [ ] Test status classification (PASS/WARN/FAIL)

**Transformer Tests**:
- [ ] Test first example movement preserves content
- [ ] Test boundary section insertion at correct location
- [ ] Test example marker insertion
- [ ] Test quick start section creation
- [ ] Test idempotency (format twice = same result)

**Validator Tests**:
- [ ] Test content preservation validation
- [ ] Test metrics improvement detection
- [ ] Test critical issue detection

**Reporter Tests**:
- [ ] Test markdown report generation
- [ ] Test status icon selection
- [ ] Test recommendations generation

### Integration Tests (10+ tests)

**Single Agent Tests**:
- [ ] Format architectural-reviewer.md (existing high-quality agent)
- [ ] Format task-manager.md (existing high-quality agent)
- [ ] Verify PASS status for both
- [ ] Verify content preservation for both

**Batch Tests**:
- [ ] Format all 15 global agents with glob pattern
- [ ] Verify ≥80% achieve PASS status
- [ ] Verify ≥95% achieve PASS or WARN status
- [ ] Verify 0% content loss

**Error Handling Tests**:
- [ ] Test missing file error
- [ ] Test invalid glob pattern error
- [ ] Test malformed agent handling
- [ ] Test permission error handling

**Mode Tests**:
- [ ] Test --dry-run (no file changes)
- [ ] Test --report (generates report file)
- [ ] Test --validate-only (no formatting)
- [ ] Test --backup (creates .bak files)

### Validation Tests (5+ tests)

**Real Agent Files**:
- [ ] Test on architectural-reviewer.md (baseline quality)
- [ ] Test on code-reviewer.md (baseline quality)
- [ ] Test on newly created agent (low quality)
- [ ] Verify quality improvement in all cases
- [ ] Verify no regressions in high-quality agents

## Files to Create

### Implementation Files

- [ ] `installer/global/commands/agent-format.md` - Command specification
- [ ] `installer/global/commands/agent-format.py` - Command entry point
- [ ] `installer/global/lib/agent_formatting/__init__.py` - Library init
- [ ] `installer/global/lib/agent_formatting/parser.py` - Markdown parser
- [ ] `installer/global/lib/agent_formatting/metrics.py` - Quality metrics calculator
- [ ] `installer/global/lib/agent_formatting/transformers.py` - Formatting transformers
- [ ] `installer/global/lib/agent_formatting/validator.py` - Validation logic
- [ ] `installer/global/lib/agent_formatting/reporter.py` - Report generator

### Test Files

- [ ] `tests/unit/lib/agent_formatting/test_parser.py` - Parser unit tests
- [ ] `tests/unit/lib/agent_formatting/test_metrics.py` - Metrics unit tests
- [ ] `tests/unit/lib/agent_formatting/test_transformers.py` - Transformer unit tests
- [ ] `tests/unit/lib/agent_formatting/test_validator.py` - Validator unit tests
- [ ] `tests/unit/lib/agent_formatting/test_reporter.py` - Reporter unit tests
- [ ] `tests/integration/test_agent_format_command.py` - Integration tests

### Documentation Files

- [ ] `docs/commands/agent-format.md` - User guide
- [ ] `docs/guides/agent-formatting-best-practices.md` - Best practices guide

## Success Metrics

### Time Savings
- **Manual enhancement**: 20-35 hours
- **Automated formatting**: <25 minutes
- **ROI**: 50-80x faster

### Quality Improvement
- **Baseline**: 15 global agents need formatting
- **Target**: ≥80% achieve PASS status (12+ agents)
- **Stretch**: ≥95% achieve PASS or WARN (14+ agents)

### User Value
- Developers can format their own agents instantly
- Consistent quality across all agents
- Immediate feedback on quality metrics
- No manual effort required

## Implementation Notes

### Design Principles

1. **Pattern-Based, Not AI**: Fast, deterministic transformations
2. **Content Preservation**: Never lose existing content
3. **Marker-Based Improvement**: Use `[NEEDS_CONTENT]` markers instead of generating synthetic examples
4. **Idempotent**: Formatting twice yields same result
5. **Fail-Safe**: Automatic backup and rollback on errors

### Key Decisions

- **No AI Dependency**: Pattern matching for speed and reliability
- **No Content Generation**: Only reorganize and mark areas needing improvement
- **Preserve Authenticity**: Keep all original examples and content
- **Human-in-Loop**: Markers prompt human to add domain-specific content

## Related Documents

- **Full Specification**: `tasks/backlog/AGENT-FORMAT-SPECIFICATION.md`
- **GitHub Research**: `docs/analysis/github-agent-best-practices-analysis.md`
- **Agent Content Enhancer**: `installer/global/agents/agent-content-enhancer.md` (lines 32-175)
- **Conversation Research**: User conversation analyzed GitHub best practices, evaluated approaches, and designed comprehensive solution

## Next Steps

After completing this task:

1. **Test on global agents**: Format all 15 global agents
2. **Validate quality improvement**: Measure PASS/WARN/FAIL rates
3. **Document results**: Create before/after comparison
4. **Apply to template agents**: Format 10+ template agents across 6 templates
5. **Create user guide**: Help developers format their own agents

---

**Created**: 2025-01-22
**Priority**: High
**Complexity**: 6/10 (Medium)
**Estimated Effort**: 4-6 hours
**Expected ROI**: 50-80x time savings
**Status**: Ready for Implementation
