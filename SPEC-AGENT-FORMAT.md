# Agent Format - Structural Best Practices Formatter

Apply GitHub structural best practices to agent documentation files using pattern-based transformation.

**Status**: SPECIFICATION (Ready for `/task-create`)

## Purpose

Batch format agent documentation files to meet GitHub best practices for documentation structure, example placement, and readability. This is a **lightweight, standalone formatter** that applies structural transformations without template-specific content enhancement.

**Key Difference from `/agent-enhance`:**
- **`/agent-format`**: Structural formatting only (examples placement, sections, boundaries) - works on ANY agent
- **`/agent-enhance`**: Content enhancement with template-specific examples - requires template context

**Use Cases:**
1. Format 15 global agents to meet GitHub standards (20-35 hours manual → 7.5 minutes automated)
2. Format 10+ template agents across 6 templates
3. Quick structural cleanup of user-created agents
4. Pre-distribution formatting for team agents
5. CI/CD quality gates for agent documentation

## Usage

```bash
# Format single agent
/agent-format installer/global/agents/architectural-reviewer.md

# Format agent with quality report
/agent-format installer/global/agents/test-verifier.md --report

# Preview changes without applying
/agent-format installer/global/agents/task-manager.md --dry-run

# Batch format all global agents
/agent-format installer/global/agents/*.md

# Batch format template agents
/agent-format ~/.agentecflow/templates/react-typescript/agents/*.md

# Format with verbose progress tracking
/agent-format installer/global/agents/*.md --verbose

# Validation only (no changes)
/agent-format installer/global/agents/code-reviewer.md --validate-only
```

## Command Options

### Required Arguments

```bash
agent_path(s)            One or more agent file paths
                         Supports:
                         - Single file: /path/to/agent.md
                         - Wildcard: /path/to/agents/*.md
                         - Multiple: agent1.md agent2.md agent3.md

                         Path resolution:
                         - Absolute paths used directly
                         - Relative paths resolved from current working directory
                         - Glob patterns expanded using shell expansion
```

### Optional Flags

```bash
--dry-run               Show formatting preview without applying changes
                        Shows before/after metrics and structural diff
                        Default: false

--report                Generate detailed quality report for each agent
                        Saved as {agent_dir}/{agent_name}-format-report.md
                        Default: false (only show summary metrics)

--validate-only         Run validation checks without formatting
                        Shows current quality metrics and recommendations
                        Default: false

--verbose               Show detailed progress for each formatting step
                        Default: false (only show summary)

--fail-on-warn         Exit with code 1 if any warnings detected
                        Default: false (warnings are non-fatal)

--max-iterations N      Maximum self-validation iterations per agent
                        Default: 3 (per GitHub best practices)

--skip-backup          Don't create .bak files before formatting
                        Default: false (backups created)
```

## Formatting Rules (GitHub Best Practices)

### 1. Time to First Example (CRITICAL)

**Target**: First code example within 50 lines of frontmatter end

**Transformation Logic**:
1. Parse agent file, locate frontmatter end (line N)
2. Find first ```code block (line M)
3. If M - N > 50:
   - Move "Purpose" section after frontmatter (lines N+1 to N+20 max)
   - Insert "Quick Start" section with minimal example (lines N+21 to N+45)
   - Move detailed content after Quick Start
4. If no code examples exist:
   - Generate placeholder example section
   - Mark as [NEEDS_EXAMPLE] for manual completion

**Example Transformation**:
```markdown
# BEFORE (first example at line 150)
---
name: test-verifier
---
# Test Verifier
## Purpose
Long description...
## Capabilities
Bullet list...
## Technologies
...

# AFTER (first example at line 35)
---
name: test-verifier
---
# Test Verifier

## Quick Start

### Basic Usage
```bash
/task-work TASK-001 --mode=tdd
```
**Expected Output**: Test execution with coverage report

## Purpose
Long description...
```

### 2. Example Density (CRITICAL)

**Target**: 40-50% of content should be code examples

**Transformation Logic**:
1. Count total lines (excluding frontmatter): T
2. Count code block lines: C
3. Calculate density: D = (C / T) × 100
4. If D < 30%:
   - **FAIL**: Agent needs manual example addition
   - Add [NEEDS_EXAMPLES] markers in relevant sections
5. If 30% ≤ D < 40%:
   - **WARN**: Suggest example additions
   - Identify sections lacking examples
6. If D ≥ 40%:
   - **PASS**: No changes needed

**Note**: This formatter does NOT generate new examples (that's `/agent-enhance`'s job). It only validates density and marks sections needing examples.

### 3. Boundary Sections (REQUIRED)

**Target**: ALWAYS/NEVER/ASK sections present after Quick Start

**Transformation Logic**:
1. Check for existence of boundary sections
2. If missing, insert template structure:

```markdown
## Boundaries

### ALWAYS
- [NEEDS_CONTENT] Review this section and add 5-7 non-negotiable rules
- Example: "Run all tests before marking task as IN_REVIEW"

### NEVER
- [NEEDS_CONTENT] Review this section and add 5-7 prohibited actions
- Example: "Skip architectural review for 'simple' changes"

### ASK
- [NEEDS_CONTENT] Review this section and add 3-5 escalation scenarios
- Example: "When acceptance criteria conflict with implementation plan"
```

3. Insert after "Quick Start" section (or after "Purpose" if no Quick Start)
4. Mark with [NEEDS_CONTENT] for manual completion

**Preservation Logic**:
- If boundary sections already exist, preserve content
- Only reorder placement if in wrong location
- Validate section completeness (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)

### 4. Commands-First Structure (CRITICAL)

**Target**: Working command example in first 50 lines

**Transformation Logic**:
1. Detect if agent is command-invokable (has command syntax)
2. If yes and no command example in first 50 lines:
   - Generate "Quick Start" section at line 20-30
   - Insert command example with basic flags
   - Add expected output example

**Command Detection Patterns**:
- Agent name matches `/[a-z-]+-(specialist|reviewer|verifier|manager|orchestrator)/`
- Description contains "invoked during", "called by", "use /command"
- Frontmatter contains `invocation:` field

**Example Insertion**:
```markdown
## Quick Start

### Basic Command
```bash
/{agent-name} [primary-argument]
```

### With Common Options
```bash
/{agent-name} [primary-argument] --option=value
```

### Expected Output
```
[Sample output showing success state]
```
```

### 5. Code-to-Text Ratio (CRITICAL)

**Target**: ≥1:1 (one code block per prose paragraph)

**Transformation Logic**:
1. Count prose paragraphs (excluding headings, lists): P
2. Count code blocks: C
3. Calculate ratio: R = C / P
4. If R < 0.5:
   - **FAIL**: Insufficient examples
   - Mark sections with [NEEDS_CODE_EXAMPLE]
5. If 0.5 ≤ R < 1.0:
   - **WARN**: Below target ratio
   - Suggest example placement
6. If R ≥ 1.0:
   - **PASS**: Good balance

**Marking Strategy**:
```markdown
## Capabilities [NEEDS_CODE_EXAMPLE]

This agent performs architectural review using SOLID principles.
[NEEDS_CODE_EXAMPLE: Show example command or code snippet]

It analyzes code structure and provides recommendations.
[NEEDS_CODE_EXAMPLE: Show example output or report format]
```

### 6. Section Reordering

**Target Order** (GitHub industry standard):
1. YAML Frontmatter
2. Title (H1)
3. Purpose Statement (50-100 words)
4. Quick Start (first code example < line 50)
5. Boundaries (ALWAYS/NEVER/ASK)
6. When to Use (scenarios)
7. Capabilities (bullet list)
8. Detailed Sections (examples, patterns, integration)

**Transformation Logic**:
1. Parse all sections by heading level
2. Detect section types by heading text pattern matching
3. Reorder according to target structure
4. Preserve all content, only change order
5. Maintain heading hierarchy (H2, H3, H4)

**Section Detection Patterns**:
```python
SECTION_PATTERNS = {
    "purpose": r"^(Purpose|Overview|About)$",
    "quick_start": r"^(Quick Start|Getting Started|Usage)$",
    "boundaries": r"^(Boundaries|Rules|Constraints)$",
    "when_to_use": r"^(When to Use|Use Cases|Scenarios)$",
    "capabilities": r"^(Capabilities|Features|What It Does)$",
}
```

## Implementation Approach

### Architecture: Pattern-Based Transformation (No AI Required)

**Why Pattern-Based?**
- **Speed**: <30 seconds per agent (vs 2-5 minutes with AI)
- **Reliability**: 100% consistent formatting (vs 70-80% with AI)
- **Deterministic**: Same input → same output
- **No Dependencies**: Works without Claude API access
- **Batch-Friendly**: Can process 25 agents in <15 minutes

### Core Algorithm

```python
class AgentFormatter:
    """Pattern-based agent documentation formatter."""

    def format_agent(self, agent_path: Path) -> FormatResult:
        """
        Format single agent file.

        Algorithm:
        1. Parse markdown (frontmatter + sections)
        2. Validate current quality metrics
        3. Apply transformations (structure, examples, boundaries)
        4. Self-validate (3 iterations max)
        5. Return formatted content + metrics
        """
        # Phase 1: Parse
        agent = self._parse_agent(agent_path)

        # Phase 2: Baseline metrics
        before_metrics = self._calculate_metrics(agent)

        # Phase 3: Transform (iterative)
        for iteration in range(self.max_iterations):
            agent = self._apply_transformations(agent)
            after_metrics = self._calculate_metrics(agent)

            if self._meets_thresholds(after_metrics):
                break  # Success

        # Phase 4: Generate result
        return FormatResult(
            agent=agent,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            iterations=iteration + 1,
            status=self._determine_status(after_metrics)
        )

    def _apply_transformations(self, agent: Agent) -> Agent:
        """Apply all formatting transformations."""
        agent = self._ensure_quick_start(agent)       # Time to first example
        agent = self._insert_boundaries(agent)        # ALWAYS/NEVER/ASK
        agent = self._reorder_sections(agent)         # GitHub structure
        agent = self._mark_missing_examples(agent)    # Code-to-text ratio
        agent = self._validate_commands(agent)        # Commands-first
        return agent
```

### Parsing Strategy

**Markdown Parsing**:
1. Use Python `frontmatter` library for YAML frontmatter
2. Use regex patterns for heading detection (`^#{1,6}\s+(.+)$`)
3. Use regex for code block detection (` ```(.+?)``` ` with DOTALL)
4. Preserve exact whitespace and formatting
5. Track line numbers for metrics calculation

**Section Tree Structure**:
```python
@dataclass
class Section:
    level: int              # Heading level (1-6)
    title: str              # Heading text
    content: str            # Section body (excluding children)
    children: List[Section] # Nested sections
    line_start: int         # Starting line number
    line_end: int          # Ending line number
    code_blocks: List[str] # Code blocks in this section
```

### Content Preservation

**Critical Principle**: Never lose existing content

**Preservation Rules**:
1. **Frontmatter**: Preserve exactly, only validate structure
2. **Code Blocks**: Never modify content, only relocate
3. **Prose**: Preserve wording, only mark for improvement
4. **Lists**: Preserve items, only validate completeness
5. **Links**: Preserve all references
6. **Custom Sections**: Preserve if not conflicting with GitHub structure

**Marking Strategy** (for manual completion):
```markdown
[NEEDS_CONTENT]          # Empty required section
[NEEDS_EXAMPLE]          # Section needs code example
[NEEDS_CODE_EXAMPLE]     # Specific location for code
[REVIEW_PLACEMENT]       # Section may be in wrong location
```

## Validation & Reporting

### Metrics Calculation

```python
@dataclass
class QualityMetrics:
    # Critical metrics
    time_to_first_example: int           # Lines from frontmatter to first code block
    example_density: float               # Percentage of lines in code blocks
    boundary_sections: List[str]         # Present boundary sections
    commands_first: int                  # Lines to first command example
    specificity_score: int               # 0-10 based on rubric
    code_to_text_ratio: float            # Code blocks per prose paragraph

    # Section presence
    has_purpose: bool
    has_quick_start: bool
    has_boundaries: bool
    has_examples: bool

    # Counts
    total_lines: int                     # Excluding frontmatter
    code_block_lines: int
    prose_paragraphs: int
    code_blocks: int

    # Validation status
    overall_status: str                  # PASS | WARN | FAIL
    failed_checks: List[str]
    warnings: List[str]
```

### Validation Thresholds

```python
THRESHOLDS = {
    "time_to_first_example": {"fail": 50, "warn": 40},
    "example_density": {"fail": 30, "warn": 40},
    "boundary_sections": {"fail": 0, "warn": 2},  # Require all 3
    "commands_first": {"fail": 50, "warn": 40},
    "specificity_score": {"fail": 8, "warn": 9},
    "code_to_text_ratio": {"fail": 0.5, "warn": 1.0},
}

def determine_status(metrics: QualityMetrics) -> str:
    """
    Determine overall status from metrics.

    Logic:
    - FAIL: Any metric below fail threshold
    - WARN: Any metric below warn threshold (but above fail)
    - PASS: All metrics above warn threshold
    """
    if any(metric_below_fail_threshold(m) for m in metrics):
        return "FAIL"
    elif any(metric_below_warn_threshold(m) for m in metrics):
        return "WARN"
    else:
        return "PASS"
```

### Report Formats

#### 1. Summary Report (Default - Terminal Output)

```
✅ Formatted architectural-reviewer.md

Before → After:
  time_to_first_example: 150 lines → 35 lines ✅
  example_density: 25% → 43% ✅
  boundary_sections: [] → ["ALWAYS", "NEVER", "ASK"] ✅
  commands_first: N/A → 28 lines ✅
  specificity_score: 9/10 → 9/10 ✅
  code_to_text_ratio: 0.4:1 → 1.1:1 ✅

Overall: PASSED (6/6 checks)
Iterations: 2
Changes: 12 sections reordered, 3 sections added
```

#### 2. Detailed Report (--report flag - Markdown file)

```markdown
# Agent Format Report: architectural-reviewer.md

**Generated**: 2025-11-22 14:30:00
**Status**: PASSED (6/6 checks)
**Iterations**: 2

## Metrics Summary

| Metric | Before | After | Threshold | Status |
|--------|--------|-------|-----------|--------|
| Time to First Example | 150 lines | 35 lines | <50 lines | ✅ PASS |
| Example Density | 25% | 43% | ≥40% | ✅ PASS |
| Boundary Sections | 0/3 | 3/3 | 3/3 | ✅ PASS |
| Commands-First | N/A | 28 lines | <50 lines | ✅ PASS |
| Specificity Score | 9/10 | 9/10 | ≥8/10 | ✅ PASS |
| Code-to-Text Ratio | 0.4:1 | 1.1:1 | ≥1.0:1 | ✅ PASS |

## Changes Applied

### Structural Changes
1. ✅ Inserted "Quick Start" section at line 22
2. ✅ Moved first code example from line 150 to line 35
3. ✅ Added "Boundaries" section with ALWAYS/NEVER/ASK templates
4. ✅ Reordered sections: Purpose → Quick Start → Boundaries → Capabilities

### Content Additions
1. ⚠️ Marked 3 sections with [NEEDS_CODE_EXAMPLE]
2. ⚠️ Added boundary section templates requiring manual completion

### Validation Warnings
- None

## Recommendations

### High Priority
None - all thresholds met

### Optional Improvements
1. Consider adding more code examples to "Integration Points" section
2. Expand "Common Patterns" with real-world scenarios

## Next Steps

1. ✅ Review boundary sections and replace [NEEDS_CONTENT] markers
2. ✅ Review [NEEDS_CODE_EXAMPLE] markers and add relevant examples
3. ✅ Commit formatted agent to version control
```

#### 3. Batch Progress Report (--verbose flag)

```
Formatting 15 agents...

[1/15] architectural-reviewer.md
  ✓ Parsed (0.1s)
  ✓ Transformed (0.3s)
  ✓ Validated iteration 1: WARN (density=35%)
  ✓ Validated iteration 2: PASS
  ✅ Formatted (0.5s total)

[2/15] test-verifier.md
  ✓ Parsed (0.1s)
  ✓ Transformed (0.2s)
  ✓ Validated iteration 1: PASS
  ✅ Formatted (0.3s total)

...

[15/15] software-architect.md
  ✓ Parsed (0.1s)
  ✓ Transformed (0.4s)
  ✓ Validated iteration 1: FAIL (no examples)
  ✓ Validated iteration 2: WARN (density=32%)
  ✓ Validated iteration 3: WARN (density=33%)
  ⚠️ Formatted with warnings (0.6s total)

Summary:
  Total: 15 agents
  Passed: 12 (80%)
  Warnings: 3 (20%)
  Failed: 0 (0%)
  Duration: 7.2 seconds
  Avg: 0.48s per agent
```

### Validation-Only Mode (--validate-only)

```bash
$ /agent-format installer/global/agents/task-manager.md --validate-only

Validation Report: task-manager.md

Current Metrics:
  time_to_first_example: 185 lines ❌ FAIL (threshold: 50)
  example_density: 18% ❌ FAIL (threshold: 30%)
  boundary_sections: [] ❌ FAIL (required: 3)
  commands_first: 45 lines ✅ PASS (threshold: 50)
  specificity_score: 9/10 ✅ PASS (threshold: 8)
  code_to_text_ratio: 0.3:1 ❌ FAIL (threshold: 1.0)

Overall: FAILED (3/6 checks)

Recommendations:
1. CRITICAL: Move first code example to within 50 lines
2. CRITICAL: Add boundary sections (ALWAYS/NEVER/ASK)
3. CRITICAL: Increase example density to ≥30% (need 15+ more code lines)
4. HIGH: Add code examples to balance with prose (need 20+ more code blocks)

Run without --validate-only to apply automatic fixes.
```

## Exit Codes & Error Handling

### Exit Codes

```python
EXIT_SUCCESS = 0         # All agents formatted successfully
EXIT_WARNINGS = 1        # Some agents have warnings (only if --fail-on-warn)
EXIT_FILE_ERROR = 2      # File not found or permission denied
EXIT_PARSE_ERROR = 3     # Agent file malformed (invalid frontmatter)
EXIT_VALIDATION_ERROR = 4 # Agent failed validation after 3 iterations
EXIT_BATCH_PARTIAL = 5   # Batch job had some failures
```

### Error Scenarios

#### 1. File Not Found
```bash
Error: Agent file not found: /path/to/missing.md
Exit code: 2
```

#### 2. Permission Denied
```bash
Error: Cannot write to agent file: /path/to/agent.md
Reason: Permission denied
Suggestion: Check file permissions or run with appropriate privileges
Exit code: 2
```

#### 3. Invalid Frontmatter
```bash
Error: Failed to parse agent file: /path/to/agent.md
Reason: Invalid YAML frontmatter (line 5: unexpected token)
Suggestion: Fix YAML syntax in frontmatter
Exit code: 3
```

#### 4. Validation Failed After Max Iterations
```bash
Warning: Agent did not meet thresholds after 3 iterations: agent.md
Current status: WARN (density=32%, threshold=40%)
Action: Formatted with [NEEDS_EXAMPLE] markers for manual completion
Exit code: 0 (warnings are non-fatal by default)
```

#### 5. Batch Partial Failure
```bash
Batch formatting completed with errors:
  Succeeded: 12/15 (80%)
  Warnings: 2/15 (13%)
  Failed: 1/15 (7%)

Failed agents:
  - broken-agent.md: Invalid frontmatter (exit code 3)

Exit code: 5
```

### Error Recovery

**Backup Strategy**:
```python
def format_with_backup(agent_path: Path) -> None:
    """Format agent with automatic backup."""
    if not args.skip_backup:
        backup_path = agent_path.with_suffix('.md.bak')
        shutil.copy2(agent_path, backup_path)
        print(f"Backup created: {backup_path}")

    try:
        result = format_agent(agent_path)
        write_formatted_agent(agent_path, result.agent)
    except Exception as e:
        if backup_path.exists():
            shutil.copy2(backup_path, agent_path)
            print(f"Restored from backup due to error: {e}")
        raise
```

**Batch Failure Handling**:
- Continue processing remaining agents on individual failures
- Collect all errors and warnings
- Report summary at end
- Exit with appropriate code based on worst failure

## Acceptance Criteria

### Functional Requirements

1. **Single Agent Formatting**
   - [ ] Parse agent file with frontmatter and sections
   - [ ] Calculate before/after quality metrics
   - [ ] Apply all 6 transformation rules
   - [ ] Self-validate with up to 3 iterations
   - [ ] Preserve all existing content
   - [ ] Create backup before formatting
   - [ ] Return formatted agent + metrics

2. **Batch Processing**
   - [ ] Accept wildcard patterns (*.md)
   - [ ] Process agents in sequence
   - [ ] Track progress for each agent
   - [ ] Continue on individual failures
   - [ ] Report batch summary

3. **Dry-Run Mode**
   - [ ] Show before/after metrics
   - [ ] Display structural diff
   - [ ] Don't write changes to file
   - [ ] Exit with appropriate code

4. **Validation-Only Mode**
   - [ ] Calculate current metrics
   - [ ] Show threshold compliance
   - [ ] Provide recommendations
   - [ ] Don't modify file

5. **Reporting**
   - [ ] Terminal summary (default)
   - [ ] Detailed markdown report (--report)
   - [ ] Verbose progress (--verbose)
   - [ ] Validation report (--validate-only)

### Quality Thresholds

1. **Performance**
   - [ ] Single agent: <30 seconds
   - [ ] Batch of 15 agents: <15 minutes
   - [ ] Batch of 25 agents: <25 minutes

2. **Reliability**
   - [ ] 100% content preservation (no data loss)
   - [ ] 100% frontmatter preservation
   - [ ] 100% code block preservation
   - [ ] Deterministic output (same input → same output)

3. **Quality Metrics** (After Formatting)
   - [ ] ≥80% of agents meet all thresholds (PASS status)
   - [ ] ≥95% of agents meet fail thresholds (PASS or WARN status)
   - [ ] 0% data loss or corruption

4. **Error Handling**
   - [ ] Graceful handling of malformed agents
   - [ ] Automatic backup before formatting
   - [ ] Restoration on error
   - [ ] Clear error messages
   - [ ] Appropriate exit codes

### Non-Functional Requirements

1. **Maintainability**
   - [ ] Pattern-based (no AI dependency)
   - [ ] Modular architecture (Parser, Transformer, Validator, Reporter)
   - [ ] Comprehensive unit tests (≥80% coverage)
   - [ ] Integration tests for batch processing
   - [ ] Clear separation of concerns

2. **Usability**
   - [ ] Intuitive command syntax
   - [ ] Helpful error messages
   - [ ] Progress indicators for batch jobs
   - [ ] Clear before/after reporting
   - [ ] Dry-run preview support

3. **Compatibility**
   - [ ] Works with global agents (installer/global/agents/)
   - [ ] Works with template agents (~/.agentecflow/templates/*/agents/)
   - [ ] Works with user agents (any location)
   - [ ] Preserves all markdown flavors
   - [ ] Compatible with Python 3.8+

## Testing Requirements

### Unit Tests

```python
# tests/unit/test_agent_formatter.py

class TestAgentParser:
    def test_parse_valid_agent(self):
        """Parse agent with valid frontmatter and sections."""

    def test_parse_malformed_frontmatter(self):
        """Raise error on invalid YAML."""

    def test_parse_nested_sections(self):
        """Build correct section tree from headings."""

    def test_extract_code_blocks(self):
        """Extract all code blocks with positions."""

class TestMetricsCalculator:
    def test_time_to_first_example(self):
        """Calculate lines from frontmatter to first code block."""

    def test_example_density(self):
        """Calculate percentage of lines in code blocks."""

    def test_boundary_sections(self):
        """Detect ALWAYS/NEVER/ASK sections."""

    def test_code_to_text_ratio(self):
        """Calculate code blocks per prose paragraph."""

class TestTransformations:
    def test_ensure_quick_start_missing(self):
        """Insert Quick Start when missing."""

    def test_ensure_quick_start_exists(self):
        """Preserve existing Quick Start."""

    def test_insert_boundaries(self):
        """Insert boundary sections template."""

    def test_reorder_sections(self):
        """Reorder to GitHub structure."""

    def test_mark_missing_examples(self):
        """Add [NEEDS_EXAMPLE] markers."""

    def test_content_preservation(self):
        """Never lose existing content."""

class TestSelfValidation:
    def test_iterative_improvement(self):
        """Improve metrics over iterations."""

    def test_max_iterations(self):
        """Stop after max iterations."""

    def test_early_exit(self):
        """Exit early when thresholds met."""
```

### Integration Tests

```python
# tests/integration/test_agent_format_command.py

class TestSingleAgentFormatting:
    def test_format_global_agent(self):
        """Format agent in installer/global/agents/."""

    def test_format_template_agent(self):
        """Format agent in template agents directory."""

    def test_dry_run(self):
        """Preview without applying changes."""

    def test_validate_only(self):
        """Validate without formatting."""

    def test_with_report(self):
        """Generate detailed markdown report."""

class TestBatchFormatting:
    def test_batch_all_global_agents(self):
        """Format all 15 global agents."""

    def test_batch_template_agents(self):
        """Format template agent directory."""

    def test_batch_partial_failure(self):
        """Handle individual agent failures."""

    def test_batch_progress_tracking(self):
        """Show progress for each agent."""

class TestErrorHandling:
    def test_missing_file(self):
        """Return exit code 2 for missing file."""

    def test_permission_denied(self):
        """Return exit code 2 for permission error."""

    def test_malformed_frontmatter(self):
        """Return exit code 3 for parse error."""

    def test_backup_and_restore(self):
        """Create backup and restore on error."""
```

### Validation Test Cases

```python
# tests/validation/test_quality_metrics.py

class TestQualityMetrics:
    """Test against real agent files."""

    def test_architectural_reviewer_before(self):
        """Baseline metrics for architectural-reviewer.md."""
        agent = load_agent("installer/global/agents/architectural-reviewer.md")
        metrics = calculate_metrics(agent)

        # Before formatting
        assert metrics.time_to_first_example > 50  # Currently fails
        assert metrics.example_density < 40        # Currently fails

    def test_architectural_reviewer_after(self):
        """Metrics after formatting."""
        agent = load_agent("installer/global/agents/architectural-reviewer.md")
        result = format_agent(agent)

        # After formatting
        assert result.after_metrics.time_to_first_example <= 50
        assert result.after_metrics.example_density >= 40
        assert "ALWAYS" in result.after_metrics.boundary_sections
        assert "NEVER" in result.after_metrics.boundary_sections
        assert "ASK" in result.after_metrics.boundary_sections
```

## Implementation Plan

### Phase 1: Core Parser (1 hour)
- [ ] Frontmatter extraction using `frontmatter` library
- [ ] Section tree parsing using regex
- [ ] Code block detection
- [ ] Line number tracking
- [ ] Unit tests for parser

### Phase 2: Metrics Calculator (1 hour)
- [ ] Time to first example
- [ ] Example density
- [ ] Boundary sections detection
- [ ] Code-to-text ratio
- [ ] Specificity score (simple rubric)
- [ ] Unit tests for metrics

### Phase 3: Transformers (2 hours)
- [ ] Quick Start insertion
- [ ] Boundary sections insertion
- [ ] Section reordering
- [ ] Example marking
- [ ] Commands-first validation
- [ ] Content preservation
- [ ] Unit tests for transformers

### Phase 4: Self-Validation Loop (0.5 hours)
- [ ] Iterative improvement
- [ ] Threshold checking
- [ ] Early exit on success
- [ ] Max iterations handling
- [ ] Unit tests for validation

### Phase 5: Reporting (0.5 hours)
- [ ] Terminal summary formatter
- [ ] Markdown report generator
- [ ] Verbose progress tracker
- [ ] Validation-only reporter
- [ ] Unit tests for reporting

### Phase 6: CLI Integration (1 hour)
- [ ] Argument parsing (argparse)
- [ ] Path resolution
- [ ] Wildcard expansion
- [ ] Batch processing
- [ ] Error handling
- [ ] Exit codes
- [ ] Integration tests

**Total Estimated Time**: 6 hours (4-6 hour target achieved)

## Performance Targets

### Single Agent
- **Parsing**: <0.1 seconds
- **Metrics Calculation**: <0.1 seconds
- **Transformation**: <0.2 seconds
- **Validation** (3 iterations): <0.3 seconds
- **Total**: <30 seconds (with buffer for complex agents)

### Batch Processing
- **15 Global Agents**: <15 minutes (<60s avg per agent)
- **25 Agents** (15 global + 10 template): <25 minutes
- **50 Agents**: <50 minutes (linear scaling)

### Resource Usage
- **Memory**: <50MB per agent
- **CPU**: Single-threaded (pattern matching, no AI)
- **Disk**: Minimal (backup files only)

## Usage Examples

### Example 1: Format Single Global Agent

```bash
$ /agent-format installer/global/agents/architectural-reviewer.md

✅ Formatted architectural-reviewer.md

Before → After:
  time_to_first_example: 150 lines → 35 lines ✅
  example_density: 25% → 43% ✅
  boundary_sections: [] → ["ALWAYS", "NEVER", "ASK"] ✅
  commands_first: N/A → 28 lines ✅
  specificity_score: 9/10 → 9/10 ✅
  code_to_text_ratio: 0.4:1 → 1.1:1 ✅

Overall: PASSED (6/6 checks)
Iterations: 2
Changes: 12 sections reordered, 3 sections added
Backup: installer/global/agents/architectural-reviewer.md.bak
```

### Example 2: Batch Format with Report

```bash
$ /agent-format installer/global/agents/*.md --report --verbose

Formatting 15 agents...

[1/15] architectural-reviewer.md ✅ (0.5s)
[2/15] test-verifier.md ✅ (0.3s)
[3/15] code-reviewer.md ✅ (0.4s)
...
[15/15] software-architect.md ⚠️ (0.6s)

Summary:
  Total: 15 agents
  Passed: 12 (80%)
  Warnings: 3 (20%)
  Failed: 0 (0%)
  Duration: 7.2 seconds
  Reports: installer/global/agents/*-format-report.md
```

### Example 3: Dry-Run Preview

```bash
$ /agent-format installer/global/agents/task-manager.md --dry-run

[DRY RUN] Previewing changes for task-manager.md

Before → After:
  time_to_first_example: 185 lines → 38 lines ✅
  example_density: 18% → 41% ✅

Changes Preview:
  + Line 22: Insert "Quick Start" section
  + Line 35: Insert first code example
  + Line 60: Insert "Boundaries" section
  ~ Line 100-300: Reorder sections

Overall: Would PASS (6/6 checks after formatting)

To apply changes, run without --dry-run
```

### Example 4: Validation Only

```bash
$ /agent-format ~/.agentecflow/templates/react-typescript/agents/testing-specialist.md --validate-only

Validation Report: testing-specialist.md

Current Metrics:
  time_to_first_example: 45 lines ✅
  example_density: 48% ✅
  boundary_sections: ["ALWAYS", "NEVER", "ASK"] ✅
  commands_first: 32 lines ✅
  specificity_score: 9/10 ✅
  code_to_text_ratio: 1.2:1 ✅

Overall: PASSED (6/6 checks)

No formatting needed - agent already meets all quality thresholds!
```

## Related Commands

- `/agent-enhance` - Content enhancement with template-specific examples (requires template context)
- `/template-create` - Creates template including agents (auto-formats with this command)
- `/template-validate` - Comprehensive template audit (Level 3 validation)
- `/task-create` - Create implementation task for `/agent-format` command

## Implementation Notes

### Python Modules

**Command Entry Point**:
- `installer/global/commands/agent-format.py` - CLI entry point

**Core Modules**:
- `installer/global/lib/agent_formatting/parser.py` - Markdown parsing
- `installer/global/lib/agent_formatting/metrics.py` - Quality metrics calculation
- `installer/global/lib/agent_formatting/transformer.py` - Pattern-based transformations
- `installer/global/lib/agent_formatting/validator.py` - Self-validation logic
- `installer/global/lib/agent_formatting/reporter.py` - Report generation

**Shared Utilities**:
- `installer/global/lib/utils/markdown.py` - Markdown utilities
- `installer/global/lib/utils/file_ops.py` - File operations (backup, restore)

### Dependencies

**Required**:
- `frontmatter` - YAML frontmatter parsing
- Python 3.8+ stdlib (re, pathlib, argparse, json)

**Optional**:
- `rich` - Enhanced terminal output (fallback to plain text)
- `diff_match_patch` - Better diff generation (fallback to difflib)

### Configuration

**Default Thresholds** (can be overridden):
```python
# installer/global/lib/agent_formatting/config.py

DEFAULT_THRESHOLDS = {
    "time_to_first_example": {"fail": 50, "warn": 40},
    "example_density": {"fail": 30, "warn": 40},
    "boundary_sections": {"fail": 0, "warn": 2},
    "commands_first": {"fail": 50, "warn": 40},
    "specificity_score": {"fail": 8, "warn": 9},
    "code_to_text_ratio": {"fail": 0.5, "warn": 1.0},
}

MAX_ITERATIONS = 3
BACKUP_EXTENSION = ".bak"
REPORT_FILENAME_PATTERN = "{agent_name}-format-report.md"
```

## See Also

- [GitHub Agent Best Practices Analysis](docs/analysis/github-agent-best-practices-analysis.md) - Research findings
- [Agent Content Enhancer](installer/global/agents/agent-content-enhancer.md) - Template-specific enhancement
- [Template Validation Guide](docs/guides/template-validation-guide.md) - 3-level validation system

---

**Document Status**: READY FOR IMPLEMENTATION
**Estimated Implementation Time**: 4-6 hours
**Target Use Case**: Format 15 global agents + 10+ template agents (25 total) in <25 minutes
**Quality Goal**: ≥80% PASS rate, ≥95% PASS+WARN rate, 0% data loss
