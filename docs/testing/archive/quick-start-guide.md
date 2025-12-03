# Quick Start Guide - Initialization Feature Testing

## Overview

This guide provides step-by-step instructions for testing the GuardKit initialization feature using popular GitHub repositories across different technology stacks.

**Estimated Time**: 2-3 days (16 hours)
**Environment**: Virtual Machine (recommended)
**Prerequisites**: Git, GuardKit installed

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Clone Test Repositories](#clone-test-repositories)
3. [Running Tests](#running-tests)
4. [Recording Results](#recording-results)
5. [Troubleshooting](#troubleshooting)

## Environment Setup

### 1. Verify GuardKit Installation

```bash
# Check GuardKit is installed
guardkit --version

# Verify initialization feature is available
guardkit init --help
```

**Expected Output**: Should show version and help for init command.

### 2. Create Testing Workspace

```bash
# Create a dedicated testing directory
mkdir -p ~/guardkit-testing
cd ~/guardkit-testing

# Create results directory
mkdir -p results
```

### 3. Copy Testing Resources

If you have the GuardKit repository locally:

```bash
# Copy the test plan and scripts
cp /path/to/guardkit/docs/testing/initialization-test-plan.md .
cp /path/to/guardkit/docs/testing/clone-test-repos.sh .
chmod +x clone-test-repos.sh
```

Or download directly:

```bash
# Download the clone script
curl -O https://raw.githubusercontent.com/[your-repo]/guardkit/main/docs/testing/clone-test-repos.sh
chmod +x clone-test-repos.sh
```

## Clone Test Repositories

### Option 1: Clone All Repositories (Recommended)

```bash
# Clone all test repositories to ./test-repos
./clone-test-repos.sh

# Or specify a custom directory
./clone-test-repos.sh ~/my-test-repos
```

**Note**: By default, repositories are shallow-cloned (depth=1) for speed. For full history:

```bash
CLONE_DEPTH=0 ./clone-test-repos.sh
```

### Option 2: Clone Individual Repositories

If you prefer manual control or want to test specific phases:

```bash
mkdir -p test-repos
cd test-repos

# Phase 1 - Small repos
git clone --depth 1 https://github.com/zhashkevych/go-clean-architecture.git
git clone --depth 1 https://github.com/alan2207/bulletproof-react.git

# Phase 2 - Medium complexity
git clone --depth 1 https://github.com/fastapi/full-stack-fastapi-template.git
git clone --depth 1 https://github.com/ardalis/CleanArchitecture.git CleanArchitecture-ardalis
git clone --depth 1 https://github.com/qiangxue/go-rest-api.git

# Continue for other phases as needed...
```

## Understanding the Init Command

The `guardkit init` command automatically detects your project type and recommends an appropriate template. **No flags needed** - detection is automatic!

**How it works:**
```bash
cd /path/to/repository
guardkit init

# Output shows:
# ℹ Detected project type: [type]
# Recommended template: [template]
#
# Then prompts you to:
# 1. Accept the recommendation
# 2. Choose a different template
# 3. Proceed with initialization
```

**What it detects:**
- Programming language (.cs, .ts, .py, .go, .rs files)
- Framework (React, FastAPI, MAUI, etc.)
- Architecture patterns (Clean Architecture, MVVM, MVC)
- Testing frameworks
- Build tools

**For testing purposes**, you want to capture the detection output to evaluate accuracy.

## Running Tests

### Testing Workflow

For each repository, follow these steps:

#### 1. Navigate to Repository

```bash
cd test-repos/[repository-name]
```

#### 2. Run Initialization Detection

```bash
# Run init - it will auto-detect and show results
guardkit init

# To capture output for analysis (DON'T actually initialize):
# Answer "No" when asked to proceed with initialization
# OR use Ctrl+C after seeing the detection results

# Better: Redirect output to capture detection info
guardkit init 2>&1 | tee ../../results/[repository-name]-detection.txt
# Then press Ctrl+C when you see the detection results
```

**Time the execution** (optional but recommended):

```bash
time ( guardkit init 2>&1 | head -20 ) | tee ../../results/[repository-name]-detection.txt
```

**Important**: You DON'T want to actually initialize GuardKit in these test repos - you just want to see what it detects. So either:
1. Answer "No" to the initialization prompt
2. Use `Ctrl+C` after seeing the detection
3. Or just note the "Detected project type" line

#### 3. Review Output

The initialization should detect and display:
- Detected project type (language/framework)
- Example: `ℹ Detected project type: react`
- Example: `ℹ Detected project type: dotnet-api`
- Example: `ℹ Detected project type: python`
- Recommended template (if showing)

#### 4. Record Results

Use the test data collection template (see below) to document findings.

### Phase-by-Phase Testing Approach

#### Phase 1: Small Repositories (2 hours)

**Goal**: Quick validation of basic pattern detection

```bash
cd ~/guardkit-testing/test-repos

# Test 1: Go Clean Architecture
cd go-clean-architecture
echo "Testing: go-clean-architecture" | tee ../../results/go-clean-architecture.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/go-clean-architecture.txt
# Press Ctrl+C or answer "No" to avoid full initialization
cd ..

# Test 2: Bulletproof React
cd bulletproof-react
echo "Testing: bulletproof-react" | tee ../../results/bulletproof-react.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/bulletproof-react.txt
# Press Ctrl+C or answer "No" to avoid full initialization
cd ..
```

**Success Criteria**:
- ✅ Execution completes without errors
- ✅ Correct language/framework detection
- ✅ Execution time < 30 seconds each
- ✅ Reasonable template recommendation

**Decision Point**: If Phase 1 shows major issues, stop and fix before continuing.

#### Phase 2: Medium Complexity (3 hours)

**Goal**: Validate production-ready pattern detection

```bash
# Test 3: FastAPI Template
cd full-stack-fastapi-template
echo "Testing: fastapi-template" | tee ../../results/fastapi-template.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/fastapi-template.txt
cd ..

# Test 4: Ardalis Clean Architecture
cd CleanArchitecture-ardalis
echo "Testing: ardalis-clean-arch" | tee ../../results/ardalis-clean-arch.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/ardalis-clean-arch.txt
cd ..

# Test 5: Go REST API
cd go-rest-api
echo "Testing: go-rest-api" | tee ../../results/go-rest-api.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/go-rest-api.txt
cd ..
```

**Success Criteria**:
- ✅ Multi-directory structure handling
- ✅ Infrastructure detection (Docker, DBs)
- ✅ Testing strategy identification
- ✅ Execution time < 2 minutes each

#### Phase 3: Complex/Multi-Stack (4 hours)

**Goal**: Stress test with large, complex projects

```bash
# Test 6: Jason Taylor Clean Architecture
cd CleanArchitecture-jasontaylor
echo "Testing: jasontaylor-clean-arch" | tee ../../results/jasontaylor-clean-arch.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/jasontaylor-clean-arch.txt
cd ..

# Test 7: Go REST API with Full Stack
cd Go-Clean-Architecture-REST-API
echo "Testing: go-rest-full-stack" | tee ../../results/go-rest-full-stack.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/go-rest-full-stack.txt
cd ..

# Test 8: Actix Examples
cd actix-examples
echo "Testing: actix-examples" | tee ../../results/actix-examples.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/actix-examples.txt
cd ..

# Test 9: Rocket Examples
cd rocket/examples
echo "Testing: rocket-examples" | tee ../../../results/rocket-examples.txt
guardkit init 2>&1 | head -20 | tee -a ../../../results/rocket-examples.txt
cd ../..

# Test 10: Practical Clean Architecture (Optional - Very Large)
cd Practical.CleanArchitecture
echo "Testing: practical-clean-arch" | tee ../../results/practical-clean-arch.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/practical-clean-arch.txt
cd ..
```

**Success Criteria**:
- ✅ Multiple frontend detection
- ✅ Complex architecture patterns
- ✅ Production infrastructure
- ✅ Execution time < 5 minutes (or < 10 for very large)

#### Phase 4: Microservices (3 hours)

**Goal**: Validate distributed systems detection

```bash
# Test 11: eShop Microservices
cd eShop
echo "Testing: eShop" | tee ../../results/eShop.txt
guardkit init 2>&1 | head -20 | tee -a ../../results/eShop.txt
cd ..
```

**Success Criteria**:
- ✅ Service boundary detection
- ✅ Inter-service communication patterns
- ✅ Event-driven architecture recognition
- ✅ Container orchestration patterns

## Recording Results

### Test Data Collection Template

Create a file for each repository: `results/[repository-name]-report.md`

```markdown
### Repository: [Name]
**Date**: [YYYY-MM-DD]
**Tester**: [Your Name]
**VM Environment**: [OS, specs]
**Phase**: [1/2/3/4]

#### Execution
- **Time**: [X.XX seconds]
- **Success**: [Yes/No]
- **Errors**: [Any errors or warnings]

#### Detection Results

**Stack Detection**:
- Language: [Detected] (Actual: [Actual]) ✓/✗
- Framework: [Detected] (Actual: [Actual]) ✓/✗
- Testing: [Detected] (Actual: [Actual]) ✓/✗
- Build Tool: [Detected] (Actual: [Actual]) ✓/✗

**Architecture Patterns** (with confidence %):
- [Pattern]: [XX%] ✓/✗
- [Pattern]: [XX%] ✓/✗
- [Pattern]: [XX%] ✓/✗

**Infrastructure**:
- Database: [Detected] ✓/✗
- Cache: [Detected] ✓/✗
- Message Queue: [Detected] ✓/✗
- Container: [Detected] ✓/✗
- Orchestration: [Detected] ✓/✗

**Template Recommendation**:
- Recommended: [Template Name]
- Correct: [Yes/No/Partial]
- Match %: [0-100%]
- Notes: [Why correct/incorrect]

#### Accuracy Score: [0-10]

#### Detailed Notes

**What Worked Well**:
- [List things that were detected correctly]

**False Positives**:
- [Pattern] - Detected but not actually present because [reason]

**Missed Patterns**:
- [Pattern] - Present but not detected, evidence: [file/directory/code]

**Performance Issues**:
- [Any slowdowns, timeouts, or performance concerns]

**Improvement Suggestions**:
- [Specific suggestions for better detection]

#### Supporting Evidence

**Key Files Analyzed**:
- [List important files that should have been analyzed]

**Key Directories**:
- [List important directories]

**Sample Output**:
```
[Paste relevant portions of the analysis output]
```
```

### Quick Recording Method

For rapid testing, use this shorthand:

```bash
# Create a quick results file
cat > results/[repo-name]-quick.txt <<EOF
Repo: [name]
Time: [seconds]
Language: [detected] - [✓/✗]
Framework: [detected] - [✓/✗]
Architecture: [detected] - [✓/✗]
Template: [recommended]
Score: [0-10]
Notes: [brief notes]
EOF
```

## Progress Tracking

### Checklist Format

Use this checklist to track overall progress:

```
Phase 1: Small Repositories
  [ ] go-clean-architecture
  [ ] bulletproof-react

Phase 2: Medium Complexity
  [ ] full-stack-fastapi-template
  [ ] CleanArchitecture-ardalis
  [ ] go-rest-api

Phase 3: Complex/Multi-Stack
  [ ] CleanArchitecture-jasontaylor
  [ ] Go-Clean-Architecture-REST-API
  [ ] actix-examples
  [ ] rocket (examples dir)
  [ ] Practical.CleanArchitecture (optional)

Phase 4: Microservices
  [ ] eShop
```

### Daily Summary Template

At the end of each testing day:

```markdown
## Testing Summary - Day [N]

**Date**: [YYYY-MM-DD]
**Repositories Tested**: [N]
**Phase(s) Completed**: [Phase numbers]

### Statistics
- Total execution time: [HH:MM:SS]
- Average per repo: [MM:SS]
- Success rate: [N/N]
- Average accuracy: [0-10]

### Key Findings
**Strengths**:
- [What worked well across multiple repos]

**Issues**:
- [Common problems found]

**Blockers**:
- [Anything preventing progress]

### Next Steps
- [ ] [Tomorrow's plan]
```

## Troubleshooting

### Common Issues

#### Issue: Clone script fails

```bash
# Check git is installed
git --version

# Check network connectivity
ping github.com

# Try manual clone
git clone https://github.com/zhashkevych/go-clean-architecture.git
```

#### Issue: GuardKit init command not found

```bash
# Verify installation
which guardkit

# Check PATH
echo $PATH

# Reinstall if needed
./installer/scripts/install.sh
```

#### Issue: Initialization takes too long

```bash
# Check if repository is too large
du -sh .

# Check file count
find . -type f | wc -l

# Note: init command doesn't have exclude flags
# It should be fast as it only scans for detection
```

#### Issue: Out of disk space

```bash
# Check available space
df -h

# Clean up shallow clones
cd test-repos
find . -name ".git" -type d -exec du -sh {} \; | sort -hr

# Remove large repos you've already tested
rm -rf [repo-name]
```

#### Issue: Results are inconsistent

```bash
# Clear any GuardKit state (if it exists)
rm -rf .claude/

# Run detection again
guardkit init
```

### Getting Help

If you encounter issues:

1. **Check logs**: Look for log files in `.guardkit/logs/`
2. **Verbose mode**: Run with `--verbose` flag
3. **Debug mode**: Run with `--debug` flag
4. **Document the issue**: Capture error messages and context
5. **Open issue**: Create a GitHub issue with details

## Best Practices

### 1. Test in Order
Start with Phase 1 (small repos) and progress sequentially. Don't skip to complex repos until basic detection works.

### 2. Document As You Go
Don't wait until the end to document findings. Record results immediately after each test.

### 3. Take Breaks
This is 16 hours of work. Take regular breaks to maintain focus and accuracy.

### 4. Compare Results
If two similar repos give different results, investigate why.

### 5. Save All Output
Use `tee` to save all output to files. You might need to review later.

### 6. Version Control Results
Consider committing results to a git repo for tracking:

```bash
cd ~/guardkit-testing
git init
git add results/
git commit -m "Testing results for [date]"
```

## After Testing Complete

### 1. Aggregate Results

```bash
# Create summary report
cat results/*-report.md > results/COMPLETE-SUMMARY.md
```

### 2. Calculate Statistics

```bash
# Count total tests
ls results/*-report.md | wc -l

# Extract accuracy scores
grep "Accuracy Score:" results/*-report.md
```

### 3. Identify Patterns

- Which technology stacks had best detection?
- Which patterns were most commonly missed?
- What was average execution time by project size?
- Which templates were most recommended?

### 4. Create Final Report

See [initialization-test-plan.md](initialization-test-plan.md) for report template.

### 5. Share Findings

- Commit results to repository
- Share with team
- Create GitHub issues for bugs found
- Update documentation based on findings

## Quick Reference Commands

```bash
# Clone all repos
./clone-test-repos.sh

# Test a single repo (capture detection only)
cd test-repos/[repo-name]
guardkit init 2>&1 | head -20 | tee ../../results/[repo-name]-detection.txt

# Check progress
ls results/*.txt | wc -l

# View all results
cat results/*.txt | less

# Clean up (after testing)
rm -rf test-repos
```

## Time Management

Suggested schedule for 3-day testing:

**Day 1** (6 hours):
- Setup environment (1h)
- Clone all repos (1h)
- Phase 1 testing (2h)
- Phase 2 testing (2h)

**Day 2** (6 hours):
- Phase 3 testing (4h)
- Phase 4 testing (2h)

**Day 3** (4 hours):
- Re-test any issues (1h)
- Aggregate results (1h)
- Write final report (2h)

## Support

For questions or issues:
- Review [initialization-test-plan.md](initialization-test-plan.md)
- Check GuardKit documentation
- Open GitHub issue
- Contact maintainers

---

**Good luck with your testing!** 🚀
