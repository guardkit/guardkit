# Manual Testing Checklist for EPIC-001 Template Creation

## Overview

This checklist guides you through testing `/template-create` on each repository **individually** with fresh Claude Code sessions to avoid context pollution.

## Important Constraints

- ✅ **One repo per Claude Code session** - Clear context between tests
- ✅ **Manual execution** - `/template-create` is a slash command, not automatable
- ✅ **Record as you go** - Document results immediately
- ✅ **Fresh start** - Reload Claude Code window between repos

## Pre-Test Setup

1. Clone all repositories:
   ```bash
   cd ~/guardkit-testing
   ./docs/testing/clone-test-repos.sh
   mkdir -p results
   ```

2. Create results template files (one per repo)

## Testing Workflow Per Repository

### Before Each Test

1. **Reload Claude Code window**:
   - Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux)
   - Type "Developer: Reload Window"
   - Wait for reload to complete

2. **Navigate to test repo**:
   ```bash
   cd ~/guardkit-testing/test-repos/[repo-name]
   ```

3. **Open results file** in editor for notes

### Run Test

In Claude Code, execute:

```bash
/template-create --skip-qa --dry-run
```

**Flags explained**:
- `--skip-qa` - Skip interactive questions (faster testing)
- `--dry-run` - Analyze but don't save files (non-destructive)

### Capture Output

Copy the entire output and paste into `results/[repo-name]-analysis.txt`

### Record Results

Fill out the test template (see below) in `results/[repo-name]-report.md`

### After Each Test

1. **Save results** to both files
2. **Reload Claude Code** before next test
3. **Take a break** if needed (testing fatigue is real!)

## Test Checklist

Track your progress:

```markdown
## Phase 1: Small Repositories (Start Here)
- [ ] go-clean-architecture
- [ ] bulletproof-react

## Phase 2: Medium Complexity
- [ ] full-stack-fastapi-template
- [ ] CleanArchitecture-ardalis
- [ ] go-rest-api

## Phase 3: Complex/Multi-Stack
- [ ] CleanArchitecture-jasontaylor
- [ ] Go-Clean-Architecture-REST-API
- [ ] actix-examples
- [ ] rocket (examples directory)
- [ ] Practical.CleanArchitecture (optional - very large)

## Phase 4: Microservices
- [ ] eShop
```

## Test Data Collection Template

For each repository, create: `results/[repo-name]-report.md`

```markdown
# Test Report: [Repository Name]

**Date**: [YYYY-MM-DD]
**Tester**: [Your Name]
**Session**: [Fresh/Continued]
**Command**: `/template-create --skip-qa --dry-run`

---

## 1. Detection Results

### Primary Stack
- **Language**: [Detected]
  - Actual: [Actual]
  - Correct: ✓ / ✗
  - Confidence: [%]

- **Framework(s)**: [Detected]
  - Actual: [Actual]
  - Correct: ✓ / ✗

- **Language Version**: [Detected]
  - Actual: [Actual]
  - Correct: ✓ / ✗

### Architecture
- **Pattern**: [Detected]
  - Actual: [Actual]
  - Correct: ✓ / ✗
  - Confidence: [%]

- **Layers**: [Detected]
  - Actual: [Actual]
  - Correct: ✓ / ✗

- **Patterns**: [List detected patterns]
  - Correct: [Which ones are right]
  - Missed: [Which ones were missed]
  - False Positives: [Which ones are wrong]

### Infrastructure
- **Database**: [Detected] (✓/✗)
- **Cache**: [Detected] (✓/✗)
- **Testing Framework**: [Detected] (✓/✗)
- **Build Tool**: [Detected] (✓/✗)
- **Container**: [Detected] (✓/✗)

### Example Files Selected
- File 1: [path] - Quality: [Good/Fair/Poor]
- File 2: [path] - Quality: [Good/Fair/Poor]
- File 3: [path] - Quality: [Good/Fair/Poor]
- [etc.]

**Selection Quality**: [Excellent/Good/Fair/Poor]
**Reasoning**: [Why were these good/bad choices?]

---

## 2. Template Generation Plan

### Would Generate
- **manifest.json**: [Yes/No]
- **settings.json**: [Yes/No]
- **CLAUDE.md**: [Yes/No]
- **Template Files**: [Number] files
- **Custom Agents**: [Number] agents

### Template File Assessment
- **Count**: [Number] - Appropriate: ✓ / ✗
- **Coverage**: [Does it cover main patterns?]
- **Quality**: [Would templates be useful?]

---

## 3. AI Analysis Quality

### Overall Confidence Score
- **Score**: [0-100]%
- **Assessment**: [Too Low/Appropriate/Too High]

### Analysis Depth
- **Architecture Understanding**: [Excellent/Good/Fair/Poor]
- **Pattern Recognition**: [Excellent/Good/Fair/Poor]
- **Technology Stack**: [Excellent/Good/Fair/Poor]
- **Naming Conventions**: [Excellent/Good/Fair/Poor]

### Reasoning Quality
- **Explanations Clear**: ✓ / ✗
- **Evidence-Based**: ✓ / ✗
- **Accurate Conclusions**: ✓ / ✗

---

## 4. Accuracy Scoring

### Detection Accuracy
| Category | Accuracy | Notes |
|----------|----------|-------|
| Primary Language | [0-10] | |
| Framework(s) | [0-10] | |
| Architecture | [0-10] | |
| Patterns | [0-10] | |
| Infrastructure | [0-10] | |
| **Overall** | **[0-10]** | |

### False Positives
1. [Pattern/Technology] - Detected but not present
   - Evidence: [Why is this wrong?]
2. [Continue if more...]

### Missed Patterns
1. [Pattern/Technology] - Present but not detected
   - Evidence: [File/directory showing this exists]
2. [Continue if more...]

---

## 5. Performance

- **Execution Time**: [X] seconds
- **File Count Analyzed**: [N] files
- **Performance Rating**: [Excellent/Good/Fair/Poor]

**Notes**: [Any performance issues?]

---

## 6. Overall Assessment

### Strengths
1. [What did it do really well?]
2. [...]

### Weaknesses
1. [What did it miss or get wrong?]
2. [...]

### Recommendations
1. [How could detection be improved?]
2. [...]

### Overall Grade: [A/B/C/D/F]

**Would this template be usable?**: [Yes/No/Needs Work]

**Confidence in Results**: [High/Medium/Low]

---

## 7. Raw Output

<details>
<summary>Click to expand full /template-create output</summary>

\`\`\`
[Paste the complete output here]
\`\`\`

</details>

---

## 8. Screenshots (Optional)

- [Attach any relevant screenshots]

---

**Test Completed**: [YYYY-MM-DD HH:MM]
```

## Quick Reference: Repository Expectations

### CleanArchitecture-ardalis (.NET)
**Expected Detection**:
- Language: C#, .NET 9
- Framework: ASP.NET Core, FastEndpoints
- Architecture: Clean Architecture
- Patterns: REPR, CQRS, Repository
- Testing: xUnit

### go-clean-architecture (Go)
**Expected Detection**:
- Language: Go
- Framework: Gin
- Architecture: Clean Architecture
- Patterns: Repository, Dependency Injection
- Database: MongoDB

### bulletproof-react (React)
**Expected Detection**:
- Language: TypeScript
- Framework: React, Vite
- Architecture: Feature-based
- Testing: Vitest, Testing Library

### full-stack-fastapi-template (Python)
**Expected Detection**:
- Language: Python
- Framework: FastAPI, React
- Database: PostgreSQL, SQLModel
- Architecture: Clean Architecture
- Testing: pytest

### CleanArchitecture-jasontaylor (.NET)
**Expected Detection**:
- Language: C#, .NET 9
- Framework: ASP.NET Core
- Architecture: Clean Architecture
- Patterns: CQRS, MediatR
- Testing: NUnit or xUnit

### Go-Clean-Architecture-REST-API (Go)
**Expected Detection**:
- Language: Go
- Framework: Echo
- Architecture: Clean Architecture
- Infrastructure: PostgreSQL, Redis, Jaeger
- Patterns: Repository, CQRS

### actix-examples (Rust)
**Expected Detection**:
- Language: Rust
- Framework: Actix Web
- Patterns: Async/await, Actor model

### rocket/examples (Rust)
**Expected Detection**:
- Language: Rust
- Framework: Rocket
- Patterns: Type-safe routing

### Practical.CleanArchitecture (.NET)
**Expected Detection**:
- Language: C#
- Frameworks: Multiple (Blazor, React, Angular, Vue)
- Architecture: Microservices, Modular Monolith
- Very complex - may have lower confidence

### eShop (Microservices)
**Expected Detection**:
- Language: C#
- Architecture: Microservices
- Patterns: Event-driven, CQRS, DDD
- Infrastructure: Docker, Kubernetes

## Daily Testing Schedule

Suggested pace to avoid fatigue:

**Day 1** (2-3 hours):
- Morning: go-clean-architecture, bulletproof-react
- Afternoon: full-stack-fastapi-template

**Day 2** (2-3 hours):
- Morning: CleanArchitecture-ardalis, go-rest-api
- Afternoon: CleanArchitecture-jasontaylor

**Day 3** (2-3 hours):
- Morning: Go-Clean-Architecture-REST-API, actix-examples
- Afternoon: rocket

**Day 4** (2-3 hours):
- Morning: eShop
- Afternoon: Compile results, write summary

**Optional Day 5**:
- Practical.CleanArchitecture (very large, time-consuming)

## Tips for Effective Testing

### 1. Fresh Context is Critical
Don't skip the reload step! Context pollution will give inaccurate results.

### 2. Take Good Notes
Screenshot the output or copy/paste immediately. Don't rely on memory.

### 3. Compare Expected vs Actual
Use the "Repository Expectations" section to quickly validate results.

### 4. Note Surprises
If it detects something unexpected (good or bad), document it well.

### 5. Test at Different Depths
For a few repos, try without `--skip-qa` to see how Q&A affects results.

### 6. Performance Matters
Note if any repos take unusually long - could indicate optimization needs.

## Troubleshooting

### Issue: /template-create command not recognized
**Solution**: Ensure you're in Claude Code (not terminal) and the command is installed:
```bash
ls ~/.agentecflow/commands/ | grep template-create
```

### Issue: "Codebase path does not exist"
**Solution**: Verify you're in the correct directory:
```bash
pwd
ls -la
```

### Issue: Analysis fails or returns errors
**Document it!** This is valuable test feedback.

### Issue: Output is too long to capture
**Solution**: Use `--save-analysis` flag:
```bash
/template-create --skip-qa --dry-run --save-analysis
```
This saves analysis JSON to disk.

## After All Tests Complete

1. **Aggregate Results**: Create summary spreadsheet
2. **Calculate Statistics**:
   - Average accuracy scores
   - Average confidence scores
   - Success rate by language
   - Common false positives
   - Common missed patterns

3. **Write Final Report**: See [initialization-test-plan.md](initialization-test-plan.md)

4. **Create GitHub Issues**: For any bugs or improvements found

5. **Share Findings**: With GuardKit team

## Summary Report Template

After testing all repos, create: `results/FINAL-SUMMARY.md`

```markdown
# EPIC-001 Template Creation Testing - Final Summary

**Testing Period**: [Start Date] - [End Date]
**Repositories Tested**: [N] / 11
**Total Testing Time**: [X] hours

## Overall Results

### Accuracy by Category
| Category | Average Score | Pass Rate |
|----------|---------------|-----------|
| Language Detection | [X.X/10] | [XX%] |
| Framework Detection | [X.X/10] | [XX%] |
| Architecture Detection | [X.X/10] | [XX%] |
| Pattern Recognition | [X.X/10] | [XX%] |
| Infrastructure Detection | [X.X/10] | [XX%] |

### Overall Grade: [A/B/C/D/F]

### AI Confidence Scores
- Average: [XX%]
- Range: [XX%] - [XX%]
- Correlation with accuracy: [High/Medium/Low]

## Key Findings

### What Works Well
1. [Primary strengths]
2. [...]

### What Needs Improvement
1. [Primary weaknesses]
2. [...]

### Critical Issues
1. [Any blocking issues]
2. [...]

## Recommendations

### High Priority
1. [Must fix before release]
2. [...]

### Medium Priority
1. [Should fix soon]
2. [...]

### Low Priority / Future
1. [Nice to have]
2. [...]

## Test Coverage

| Technology Stack | Repos Tested | Average Accuracy |
|------------------|--------------|------------------|
| .NET | [N] | [XX%] |
| Go | [N] | [XX%] |
| Python | [N] | [XX%] |
| Rust | [N] | [XX%] |
| TypeScript/React | [N] | [XX%] |

## Conclusion

[Overall assessment of EPIC-001 template creation feature readiness]

**Ready for Production**: [Yes/No/With Caveats]
```

---

**Good luck with your testing!** 🚀

Remember: Quality over speed. It's better to test 5 repos thoroughly than 11 repos hastily.
