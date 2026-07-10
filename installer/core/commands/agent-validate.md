---
format_version: 1
name: agent-validate
category: Development Tools
summary: Objective quality validation for agent files using GitHub best practices and measurable metrics
---

# Agent Validate - Objective Agent Quality Validation

Provides automated, objective validation of agent markdown files against GitHub best practices and GuardKit quality standards. Generates actionable feedback with measurable metrics and auto-fix suggestions.

## Purpose

**Validation over Documentation**: Unlike guidelines that require human interpretation, this tool provides objective, automated quality assessment with:
- Measurable metrics (0-10 scale)
- Line-level issue detection
- Actionable recommendations with impact estimates
- CI/CD integration support
- Auto-fix capabilities

**Use Cases**:
- Pre-deployment validation of global agents
- Quality assurance during agent development
- CI/CD pipeline integration
- Batch validation of agent libraries
- Regression testing after agent modifications

## Command Interface

### Single Agent Validation

```bash
# Basic validation (console output)
/agent-validate installer/core/agents/code-reviewer.md

# With auto-fix suggestions
/agent-validate code-reviewer.md --suggest-fixes

# JSON output for scripting
/agent-validate code-reviewer.md --format json

# CI/CD integration with threshold
/agent-validate code-reviewer.md --threshold 8.0 --format json --exit-on-fail

# Verbose output with detailed analysis
/agent-validate code-reviewer.md --verbose

# Specific checks only
/agent-validate code-reviewer.md --checks structure,examples,boundaries
```

### Batch Validation

```bash
# Validate all agents in directory
/agent-validate-batch installer/core/agents/

# With quality threshold filter
/agent-validate-batch installer/core/agents/ --threshold 8.0

# Summary table only
/agent-validate-batch installer/core/agents/ --summary

# JSON output for all agents
/agent-validate-batch installer/core/agents/ --format json

# Fail if any agent below threshold
/agent-validate-batch installer/core/agents/ --threshold 8.0 --exit-on-fail
```

### Auto-Enhancement Integration

```bash
# Validate and automatically enhance if below threshold
/agent-validate code-reviewer.md --auto-enhance --threshold 8.5

# This invokes /agent-enhance if score < 8.5
# Re-validates after enhancement
```

## Arguments

### Single Validation (`/agent-validate`)

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `<file-path>` | string | Yes | - | Path to agent markdown file |
| `--format` | enum | No | `console` | Output format: `console`, `json`, `minimal` |
| `--threshold` | float | No | `0.0` | Minimum acceptable score (0.0-10.0) |
| `--exit-on-fail` | flag | No | `false` | Exit code 1 if score below threshold |
| `--suggest-fixes` | flag | No | `false` | Include auto-fix suggestions in output |
| `--auto-enhance` | flag | No | `false` | Auto-invoke `/agent-enhance` if below threshold |
| `--checks` | list | No | `all` | Specific checks to run (comma-separated) |
| `--verbose` | flag | No | `false` | Detailed diagnostic output |
| `--output-file` | string | No | `stdout` | Write report to file instead of stdout |

### Batch Validation (`/agent-validate-batch`)

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `<directory>` | string | Yes | - | Directory containing agent files |
| `--format` | enum | No | `table` | Output format: `table`, `json`, `csv` |
| `--threshold` | float | No | `0.0` | Filter agents below threshold |
| `--exit-on-fail` | flag | No | `false` | Exit code 1 if any agent below threshold |
| `--summary` | flag | No | `false` | Summary table only (no detailed reports) |
| `--recursive` | flag | No | `true` | Recursively search subdirectories |
| `--output-file` | string | No | `stdout` | Write report to file |

## Validation Framework

### Check Categories

Six primary quality checks, based on GitHub analysis of 2,500+ repositories:

1. **Structure Validation** (Weight: 15%)
2. **Example Density** (Weight: 25%)
3. **Boundary Clarity** (Weight: 20%)
4. **Specificity** (Weight: 20%)
5. **Code Example Quality** (Weight: 15%)
6. **Maintenance Indicators** (Weight: 5%)

### Overall Score Calculation

```python
overall_score = (
    (structure_score * 0.15) +
    (example_density_score * 0.25) +
    (boundary_clarity_score * 0.20) +
    (specificity_score * 0.20) +
    (code_quality_score * 0.15) +
    (maintenance_score * 0.05)
)
```

**Score Interpretation**:
- **9.0-10.0**: Excellent - Production ready, exemplary quality
- **8.0-8.9**: Good - Production ready with minor improvements
- **7.0-7.9**: Acceptable - Production ready with recommendations
- **6.0-6.9**: Below Standard - Needs improvement before production
- **5.0-5.9**: Poor - Significant issues, major work required
- **0.0-4.9**: Unacceptable - Critical issues, not production ready


## Output Formats (Summary)

- **console** (default): human-readable report — overall score, per-category
  scores with weights, prioritized recommendations with impact/time estimates.
- **json**: machine-readable (`--format json`) — `overall_score`, per-category
  blocks, issues with line numbers, recommendations; for scripting/CI.
- **minimal**: one line per agent (`--format minimal`) — CI/CD pass-fail use.

Full format examples and JSON schema: `agent-validate-ext.md` § Output Formats.

## Exit Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 0 | Success | Validation completed, score ≥ threshold |
| 1 | Failure | Score < threshold (when `--exit-on-fail` used) |
| 2 | Invalid Arguments | Missing required arguments, invalid file path |
| 3 | File Not Found | Agent file doesn't exist |
| 4 | Parse Error | Cannot parse YAML frontmatter or markdown |


## Integration Points (Summary)

- **`/agent-enhance`** — validate → enhance if below threshold → re-validate
  (`--auto-enhance` wires this automatically).
- **`/template-create` Phase 7** — generated agents are validated; scores land in
  the template report.
- **CI/CD** — `--threshold N` + exit codes below; minimal format for pipelines.

Detail + workflow YAML: `agent-validate-ext.md` § Integration Points.

## Reference Slices (load on demand)

Extended documentation: `agent-validate-ext.md` (same directory — K13 core/`-ext`
shape). Read the section you need:

| Need | Ext section |
|---|---|
| Scoring rubrics + algorithm listings per check category | Validation Algorithms |
| Full console/JSON/minimal output examples | Output Formats |
| Module structure, core classes, dependencies, performance | Implementation Architecture |
| Integration workflows (agent-enhance, template-create, CI) | Integration Points |
| Malformed/edge-case input handling | Edge Cases |
| Test fixtures + unit/integration/regression suites | Testing Strategy |
| CLI entry points (single + batch) | CLI Interface |
| Design summary | Summary |
