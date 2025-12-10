# Template Validation Workflows

Common workflow patterns for template validation in different scenarios.

## Workflow 1: Quick Personal Template

**Scenario**: Creating a template for personal use

**Steps**:
```bash
# 1. Create template (automatic validation only)
/template-create

# 2. Verify it works
guardkit init my-template

# 3. Use immediately
```

**Validation Level**: 1 (Automatic)
**Duration**: ~30 seconds
**Template Location**: `~/.agentecflow/templates/`

---

## Workflow 2: Team Template Before Sharing

**Scenario**: Creating a template to share with your team

**Steps**:
```bash
# 1. Create template with extended validation
/template-create --validate --output-location=repo

# 2. Review validation report
cat installer/core/templates/my-template/validation-report.md

# 3. If score ≥8/10, share with team
# 4. If score <8/10, fix issues and re-validate
```

**Validation Level**: 2 (Extended)
**Duration**: 2-5 minutes
**Template Location**: `installer/core/templates/`

---

## Workflow 3: Production Template Deployment

**Scenario**: Deploying a template for global use

**Steps**:
```bash
# 1. Create template with extended validation
/template-create --validate --output-location=repo

# 2. Run comprehensive audit
/template-validate installer/core/templates/my-template

# 3. Review audit report
cat installer/core/templates/my-template/audit-report.md

# 4. Fix any critical issues
# 5. Re-run comprehensive audit
/template-validate installer/core/templates/my-template

# 6. Deploy if all checks pass
```

**Validation Level**: 3 (Comprehensive)
**Duration**: 30-60 minutes (with AI)
**Template Location**: `installer/core/templates/`

---

## Workflow 4: CI/CD Integration

**Scenario**: Automated template validation in CI/CD pipeline

**GitHub Actions Example**:
```yaml
name: Template Validation

on:
  pull_request:
    paths:
      - 'installer/core/templates/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install GuardKit
        run: |
          chmod +x installer/scripts/install.sh
          ./installer/scripts/install.sh

      - name: Run Template Validation
        run: |
          /template-create --validate --output-location=repo
          EXIT_CODE=$?

          if [ $EXIT_CODE -eq 0 ]; then
            echo "✅ Template passed validation (≥8/10)"
          elif [ $EXIT_CODE -eq 1 ]; then
            echo "⚠️ Template needs improvement (6-7.9/10)"
            exit 1
          else
            echo "❌ Template failed validation (<6/10)"
            exit 1
          fi

      - name: Upload Validation Report
        uses: actions/upload-artifact@v3
        with:
          name: validation-report
          path: installer/core/templates/*/validation-report.md
```

**Validation Level**: 2 (Extended)
**Duration**: 2-5 minutes
**Template Location**: `installer/core/templates/`

---

## Workflow 5: Troubleshooting Low Scores

**Scenario**: Template scores low (<6/10) and needs improvement

**Steps**:
```bash
# 1. Create template with validation
/template-create --validate

# Score: 5.2/10 ❌

# 2. Review validation report for issues
cat ~/.agentecflow/templates/my-template/validation-report.md

# 3. Run comprehensive audit for deeper analysis
/template-validate ~/.agentecflow/templates/my-template

# 4. Focus on sections with issues
/template-validate ~/.agentecflow/templates/my-template --sections 4,8,11

# 5. Fix issues based on recommendations

# 6. Re-create template with validation
/template-create --validate

# Score: 8.5/10 ✅
```

**Validation Level**: 2 + 3 (Extended + Comprehensive)
**Duration**: 1-2 hours
**Template Location**: `~/.agentecflow/templates/` or `installer/core/templates/`

---

## Workflow 6: Iterative Improvement

**Scenario**: Gradually improving template quality

**Iteration 1**: Basic validation
```bash
/template-create
# Quality Score: 7.1/10
```

**Iteration 2**: Extended validation
```bash
/template-create --validate
# Quality Score: 7.1/10
# Review report, fix placeholder issues
```

**Iteration 3**: Comprehensive audit
```bash
/template-validate ~/.agentecflow/templates/my-template --sections 8,11,12
# AI identifies pattern fidelity issues
# Fix patterns based on recommendations
```

**Iteration 4**: Final validation
```bash
/template-create --validate
# Quality Score: 9.2/10 ✅
```

**Validation Level**: 1 → 2 → 3 → 2
**Duration**: 2-3 hours total
**Template Location**: `~/.agentecflow/templates/`

---

## Workflow 7: Selective Section Audit

**Scenario**: Only need to validate specific aspects of template

**Documentation Only**:
```bash
/template-validate <template-path> --sections 3,6
# Sections 3: Documentation Analysis
# Section 6: README Review
```

**Technical Validation Only**:
```bash
/template-validate <template-path> --sections 1-7
# All technical validation sections
```

**AI-Assisted Quality Assessment**:
```bash
/template-validate <template-path> --sections 8,11,12,13
# All AI-assisted sections
```

**Decision Framework Only**:
```bash
/template-validate <template-path> --sections 14-16
# Final recommendations and summary
```

**Validation Level**: 3 (Comprehensive - selective)
**Duration**: 10-30 minutes per section group
**Template Location**: Either personal or repository

---

## Workflow 8: Resume Previous Audit

**Scenario**: Continue a previous comprehensive audit

**Day 1**: Start audit
```bash
/template-validate ~/.agentecflow/templates/my-template
# Complete sections 1-7
# Session ID: audit-20250108-143022
```

**Day 2**: Resume audit
```bash
/template-validate ~/.agentecflow/templates/my-template --resume audit-20250108-143022
# Continue from section 8
```

**Validation Level**: 3 (Comprehensive)
**Duration**: Split across multiple sessions
**Template Location**: Either personal or repository

---

## Workflow 9: Pre-Release Checklist

**Scenario**: Final validation before releasing template

**Checklist**:
```bash
# 1. Run extended validation
/template-create --validate --output-location=repo
✅ Score ≥8/10

# 2. Run comprehensive audit
/template-validate installer/core/templates/my-template
✅ All sections reviewed

# 3. Verify template works
guardkit init my-template
cd my-template-test
✅ Template initializes successfully

# 4. Run template tests (if applicable)
npm test  # or pytest, dotnet test, etc.
✅ All tests pass

# 5. Review documentation
cat installer/core/templates/my-template/README.md
✅ Documentation complete and accurate

# 6. Check for security issues
grep -r "password\|secret\|token" installer/core/templates/my-template/
✅ No hardcoded secrets

# 7. Verify agent references
grep -r "@agent" installer/core/templates/my-template/
✅ All agents exist

# 8. Review audit report
cat installer/core/templates/my-template/audit-report.md
✅ No critical issues

# 9. Ready for release!
```

**Validation Level**: 2 + 3 + Manual checks
**Duration**: 1-2 hours
**Template Location**: `installer/core/templates/`

---

## Workflow 10: Comparing Templates

**Scenario**: Evaluating multiple template options

**Steps**:
```bash
# 1. Create both templates with validation
/template-create --validate # Template A
/template-create --validate # Template B

# 2. Compare validation reports
diff -u template-a/validation-report.md template-b/validation-report.md

# 3. Run comprehensive audits
/template-validate ~/.agentecflow/templates/template-a
/template-validate ~/.agentecflow/templates/template-b

# 4. Compare audit reports
diff -u template-a/audit-report.md template-b/audit-report.md

# 5. Choose template with higher quality score or better fit
```

**Validation Level**: 2 + 3 (for both templates)
**Duration**: 2-3 hours total
**Template Location**: `~/.agentecflow/templates/`

---

## Best Practices

### For Personal Templates
- ✅ Use Level 1 (automatic) for quick prototyping
- ✅ Use Level 2 (extended) before sharing with others
- ✅ Location: `~/.agentecflow/templates/`

### For Team Templates
- ✅ Always use Level 2 (extended) minimum
- ✅ Generate quality reports for stakeholders
- ✅ Use `--output-location=repo` flag
- ✅ Location: `installer/core/templates/`

### For Production Templates
- ✅ Use Level 3 (comprehensive) for thorough validation
- ✅ Review all 16 sections
- ✅ Fix all critical issues
- ✅ Achieve ≥8/10 quality score
- ✅ Location: `installer/core/templates/`

### For CI/CD
- ✅ Use Level 2 (extended) for automation
- ✅ Check exit codes to fail pipeline on low scores
- ✅ Archive validation reports as artifacts
- ✅ Set minimum quality threshold (e.g., ≥8/10)

## See Also

- [Template Validation Guide](./template-validation-guide.md) - Overview and usage
- [Template Validation AI Assistance](./template-validation-ai-assistance.md) - AI features
- [Template Validation Strategy](../research/template-validation-strategy.md) - Design decisions
