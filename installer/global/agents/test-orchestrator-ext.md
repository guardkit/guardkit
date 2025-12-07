# test-orchestrator - Extended Reference

This file contains detailed documentation for the `test-orchestrator` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/test-orchestrator-ext.md
```


## Documentation Level Awareness (TASK-035)

You receive `documentation_level` parameter via `<AGENT_CONTEXT>` block:

```markdown
<AGENT_CONTEXT>
documentation_level: minimal|standard|comprehensive
complexity_score: 1-10
task_id: TASK-XXX
stack: python|react|maui|etc
phase: 4
</AGENT_CONTEXT>
```

### Behavior by Documentation Level

**Key Principle**: Test execution, quality gates, and coverage enforcement **ALWAYS RUN** in all modes (quality gate preserved). Only the **output format** changes.

**Minimal Mode** (simple tasks, 1-3 complexity):
- Execute all tests (100% of test suite)
- Enforce all quality gates (coverage ≥80%, test pass rate 100%)
- Return **test results as structured data**
- Output: JSON test summary for embedding
- Example: `{"status": "passed", "total": 15, "passed": 15, "failed": 0, "coverage": {"lines": 92, "branches": 88}, "duration": "3.2s"}`

**Standard Mode** (medium tasks, 4-10 complexity, DEFAULT):
- Execute all tests (100% of test suite)
- Enforce all quality gates (coverage ≥80%, test pass rate 100%)
- Return **full test report**
- Output: Detailed test results with analysis and recommendations

**Comprehensive Mode** (explicit request or force triggers):
- Execute all tests (100% of test suite)
- Enforce all quality gates (coverage ≥80%, test pass rate 100%)
- Generate **enhanced test report** with historical trends, flaky test detection, and optimization suggestions
- Create supporting documents (test analysis, coverage trends)
- Output: Comprehensive test documentation

### Output Format Examples

**Minimal Mode Output** (for embedding):
```json
{
  "status": "passed",
  "build_status": "success",
  "test_results": {
    "total": 15,
    "passed": 15,
    "failed": 0,
    "skipped": 0,
    "duration": "3.2s"
  },
  "coverage": {
    "lines": 92,
    "branches": 88,
    "functions": 95
  },
  "quality_gates": {
    "build": "passed",
    "tests": "passed",
    "coverage": "passed"
  },
  "failed_tests": []
}
```

**Standard Mode Output** (embedded section):
```markdown

## Test Results (Phase 4)

**Summary**: ✅ ALL TESTS PASSED

**Test Execution**:
- Total: 15 tests
- Passed: 15 ✅
- Failed: 0
- Skipped: 0
- Duration: 3.2s

**Coverage**:
- Lines: 92% ✅ (threshold: ≥80%)
- Branches: 88% ✅ (threshold: ≥75%)
- Functions: 95% ✅

**Quality Gates**: ✅ ALL PASSED
- Build verification: ✅
- Test execution: ✅ (100% pass rate)
- Coverage thresholds: ✅

**Recommendations**:
- Consider adding edge case tests for error handling paths
```

**Comprehensive Mode Output** (standalone files):
- Full test report saved to `docs/testing/{task_id}-test-report.md`
- Historical trend analysis
- Flaky test detection
- Performance optimization suggestions
- Coverage gap analysis with recommendations
- Test quality metrics and patterns

### Quality Gate Preservation

**CRITICAL**: The following quality checks run in ALL modes (minimal/standard/comprehensive):
- Build verification (code MUST compile before tests run)
- Test execution (100% of test suite runs)
- Test pass rate enforcement (100% required)
- Coverage thresholds enforcement (≥80% lines, ≥75% branches)
- Quality gate validation (build + tests + coverage)

**What NEVER Changes**:
- Quality gate execution (all modes: 100%)
- Test coverage requirements (same thresholds)
- Test pass rate enforcement (100% required)
- Build verification rigor (comprehensive always)

**What Changes**:
- Output format (JSON vs embedded markdown vs standalone document)
- Documentation verbosity (concise vs balanced vs exhaustive)
- Supporting artifacts (none vs embedded vs standalone files)
- Analysis depth (essential metrics vs full analysis vs trend analysis)

### Agent Collaboration

**Markdown Plan**: This agent writes test results to the implementation plan at `.claude/task-plans/{TASK_ID}-implementation-plan.md`.

**Plan Format**: YAML frontmatter + structured markdown (always generated, all modes)

**Context Passing**: Uses `<AGENT_CONTEXT>` blocks for documentation_level parameter passing

**Backward Compatible**: Gracefully handles agents without context parameter support (defaults to standard)


## 🚨 MANDATORY RULE #0: EMPTY PROJECT DETECTION 🚨

**FIRST CHECK**: Before attempting any build or test operations, verify the project has source code.

**Why this is mandatory**:
- New/empty projects have no source code to compile or test
- Attempting to build empty projects wastes time and produces confusing errors
- Tests should be skipped gracefully for empty projects
- This prevents false failures on project initialization

**Detection sequence** (check BEFORE build):
```bash

# Step 0: Detect if project has source code

# Step 1: If no source code, skip build and tests with success

# Step 2: If source code exists, proceed to build verification (Rule #1)
```

**Stack-specific detection**:

### .NET / C# / MAUI
```bash

# Check for source files
source_count=$(find . -name "*.cs" -not -path "*/bin/*" -not -path "*/obj/*" -not -path "*/tests/*" | wc -l)

if [ "$source_count" -eq 0 ]; then
  echo "ℹ️  No source code detected - skipping build and tests"
  echo "✅ Empty project check passed (not applicable)"
  exit 0  # Success - empty project is valid
fi

echo "📦 Found $source_count source files - proceeding with build..."
```

### Python
```bash

# Check for Python modules
if [ ! -d "src" ] && [ $(find . -name "*.py" -not -path "*/venv/*" -not -path "*/tests/*" | wc -l) -eq 0 ]; then
  echo "ℹ️  No source code detected - skipping build and tests"
  echo "✅ Empty project check passed (not applicable)"
  exit 0
fi

echo "📦 Found Python source files - proceeding with tests..."
```

### TypeScript / Node.js
```bash

# Check for TypeScript/JavaScript source files
if [ ! -d "src" ] && [ $(find . -name "*.ts" -o -name "*.tsx" -not -path "*/node_modules/*" -not -path "*/tests/*" | wc -l) -eq 0 ]; then
  echo "ℹ️  No source code detected - skipping build and tests"
  echo "✅ Empty project check passed (not applicable)"
  exit 0
fi

echo "📦 Found TypeScript source files - proceeding with build..."
```

**Output for empty projects**:
```json
{
  "status": "skipped",
  "reason": "no_source_code",
  "message": "Empty project - build and tests skipped (not applicable)",
  "quality_gates": {
    "build": "not_applicable",
    "tests": "not_applicable",
    "coverage": "not_applicable"
  }
}
```

**IMPORTANT**: Empty project is NOT a failure - it's a valid state for new projects. Return exit code 0 (success).


## 🚨 MANDATORY RULE #1: BUILD BEFORE TEST 🚨

**ABSOLUTE REQUIREMENT**: Code MUST compile/build successfully BEFORE any tests are executed.

**Why this is mandatory**:
- Running tests on non-compiling code wastes time and produces confusing errors
- Compilation errors must be fixed before test failures can be addressed
- Test frameworks cannot execute if code doesn't build
- This prevents cascading failures and unclear error messages

**Enforcement sequence**:
```bash

# Step 1: Clean (remove previous build artifacts)

# Step 2: Restore (download dependencies)

# Step 3: Build (compile code)

# Step 4: IF build fails, STOP and report errors

# Step 5: ONLY if build succeeds, proceed to test execution
```

**Stack-specific build commands** (MUST run before tests):

### .NET / C# / MAUI
```bash

# Complete build verification sequence
dotnet clean
dotnet restore
dotnet build --no-restore

# Check exit code
if [ $? -ne 0 ]; then
  echo "❌ BUILD FAILED - Cannot proceed with tests"
  echo "Fix compilation errors first, then re-run tests"
  exit 1
fi

echo "✅ Build successful - proceeding with tests"
dotnet test --no-build --no-restore
```

### TypeScript / Node.js
```bash

# TypeScript compilation check
npm run build  # or: tsc --noEmit

# Check exit code
if [ $? -ne 0 ]; then
  echo "❌ COMPILATION FAILED - Cannot proceed with tests"
  echo "Fix TypeScript errors first, then re-run tests"
  exit 1
fi

echo "✅ Compilation successful - proceeding with tests"
npm test
```

### Python
```bash

# Python syntax and import verification
python -m py_compile src/**/*.py

# Check exit code
if [ $? -ne 0 ]; then
  echo "❌ SYNTAX ERRORS - Cannot proceed with tests"
  echo "Fix Python syntax errors first, then re-run tests"
  exit 1
fi

echo "✅ Syntax check successful - proceeding with tests"
pytest
```

### Java
```bash

# Maven compilation
mvn clean compile

# Check exit code
if [ $? -ne 0 ]; then
  echo "❌ COMPILATION FAILED - Cannot proceed with tests"
  echo "Fix Java compilation errors first, then re-run tests"
  exit 1
fi

echo "✅ Compilation successful - proceeding with tests"
mvn test
```

**Cross-reference**: See task-work.md Phase 4 for integration with task workflow.


## Test Execution Commands

### Stack-Specific Commands

#### React/TypeScript
```bash

# Unit tests with Vitest
npm run test:unit

# Component tests
npm run test:components

# E2E with Playwright
npm run test:e2e

# BDD with Cucumber
npm run test:bdd
```

#### Python API
```bash

# Unit tests with pytest
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# BDD with pytest-bdd
pytest tests/bdd --gherkin-terminal-reporter

# Coverage report
pytest --cov=src --cov-report=term-missing
```

### Parallel Execution
```javascript
// Run tests in parallel for speed
async function runTestsParallel(testSuites) {
  const promises = testSuites.map(suite => 
    runTestSuite(suite).catch(err => ({
      suite,
      error: err.message,
      failed: true
    }))
  );
  
  const results = await Promise.all(promises);
  return consolidateResults(results);
}
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat test-orchestrator-ext.md
```

Or in Claude Code:
```
Please read test-orchestrator-ext.md for detailed examples.
```
