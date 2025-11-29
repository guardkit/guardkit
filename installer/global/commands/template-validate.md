---
name: template-validate
category: Development Tools
summary: Comprehensive interactive template audit using 16-section validation framework
---

# Template Validate - Comprehensive Template Audit

Performs interactive comprehensive audit of template packages using the 16-section validation framework from [template-analysis-task.md](../../docs/testing/template-analysis-task.md).

## Purpose

Systematic quality validation for:
- Production templates (global library deployment)
- Critical deployments
- Development testing of template-create feature
- Troubleshooting template quality issues

## Usage

```bash
# Full audit (all sections)
/template-validate <template-path>

# Validate personal template (in global location)
/template-validate ~/.agentecflow/templates/my-template

# Validate repository template (for distribution)
/template-validate installer/global/templates/react-typescript

# Specific sections only
/template-validate <template-path> --sections 1,4,7,12

# Section ranges
/template-validate <template-path> --sections 1-7

# Resume previous audit
/template-validate <template-path> --resume <session-id>

# Non-interactive mode (batch processing)
/template-validate <template-path> --non-interactive

# Auto-fix issues (where possible)
/template-validate <template-path> --auto-fix

# Verbose output
/template-validate <template-path> --verbose
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<template-path>` | Yes | Path to template directory to validate |
| `--sections` | No | Comma-separated or range of section numbers (e.g., `1,4,7` or `1-7`) |
| `--resume` | No | Resume previous audit session by session ID |
| `--non-interactive` | No | Run in batch mode without prompts |
| `--auto-fix` | No | Automatically apply fixes where possible |
| `--verbose` | No | Enable verbose output |
| `--output-dir` | No | Custom output directory for reports (default: template directory) |

## 16-Section Framework

### Sections 1-7: Technical Validation
1. **Manifest Analysis** - Template metadata, placeholders, quality scores
2. **Settings Analysis** - Naming conventions, layer mappings, code style
3. **Documentation Analysis** - CLAUDE.md architecture, patterns, examples
4. **Template Files Analysis** - File selection quality, placeholder integration
5. **AI Agents Analysis** - Agent relevance, prompt quality, capabilities
6. **README Review** - Content completeness, usability, accuracy
7. **Global Template Validation** - Installation test, discovery, structure

### Sections 8-13: Quality Assessment
8. **Comparison with Source** - Pattern coverage, false positives/negatives
9. **Production Readiness** - Developer experience, pattern enforcement, learning curve
10. **Scoring Rubric** - Overall quality score, grade assignment
11. **Detailed Findings** - Strengths, weaknesses, critical issues
12. **Validation Testing** - Placeholder replacement, agent integration, cross-references
13. **Market Comparison** - Comparison with other templates (optional for MVP)

### Sections 14-16: Decision Framework
14. **Final Recommendations** - Release decision, pre-release checklist
15. **Testing Recommendations** - Next steps for testing, generalization assessment
16. **Summary Report** - Executive summary, key metrics, sign-off

## Reports Generated

After audit completion, the following files are created in the template directory (or specified output directory):

1. **audit-report.md** - Comprehensive audit report with all findings
2. **audit-session-{session-id}.json** - Session data for resume capability
3. **audit-fixes.log** - Log of inline fixes applied (if --auto-fix used)

## Quality Thresholds

| Score | Grade | Recommendation | Description |
|-------|-------|----------------|-------------|
| 9.5-10.0 | A+ | APPROVE | Excellent quality, production ready |
| 9.0-9.4 | A | APPROVE | High quality, production ready |
| 8.5-8.9 | A- | APPROVE | Good quality, production ready |
| 8.0-8.4 | B+ | APPROVE | Above average, production ready |
| 7.0-7.9 | B | NEEDS_IMPROVEMENT | Acceptable with minor improvements |
| 6.0-6.9 | C | NEEDS_IMPROVEMENT | Below standard, needs work |
| 5.0-5.9 | D | REJECT | Poor quality, significant issues |
| 0.0-4.9 | F | REJECT | Unacceptable quality |

## Example Workflows

### Full Comprehensive Audit

```bash
/template-validate ./installer/global/templates/ardalis-clean-architecture

# Interactive walkthrough of all 16 sections
# User navigates section by section
# Report generated at end
```

### Quick Technical Validation

```bash
/template-validate ./templates/my-template --sections 1-7

# Only validates technical sections (1-7)
# Faster validation for development
```

### Batch Processing

```bash
/template-validate ./templates/my-template --non-interactive --sections 1-13

# Runs without user interaction
# Useful for CI/CD pipelines
```

### Resume Previous Audit

```bash
/template-validate ./templates/my-template --resume abc12345

# Continues from where you left off
# Session state preserved
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Audit completed successfully (score ≥ 8.0) |
| 1 | Audit completed with issues (score 6.0-7.9) |
| 2 | Audit failed (score < 6.0) |
| 3 | Error during audit execution |

## Session Management

### Saving Sessions

Sessions are automatically saved after each completed section to:
```
{template-path}/audit-session-{session-id}.json
```

### Resuming Sessions

To resume a previous audit:
```bash
/template-validate <template-path> --resume {session-id}
```

### Finding Sessions

To list available sessions:
```bash
ls {template-path}/audit-session-*.json
```

## Integration with Other Commands

### After Template Creation

```bash
# Create template
/template-create source-project/ output-template/ --validate

# Comprehensive validation
/template-validate output-template/
```

### Before Template Deployment

```bash
# Validate before copying to global location
/template-validate ~/.agentecflow/templates/my-template

# If APPROVED, deploy
cp -r my-template installer/global/templates/
```

## Template Location Support

The command works with templates in two locations:

1. **Personal Templates** (default, immediate use):
   ```
   ~/.agentecflow/templates/
   ```

2. **Repository Templates** (team/public distribution):
   ```
   installer/global/templates/
   ```

Both locations follow the same validation criteria.

## Best Practices

1. **Start Simple**: Begin with technical validation (sections 1-7)
2. **Iterate**: Run quality assessment (8-13) after fixes
3. **Full Audit**: Complete all 16 sections before production release
4. **Resume Often**: Use session save/resume for large audits
5. **Auto-Fix**: Enable --auto-fix for quick iteration
6. **Verbose Mode**: Use --verbose for debugging validation issues

## Related Commands

- `/template-create` - Create templates from source code (includes basic validation)
- `/agentic-init` - Initialize projects using validated templates
- `/debug` - Troubleshoot validation issues

## Dependencies

- Python 3.8+
- Existing template validation infrastructure (TASK-040, TASK-043)
- Template structure with manifest.json

## Known Limitations

- Section 13 (Market Comparison) is optional and deferred for MVP
- Auto-fix capability limited to specific issue types
- Some sections require manual assessment (e.g., Section 8, 9)

## Future Enhancements (TASK-045)

- AI-assisted analysis for sections 8, 11, 12, 13
- Automatic source comparison
- Pattern detection improvements
- Market comparison database

---

## Command Execution

```bash
# Execute via symlinked Python script
python3 ~/.agentecflow/bin/template-validate-cli "$@"
```

**Note**: This command uses the CLI pattern with the entry point in `lib/template_validate_cli.py`. The symlink name uses hyphens for consistency with command naming conventions.

---

**Related Documents:**
- [Template Validation Strategy](../../docs/research/template-validation-strategy.md)
- [Template Analysis Task](../../docs/testing/template-analysis-task.md)
- [Template Quality Validation Guide](../../docs/guides/template-quality-validation.md)

**Version**: 1.0.0
**Created**: 2025-01-08
**Phase**: 2 (Template Validation Strategy - TASK-044)
