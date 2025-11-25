# /agent-format Command - Comprehensive Specification

## Executive Summary

Create a lightweight, pattern-based command to format agent documentation files according to GitHub best practices research (2,500+ repositories). Unlike `/agent-enhance`, this command works on ANY agent without requiring template context, making it perfect for global agents and user-created agents.

**Problem**: 25+ agents (15 global + 10+ template) need GitHub formatting, manual enhancement takes 20-35 hours
**Solution**: Automated pattern-based formatter completes all agents in <25 minutes
**ROI**: 50-80x time savings, consistent quality across all agents

---

## Command Specification

### Command Signature

```bash
/agent-format <path> [options]
```

### Arguments

**Required:**
- `path` - Agent file path or glob pattern
  - Single file: `/path/to/agent.md` or `agent.md`
  - Glob pattern: `installer/global/agents/*.md`
  - Directory: `installer/global/agents/` (formats all .md files)

**Optional Flags:**
- `--dry-run` - Preview changes without applying (default: false)
- `--report` - Generate detailed validation report (default: false)
- `--validate-only` - Check quality metrics only, no formatting (default: false)
- `--backup` - Create `.bak` backup before formatting (default: true)
- `--verbose` - Show detailed progress (default: false)
- `--fail-on-warn` - Exit with error on warnings (default: false)

### Examples

```bash
# Format single agent
/agent-format installer/global/agents/architectural-reviewer.md

# Format all global agents
/agent-format installer/global/agents/*.md

# Dry-run preview with report
/agent-format architectural-reviewer.md --dry-run --report

# Batch format with validation report
/agent-format installer/global/agents/*.md --report

# Validate quality metrics only (no changes)
/agent-format installer/global/agents/*.md --validate-only
```

---

## Formatting Rules (GitHub Best Practices)

Based on `agent-content-enhancer.md` (lines 32-175) and GitHub research on 2,500+ repositories.

### Rule 1: Time to First Example (<50 lines) - CRITICAL

**Goal**: First code example must appear within 50 lines of frontmatter end

**Algorithm**:
```python
def check_time_to_first_example(content: str) -> tuple[bool, int]:
    """Return (passes, line_number)"""
    lines = content.split('\n')

    # Skip frontmatter
    in_frontmatter = False
    frontmatter_end = 0
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                frontmatter_end = i + 1
                break

    # Find first code block
    for i in range(frontmatter_end, len(lines)):
        if lines[i].strip().startswith('```'):
            line_number = i - frontmatter_end
            return (line_number < 50, line_number)

    return (False, -1)  # No code examples found
```

**Transformation** (if fails):
1. Find "Quick Start" or "Examples" section (or create after role description)
2. If no code examples exist, insert `[NEEDS_CONTENT: Add working code example]` marker
3. If examples exist but too far down, move first example to line 21-50 range
4. Preserve original example location with reference: `<!-- Example moved from line X -->`

### Rule 2: Example Density (40-50%) - CRITICAL

**Goal**: 40-50% of content should be executable code examples

**Algorithm**:
```python
def calculate_example_density(content: str) -> float:
    """Return percentage of content that is code"""
    lines = content.split('\n')

    # Skip frontmatter
    content_lines = skip_frontmatter(lines)

    code_lines = 0
    in_code_block = False

    for line in content_lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            code_lines += 1

    total_lines = len([l for l in content_lines if l.strip()])
    return (code_lines / total_lines * 100) if total_lines > 0 else 0
```

**Transformation** (if <40%):
1. Calculate current density
2. Add `[NEEDS_CONTENT: Add X more code examples to reach 40% density]` markers
3. Suggest ✅/❌ comparison format
4. Do NOT generate synthetic examples (preserve authenticity)

### Rule 3: Boundary Sections (ALWAYS/NEVER/ASK) - REQUIRED

**Goal**: Explicit decision framework for agent behavior

**Algorithm**:
```python
def check_boundary_sections(content: str) -> dict[str, bool]:
    """Return which boundary sections exist"""
    sections = {
        'ALWAYS': '### ALWAYS' in content or '## ALWAYS' in content,
        'NEVER': '### NEVER' in content or '## NEVER' in content,
        'ASK': '### ASK' in content or '## ASK' in content
    }
    return sections
```

**Transformation** (if missing):
1. Find placement: After "Quick Start", before detailed capabilities
2. Insert boundary template:

```markdown
## Boundaries

### ALWAYS
[NEEDS_CONTENT: Add 5-7 non-negotiable rules this agent MUST follow]
- Example: Validate all inputs before processing
- Example: Run tests before any code changes

### NEVER
[NEEDS_CONTENT: Add 5-7 prohibited actions this agent MUST avoid]
- Example: Skip security validation for convenience
- Example: Auto-approve changes without human review

### ASK
[NEEDS_CONTENT: Add 3-5 scenarios requiring human escalation]
- Example: Ambiguous requirements that conflict
- Example: Security tradeoffs affecting performance
```

### Rule 4: Commands-First Structure (<50 lines) - CRITICAL

**Goal**: Working command example in first 50 lines

**Algorithm**:
```python
def check_commands_first(content: str) -> tuple[bool, int]:
    """Return (passes, line_number_of_first_command)"""
    lines = content.split('\n')
    frontmatter_end = find_frontmatter_end(lines)

    # Look for command examples (bash, shell, or command blocks)
    for i in range(frontmatter_end, min(frontmatter_end + 50, len(lines))):
        line = lines[i].strip()
        if line.startswith('```bash') or line.startswith('```shell'):
            return (True, i - frontmatter_end)

    return (False, -1)
```

**Transformation** (if fails):
1. Create "Quick Start" section immediately after role description
2. Add working command example:

```markdown
## Quick Start

### Basic Usage
```bash
[NEEDS_CONTENT: Add command example with flags/options]
```

### Expected Output
```yaml
[NEEDS_CONTENT: Add example output showing validation report]
```
```

### Rule 5: Code-to-Text Ratio (≥1:1) - CRITICAL

**Goal**: At least one code snippet per paragraph of prose

**Algorithm**:
```python
def calculate_code_to_text_ratio(content: str) -> float:
    """Return ratio of code blocks to prose paragraphs"""
    lines = content.split('\n')
    content_lines = skip_frontmatter(lines)

    code_blocks = content.count('```') // 2  # Pairs of backticks

    # Count paragraphs (non-empty, non-heading, non-list lines)
    paragraphs = 0
    in_paragraph = False
    for line in content_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('-'):
            if not in_paragraph:
                paragraphs += 1
                in_paragraph = True
        else:
            in_paragraph = False

    return code_blocks / paragraphs if paragraphs > 0 else 0
```

**Transformation** (if <1.0):
1. Add `[NEEDS_CONTENT: Add code examples - ratio is X:1, target is ≥1:1]` markers
2. Suggest placement after long prose sections

### Rule 6: Specificity Score (≥8/10) - MAINTAINED

**Goal**: Clear, specific role definition

**Algorithm**:
```python
def calculate_specificity_score(agent_content: str) -> int:
    """Return specificity score 0-10"""
    frontmatter = extract_frontmatter(agent_content)
    description = frontmatter.get('description', '')

    score = 0

    # Tech stack mentioned (+4 points)
    tech_keywords = ['React', 'TypeScript', 'Python', 'FastAPI', 'Go', 'Rust', '.NET']
    if any(tech in description for tech in tech_keywords):
        score += 4

    # Domain mentioned (+3 points)
    domain_keywords = ['testing', 'security', 'performance', 'architecture', 'database']
    if any(domain in description.lower() for domain in domain_keywords):
        score += 3

    # Standards mentioned (+3 points)
    standard_keywords = ['SOLID', 'DRY', 'YAGNI', 'TDD', 'BDD', 'WCAG']
    if any(std in description for std in standard_keywords):
        score += 3

    return min(score, 10)
```

**Transformation** (if <8):
1. Add warning: `[NEEDS_IMPROVEMENT: Specificity score is X/10, enhance description to include: tech stack, domain, standards]`
2. Do NOT auto-generate (requires human judgment)

---

## Implementation Architecture

### Module Structure

```
installer/global/lib/agent_formatting/
├── __init__.py
├── parser.py           # Parse agent markdown structure
├── metrics.py          # Calculate quality metrics
├── transformers.py     # Apply formatting rules
├── validator.py        # Validate before/after quality
└── reporter.py         # Generate validation reports
```

### Phase 1: Parser (1 hour)

**Purpose**: Parse agent markdown into structured data

```python
@dataclass
class AgentStructure:
    frontmatter: dict
    sections: list[Section]
    code_blocks: list[CodeBlock]

@dataclass
class Section:
    title: str
    level: int  # heading level (1-6)
    start_line: int
    end_line: int
    content: str

@dataclass
class CodeBlock:
    language: str
    start_line: int
    end_line: int
    content: str
```

**Key Functions**:
- `parse_agent(file_path: Path) -> AgentStructure`
- `extract_frontmatter(content: str) -> dict`
- `find_sections(content: str) -> list[Section]`
- `find_code_blocks(content: str) -> list[CodeBlock]`

### Phase 2: Metrics (1 hour)

**Purpose**: Calculate all quality metrics

```python
@dataclass
class QualityMetrics:
    time_to_first_example: int  # line number
    example_density: float  # percentage
    boundary_sections: dict[str, bool]  # ALWAYS/NEVER/ASK
    commands_first: int  # line number or -1
    code_to_text_ratio: float
    specificity_score: int  # 0-10

    def passes_threshold(self) -> bool:
        """Check if all CRITICAL thresholds met"""
        return (
            self.time_to_first_example < 50 and
            self.example_density >= 30 and  # WARN at 30, PASS at 40
            all(self.boundary_sections.values()) and
            self.commands_first < 50 and
            self.code_to_text_ratio >= 0.8 and  # WARN at 0.8, PASS at 1.0
            self.specificity_score >= 8
        )

    def get_status(self) -> str:
        """Return PASS, WARN, or FAIL"""
        critical_fail = (
            self.time_to_first_example >= 50 or
            self.example_density < 30 or
            not all(self.boundary_sections.values()) or
            self.commands_first >= 50 or
            self.specificity_score < 8
        )

        if critical_fail:
            return "FAIL"

        warning = (
            30 <= self.example_density < 40 or
            0.8 <= self.code_to_text_ratio < 1.0
        )

        return "WARN" if warning else "PASS"
```

**Key Functions**:
- `calculate_metrics(agent: AgentStructure) -> QualityMetrics`
- `check_time_to_first_example(agent) -> int`
- `calculate_example_density(agent) -> float`
- `check_boundary_sections(agent) -> dict`
- `check_commands_first(agent) -> int`
- `calculate_code_to_text_ratio(agent) -> float`
- `calculate_specificity_score(agent) -> int`

### Phase 3: Transformers (2 hours)

**Purpose**: Apply formatting transformations

```python
class AgentFormatter:
    def format(self, agent: AgentStructure, metrics: QualityMetrics) -> AgentStructure:
        """Apply all formatting rules"""
        formatted = agent

        if metrics.time_to_first_example >= 50:
            formatted = self.move_first_example(formatted)

        if metrics.example_density < 40:
            formatted = self.add_example_markers(formatted, metrics.example_density)

        if not all(metrics.boundary_sections.values()):
            formatted = self.add_boundary_sections(formatted, metrics.boundary_sections)

        if metrics.commands_first >= 50:
            formatted = self.add_quick_start(formatted)

        if metrics.code_to_text_ratio < 1.0:
            formatted = self.add_ratio_markers(formatted, metrics.code_to_text_ratio)

        return formatted

    def move_first_example(self, agent: AgentStructure) -> AgentStructure:
        """Move first code example to lines 21-50"""
        # Implementation details...

    def add_example_markers(self, agent: AgentStructure, current_density: float) -> AgentStructure:
        """Add markers indicating where examples needed"""
        target_density = 40.0
        total_lines = sum(s.end_line - s.start_line for s in agent.sections)
        current_code_lines = int(total_lines * current_density / 100)
        needed_code_lines = int(total_lines * target_density / 100) - current_code_lines

        marker = f"[NEEDS_CONTENT: Add ~{needed_code_lines} lines of code examples to reach 40% density (currently {current_density:.1f}%)]"
        # Insert marker after first section
        # Implementation details...

    def add_boundary_sections(self, agent: AgentStructure, existing: dict[str, bool]) -> AgentStructure:
        """Add missing ALWAYS/NEVER/ASK sections"""
        # Implementation details...
```

### Phase 4: Validator (0.5 hours)

**Purpose**: Validate changes preserve content and improve quality

```python
class FormatValidator:
    def validate(self, original: AgentStructure, formatted: AgentStructure) -> ValidationResult:
        """Validate formatting changes"""
        issues = []

        # Check content preservation
        if not self.content_preserved(original, formatted):
            issues.append("CRITICAL: Content was lost during formatting")

        # Check metrics improved
        original_metrics = calculate_metrics(original)
        new_metrics = calculate_metrics(formatted)

        if new_metrics.get_status() == original_metrics.get_status():
            issues.append("WARNING: Quality status did not improve")

        return ValidationResult(
            success=len([i for i in issues if 'CRITICAL' in i]) == 0,
            issues=issues,
            metrics_before=original_metrics,
            metrics_after=new_metrics
        )

    def content_preserved(self, original: AgentStructure, formatted: AgentStructure) -> bool:
        """Check no content was lost"""
        # Extract all text content (ignoring whitespace/formatting)
        original_text = self.extract_content(original)
        formatted_text = self.extract_content(formatted)

        # Allow added markers, but no removal
        return all(text in formatted_text for text in original_text)
```

### Phase 5: Reporter (0.5 hours)

**Purpose**: Generate validation reports

```python
class ValidationReporter:
    def generate_report(self, validation: ValidationResult, agent_path: Path) -> str:
        """Generate markdown validation report"""
        status_icon = {
            "PASS": "✅",
            "WARN": "⚠️",
            "FAIL": "❌"
        }

        before_status = validation.metrics_before.get_status()
        after_status = validation.metrics_after.get_status()

        report = f"""
# Agent Formatting Report

**Agent**: {agent_path.name}
**Status**: {status_icon[before_status]} {before_status} → {status_icon[after_status]} {after_status}

## Quality Metrics

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Time to First Example | {validation.metrics_before.time_to_first_example} lines | {validation.metrics_after.time_to_first_example} lines | {status_icon[after_status if validation.metrics_after.time_to_first_example < 50 else "FAIL"]} |
| Example Density | {validation.metrics_before.example_density:.1f}% | {validation.metrics_after.example_density:.1f}% | {status_icon["PASS" if validation.metrics_after.example_density >= 40 else "WARN"]} |
| Boundary Sections | {sum(validation.metrics_before.boundary_sections.values())}/3 | {sum(validation.metrics_after.boundary_sections.values())}/3 | {status_icon["PASS" if all(validation.metrics_after.boundary_sections.values()) else "FAIL"]} |
| Commands First | {validation.metrics_before.commands_first} lines | {validation.metrics_after.commands_first} lines | {status_icon["PASS" if validation.metrics_after.commands_first < 50 else "FAIL"]} |
| Code-to-Text Ratio | {validation.metrics_before.code_to_text_ratio:.2f}:1 | {validation.metrics_after.code_to_text_ratio:.2f}:1 | {status_icon["PASS" if validation.metrics_after.code_to_text_ratio >= 1.0 else "WARN"]} |
| Specificity Score | {validation.metrics_before.specificity_score}/10 | {validation.metrics_after.specificity_score}/10 | {status_icon["PASS" if validation.metrics_after.specificity_score >= 8 else "FAIL"]} |

## Issues

{chr(10).join(f"- {issue}" for issue in validation.issues) if validation.issues else "No issues found"}

## Recommendations

{self.generate_recommendations(validation.metrics_after)}
"""
        return report
```

### Phase 6: CLI Integration (1 hour)

**Purpose**: Command-line interface

```python
#!/usr/bin/env python3
"""
/agent-format Command - Format agents with GitHub best practices
"""

import sys
import argparse
from pathlib import Path
from glob import glob

from installer.global.lib.agent_formatting import (
    parse_agent,
    calculate_metrics,
    AgentFormatter,
    FormatValidator,
    ValidationReporter
)

def main(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-format",
        description="Format agent documentation with GitHub best practices"
    )
    parser.add_argument("path", help="Agent file or glob pattern")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--backup", action="store_true", default=True)
    parser.add_argument("--verbose", action="store_true")

    parsed_args = parser.parse_args(args)

    # Resolve paths
    paths = resolve_paths(parsed_args.path)
    if not paths:
        print(f"❌ No agents found matching: {parsed_args.path}")
        return 1

    # Process each agent
    results = []
    for path in paths:
        result = process_agent(path, parsed_args)
        results.append(result)

    # Summary
    print_summary(results)

    return 0 if all(r.success for r in results) else 1
```

---

## Acceptance Criteria

### Functional Requirements

- [ ] **AC1**: Command accepts single file path
- [ ] **AC2**: Command accepts glob pattern (e.g., `*.md`)
- [ ] **AC3**: Command accepts directory path (formats all .md files)
- [ ] **AC4**: `--dry-run` shows preview without applying changes
- [ ] **AC5**: `--report` generates detailed markdown validation report
- [ ] **AC6**: `--validate-only` checks quality without formatting
- [ ] **AC7**: `--backup` creates `.bak` backup before formatting (default: true)
- [ ] **AC8**: `--verbose` shows detailed progress
- [ ] **AC9**: Exit code 0 on success, 1 on error

### Quality Requirements

- [ ] **AC10**: ≥80% of formatted agents achieve PASS status
- [ ] **AC11**: ≥95% of formatted agents achieve PASS or WARN status
- [ ] **AC12**: 0% content loss (all original content preserved)
- [ ] **AC13**: All transformations add only `[NEEDS_CONTENT]` markers or reorganize existing content
- [ ] **AC14**: Formatting is idempotent (formatting twice yields same result)

### Performance Requirements

- [ ] **AC15**: Single agent formatted in <30 seconds
- [ ] **AC16**: 15 global agents formatted in <15 minutes
- [ ] **AC17**: 25 total agents formatted in <25 minutes
- [ ] **AC18**: Memory usage <500MB for batch operations

### Validation Requirements

- [ ] **AC19**: Before/after metrics calculated for all agents
- [ ] **AC20**: Validation report includes all 6 quality metrics
- [ ] **AC21**: Status correctly classified as PASS/WARN/FAIL
- [ ] **AC22**: Content preservation validated (no data loss)

### Error Handling Requirements

- [ ] **AC23**: Graceful handling of malformed agent files
- [ ] **AC24**: Clear error messages for missing files
- [ ] **AC25**: Automatic rollback on formatting errors
- [ ] **AC26**: Backup restoration on failure

---

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

---

## Exit Codes

- `0` - Success (all agents formatted successfully)
- `1` - File not found
- `2` - Permission error
- `3` - Formatting error (content would be lost)
- `4` - Validation error (quality metrics failed)

---

## Output Examples

### Success Output

```
✅ Formatted architectural-reviewer.md

Validation Report:
  time_to_first_example: 28 lines ✅ (was 150)
  example_density: 42% ✅ (was 25%)
  boundary_sections: ALWAYS ✅, NEVER ✅, ASK ✅ (was 0/3)
  commands_first: 22 lines ✅ (was -1)
  code_to_text_ratio: 1.2:1 ✅ (was 0.6:1)
  specificity_score: 9/10 ✅ (unchanged)

Overall Status: PASS ✅ (was FAIL)

Changes applied:
  + Moved first example to line 28
  + Added ALWAYS/NEVER/ASK boundary sections
  + Added Quick Start section with command example
  + Added 3 code example markers for density improvement

Backup: architectural-reviewer.md.bak
```

### Batch Output

```
Processing 15 agents...

[1/15] ✅ architectural-reviewer.md (FAIL → PASS)
[2/15] ✅ task-manager.md (WARN → PASS)
[3/15] ✅ code-reviewer.md (FAIL → WARN)
[4/15] ✅ test-verifier.md (FAIL → PASS)
...
[15/15] ✅ software-architect.md (WARN → PASS)

Summary:
  Total: 15 agents
  PASS: 12 (80%)
  WARN: 3 (20%)
  FAIL: 0 (0%)

  Time: 12.5 minutes
  Avg: 50 seconds/agent

All agents formatted successfully! ✅
```

### Dry-Run Output

```
[DRY RUN] architectural-reviewer.md

Proposed Changes:
  - Move first example from line 150 to line 28
  - Add ALWAYS section after Quick Start (5 rules needed)
  - Add NEVER section after ALWAYS (5 rules needed)
  - Add ASK section after NEVER (3 scenarios needed)
  - Add Quick Start section with command example
  - Add 3 [NEEDS_CONTENT] markers for density improvement

Quality Impact:
  time_to_first_example: 150 → 28 lines ✅
  example_density: 25% → 30% ⚠️
  boundary_sections: 0/3 → 3/3 ✅
  commands_first: -1 → 22 lines ✅
  code_to_text_ratio: 0.6 → 0.8 ⚠️
  specificity_score: 9/10 → 9/10 ✅

Overall Status: FAIL → WARN

[DRY RUN] No changes applied
```

### Validation-Only Output

```
[VALIDATE ONLY] architectural-reviewer.md

Current Quality Metrics:
  time_to_first_example: 150 lines ❌ (target: <50)
  example_density: 25% ❌ (target: ≥40%)
  boundary_sections: 0/3 ❌ (missing: ALWAYS, NEVER, ASK)
  commands_first: -1 ❌ (no command examples found)
  code_to_text_ratio: 0.6:1 ⚠️ (target: ≥1:1)
  specificity_score: 9/10 ✅

Overall Status: FAIL ❌

Recommendations:
  1. Add Quick Start section with command example (fixes 2 issues)
  2. Move first code example to lines 21-50 (fixes 1 issue)
  3. Add ALWAYS/NEVER/ASK boundary sections (fixes 1 issue)
  4. Add 15-20 more code examples to reach 40% density
  5. Add more code snippets to improve code-to-text ratio

Run without --validate-only to apply formatting.
```

---

## Implementation Estimate

**Total**: 4-6 hours

- **Phase 1**: Parser (1 hour)
- **Phase 2**: Metrics (1 hour)
- **Phase 3**: Transformers (2 hours)
- **Phase 4**: Validator (0.5 hours)
- **Phase 5**: Reporter (0.5 hours)
- **Phase 6**: CLI Integration (1 hour)
- **Testing**: Included in each phase

---

## Success Metrics

**Time Savings**:
- Manual enhancement: 20-35 hours
- Automated formatting: <25 minutes
- **ROI**: 50-80x faster

**Quality Improvement**:
- Baseline: 15 global agents need formatting
- Target: ≥80% achieve PASS status (12+ agents)
- Stretch: ≥95% achieve PASS or WARN (14+ agents)

**User Value**:
- Developers can format their own agents instantly
- Consistent quality across all agents
- Immediate feedback on quality metrics
- No manual effort required

---

## File Locations

**Implementation**:
- `installer/global/commands/agent-format.md` - Command specification
- `installer/global/commands/agent-format.py` - Command entry point
- `installer/global/lib/agent_formatting/` - Core library

**Tests**:
- `tests/unit/lib/agent_formatting/` - Unit tests
- `tests/integration/test_agent_format_command.py` - Integration tests

**Documentation**:
- `docs/commands/agent-format.md` - User guide
- `docs/guides/agent-formatting-best-practices.md` - Best practices

---

## References

- **GitHub Research**: `docs/analysis/github-agent-best-practices-analysis.md`
- **Agent Content Enhancer**: `installer/global/agents/agent-content-enhancer.md` (lines 32-175)
- **Template Creation**: `/template-create` workflow documentation
- **Agent Enhancement**: `/agent-enhance` command specification

---

**Status**: Ready for implementation
**Priority**: High
**Complexity**: 6/10 (Medium)
**Estimated Effort**: 4-6 hours
**Expected ROI**: 50-80x time savings (20-35 hours → 25 minutes)
