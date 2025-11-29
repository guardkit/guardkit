# Template Validation Guide

## Overview

Taskwright provides a 3-level validation system for ensuring template quality:

1. **Level 1 (Automatic)**: Built-in quality gates during template creation
2. **Level 2 (Extended)**: Optional detailed validation with reports
3. **Level 3 (Comprehensive)**: Interactive 16-section audit

## Level 1: Automatic Validation

### What It Does

Runs automatically during `/template-create` as Phase 5.5:
- ✅ CRUD completeness (Create/Read/Update/Delete/List)
- ✅ Layer symmetry (UseCases ↔ Web ↔ Infrastructure)
- ✅ File count validation
- ✅ Supporting files presence
- ✅ Auto-fix common issues

### How to Use

No action required - runs automatically:
```bash
/template-create
# → Phase 5.5 validates and auto-fixes
```

### Output

Console output during template creation:
```
✓ Validating templates (26/26, 0 issues auto-fixed)
Quality Score: 9.2/10
```

## Level 2: Extended Validation

### What It Does

Optional `--validate` flag adds:
- ✅ All Level 1 checks
- ✅ Placeholder consistency validation
- ✅ Pattern fidelity spot-checks (5 files)
- ✅ Documentation completeness
- ✅ Agent reference validation
- ✅ Detailed markdown report

### How to Use

```bash
# Personal templates (default: ~/.agentecflow/templates/)
/template-create --validate

# Repository templates (installer/global/templates/)
/template-create --validate --output-location=repo

# Dry run with validation
/template-create --dry-run --validate
```

### Output

**Console Summary**:
```
✓ Extended validation complete (9.2/10)
Report: ./templates/my-template/validation-report.md
```

**Report File** (`validation-report.md`):
- Executive summary
- Quality scores by category
- Detailed findings
- Actionable recommendations
- Production readiness assessment

### Exit Codes

- `0`: Score ≥8/10 (Production ready)
- `1`: Score 6-7.9/10 (Needs improvement)
- `2`: Score <6/10 (Not ready)

**CI/CD Integration**:
```bash
/template-create --validate || exit 1
```

## Level 3: Comprehensive Audit

### What It Does

Interactive 16-section audit command:
- ✅ Systematic validation framework
- ✅ Section selection (1-16)
- ✅ Session save/resume
- ✅ Inline issue fixes
- ✅ AI-assisted analysis
- ✅ Comprehensive audit report
- ✅ Decision framework

### How to Use

```bash
# Personal templates
/template-validate ~/.agentecflow/templates/my-template

# Repository templates
/template-validate installer/global/templates/react-typescript

# Specific sections
/template-validate <template-path> --sections 1,4,7

# Section ranges
/template-validate <template-path> --sections 1-7

# Resume previous audit
/template-validate <template-path> --resume <session-id>
```

### 16-Section Framework

**Sections 1-7**: Technical Validation
1. Manifest Analysis
2. Settings Analysis
3. Documentation Analysis
4. Template Files Analysis
5. AI Agents Analysis
6. README Review
7. Global Template Validation

**Sections 8-13**: Quality Assessment
8. Comparison with Source (AI-assisted)
9. Production Readiness
10. Scoring Rubric
11. Detailed Findings (AI-assisted)
12. Validation Testing (AI-assisted)
13. Market Comparison (AI-assisted)

**Sections 14-16**: Decision Framework
14. Final Recommendations
15. Testing Recommendations
16. Summary Report

### Output

**Interactive Workflow**:
```
============================================================
  Template Comprehensive Audit
============================================================

Template: my-template
Location: ./templates/my-template/

Audit Sections:
  [1-7]   Technical Validation
  [8-13]  Quality Assessment
  [14-16] Decision Framework

Run all sections? [Y/n/select]:
```

**Audit Report** (`audit-report.md`):
- Executive summary
- Section scores
- Detailed findings
- Critical issues
- Production readiness decision
- Pre-release checklist

## When to Use Each Level

| Scenario | Level | Why | Template Location |
|----------|-------|-----|-------------------|
| Personal template | 1 (Auto) | Quick, no ceremony | `~/.agentecflow/templates/` |
| Team template | 2 (Extended) | Quality report for stakeholders | `installer/global/templates/` (use `--output-location=repo`) |
| Global deployment | 3 (Comprehensive) | Thorough validation required | `installer/global/templates/` |
| CI/CD integration | 2 (Extended) | Exit codes, reports | `installer/global/templates/` |
| Troubleshooting | 3 (Comprehensive) | Deep analysis needed | Either location |

## Examples

### Quick Personal Template
```bash
# Automatic validation only
/template-create
```

### Team Template with Extended Validation
```bash
# Create in repository location with validation
/template-create --output-location=repo --validate

# Review report
cat installer/global/templates/my-template/validation-report.md
```

### Production Template with Comprehensive Audit
```bash
# Create template
/template-create --output-location=repo

# Run comprehensive audit
/template-validate installer/global/templates/my-template

# Review audit report
cat installer/global/templates/my-template/audit-report.md
```

### CI/CD Integration
```bash
# In CI pipeline
/template-create --validate --output-location=repo

# Check exit code
if [ $? -eq 0 ]; then
  echo "Template passed validation (≥8/10)"
elif [ $? -eq 1 ]; then
  echo "Template needs improvement (6-7.9/10)"
else
  echo "Template failed validation (<6/10)"
  exit 1
fi
```

## FAQ

**Q: Do I need to use `--validate` every time?**

A: No. Level 1 automatic validation runs by default. Use `--validate` when you need a quality report or are preparing to share the template with your team (especially for repository templates created with `--output-location=repo`).

**Q: How long does validation take?**

A:
- Level 1: ~30 seconds (automatic)
- Level 2: 2-5 minutes
- Level 3: 30-60 minutes (with AI), 2-3 hours (manual)

**Q: What's a good quality score?**

A:
- ≥8/10: Production ready
- 6-7.9/10: Usable but needs improvement
- <6/10: Not ready for production

**Q: Can I skip validation?**

A: Level 1 runs automatically. You can skip it with `--skip-validation` but this is not recommended.

**Q: How accurate is AI assistance?**

A: AI achieves ≥85% agreement with expert manual analysis. Always review AI findings.

**Q: Can I use validation in CI/CD?**

A: Yes! Use `--validate` flag and check exit codes:
```bash
/template-create --validate || exit 1
```

**Q: What if my template scores low?**

A: Review the validation report recommendations and use `/template-validate` for deeper analysis.

**Q: Where are templates created by default?**

A: Templates are created in `~/.agentecflow/templates/` by default for immediate personal use. Use `--output-location=repo` flag to create templates in `installer/global/templates/` for team/public distribution.

**Q: Can I validate templates in either location?**

A: Yes! Both `/template-create --validate` and `/template-validate` work with templates in either `~/.agentecflow/templates/` (personal) or `installer/global/templates/` (repository) locations.

## See Also

- [Template Validation Workflows](./template-validation-workflows.md) - Common usage patterns
- [Template Validation AI Assistance](./template-validation-ai-assistance.md) - AI features
- [Template Validation Strategy](../research/template-validation-strategy.md) - Design decisions
