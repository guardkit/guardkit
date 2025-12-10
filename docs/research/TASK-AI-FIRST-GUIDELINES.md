# TASK-AI-FIRST-GUIDELINES: Create AI-First Architecture Guidelines

**Created**: 2025-11-14
**Priority**: Critical
**Type**: Documentation / Architecture
**Status**: Backlog
**Complexity**: 4/10 (Medium)
**Estimated Effort**: 4-6 hours
**Dependencies**: Template-Create Forensic Analysis
**Related Tasks**: TASK-AI-FIRST-AUDIT, TASK-077E (original implementation)

---

## Problem Statement

The template-create command degraded from clean AI-first architecture (TASK-077E) to 656+ LOC of Python hard-coding through incremental "improvements". This happened because there were no explicit guidelines preventing Python pattern matching from replacing AI intelligence.

**Goal**: Create comprehensive architecture guidelines to prevent future architectural drift and establish clear rules for when to use AI vs Python.

---

## Context

**Forensic Analysis**: [template-create-forensic-analysis.md](../../docs/investigations/template-create-forensic-analysis.md)

**Key Finding**: Each task added Python logic that seemed reasonable in isolation but cumulatively violated the AI-first principle:
- TASK-9039: SmartDefaultsDetector (531 LOC of pattern matching)
- TASK-E8F4: JSON parsing logic (125 LOC of fallback strategies)
- TASK-TMPL-4E89: Hard-coded agent detection (5 patterns only)

**Total Drift**: ~656 LOC of hard-coding replaced AI intelligence

**Why This Happened**:
- No explicit "AI-first" design rules
- No code review checklist for pattern matching
- No architectural tests
- Missing "why" documentation (purpose of AI-first)

---

## Objectives

### Primary Objective
Create comprehensive architecture guidelines that prevent hard-coding patterns and enforce AI-first principles across all guardkit components.

### Success Criteria
- [ ] AI-First Design Principles documented
- [ ] Decision framework: "When to use AI vs Python"
- [ ] Code review checklist created
- [ ] Architecture tests defined
- [ ] Examples of good vs bad patterns
- [ ] Prevention rules (4 tests from forensic analysis)
- [ ] Integration with /task-create workflow
- [ ] Team training materials

---

## Implementation Scope

### 1. Create Core Guidelines Document

**File**: `docs/architecture/ai-first-principles.md`

**Content Sections**:

```markdown
# AI-First Architecture Principles

## Philosophy

**Core Principle**: AI provides intelligence, Python provides orchestration.

**Why AI-First?**
- **Maintainability**: Zero code changes for new frameworks/patterns
- **Extensibility**: Works with ANY language/framework automatically
- **Quality**: AI understands context better than pattern matching
- **Simplicity**: Less code = fewer bugs

**The Anti-Pattern**:
```python
# BAD: Python "understands" patterns
if 'Repository' in filename:
    return 'repository-pattern'
# Must update code for: Manager, Service, Engine, Handler...
```

**The AI-First Pattern**:
```python
# GOOD: AI understands patterns
ai_analysis = analyzer.analyze("What patterns exist in this codebase?")
return ai_analysis.patterns  # Works for ANY pattern
```

## The Four Tests

Before adding any Python logic, apply these tests:

### Test 1: The Maintainability Test
**Question**: "Will this code need updates when a new framework/pattern/language emerges?"

**If YES**: Use AI instead.

**Example**:
```python
# ❌ FAILS: Needs updates for new frameworks
if 'react' in deps: return 'React'
elif 'vue' in deps: return 'Vue'
# What about Svelte? Solid? Qwik?

# ✅ PASSES: Works for any framework
framework = ai.analyze("What UI framework?")
```

### Test 2: The Intelligence Source Test
**Question**: "Is Python understanding patterns, or just coordinating?"

**If Python is understanding**: Use AI instead.

**Example**:
```python
# ❌ FAILS: Python "understands" MVVM
if any('ViewModel' in f for f in files):
    return 'MVVM'

# ✅ PASSES: AI understands MVVM
architecture = ai.analyze("What architecture pattern?")
```

### Test 3: The Extensibility Test
**Question**: "How many lines of code to support a new pattern?"

**If > 0**: Use AI instead.

**Example**:
```python
# ❌ FAILS: Need code changes for each agent
if 'Repository' in files:
    yield 'repository-specialist'
if 'Service' in files:
    yield 'service-specialist'
# Need to add: Manager, Engine, Handler...

# ✅ PASSES: Zero code for new agents
agents = ai.analyze("What specialized agents needed?")
```

### Test 4: The Parsing Trap Test
**Question**: "Am I fixing AI output, or constraining AI input?"

**Always choose**: Constrain input (better prompts), not parse output.

**Example**:
```python
# ❌ FAILS: Parsing messy output (125 LOC)
def extract_json(response):
    # Try plain JSON
    # Try markdown
    # Try regex
    # etc...

# ✅ PASSES: Constrain to output correctly
response = ai.analyze(
    prompt=prompt,
    system="Respond ONLY with valid JSON"
)
```

## When to Use Python vs AI

### Use Python For:
✅ **Orchestration**: Coordinating workflow phases
✅ **File I/O**: Reading/writing files
✅ **Simple Logic**: Path manipulation, string formatting
✅ **UI/UX**: Progress indicators, user prompts
✅ **Error Handling**: Try/catch, validation
✅ **Data Transformation**: Format conversion (after AI analysis)

### Use AI For:
✅ **Pattern Recognition**: Identifying architecture patterns
✅ **Understanding**: "What does this code do?"
✅ **Decision Making**: "What agents are needed?"
✅ **Inference**: "What framework is this?"
✅ **Generation**: Creating templates, agents, docs
✅ **Analysis**: Code quality, complexity assessment

### NEVER Use Python For:
❌ **Pattern Matching**: File extension → language detection
❌ **Hard-Coding**: Known framework names, pattern names
❌ **Parsing AI Output**: Extracting JSON from text (fix prompts instead)
❌ **Pattern Detection**: Checking for *Repository.py files
❌ **Intelligence**: Any logic that "understands" code structure

## Examples: Good vs Bad

### Example 1: Language Detection

```python
# ❌ BAD (Hard-coded, needs maintenance)
def detect_language(files):
    if any(f.suffix == '.csproj' for f in files):
        return 'C#'
    elif any(f.suffix == '.py' for f in files):
        return 'Python'
    elif any(f.name == 'package.json' for f in files):
        return 'TypeScript'
    # Must add: Go, Rust, Kotlin, Swift...
    
# ✅ GOOD (AI-powered, zero maintenance)
def detect_language(files):
    file_list = "\n".join(str(f) for f in files[:20])
    return ai.analyze(f"What programming language? Files:\n{file_list}")
```

### Example 2: Agent Generation

```python
# ❌ BAD (Limited to 5 patterns)
def detect_agents(files):
    agents = []
    if any('ViewModel' in f for f in files):
        agents.append('mvvm-specialist')
    if any('Repository' in f for f in files):
        agents.append('repository-specialist')
    # Only 5 patterns supported
    return agents

# ✅ GOOD (Unlimited patterns)
def detect_agents(codebase_structure):
    return ai.analyze("""
        Analyze this codebase and recommend specialized agents.
        Return JSON: {"agents": [{"name": "...", "purpose": "..."}]}
    """)
```

### Example 3: Template Generation

```python
# ❌ BAD (Pattern-based file selection)
def select_template_files(files):
    templates = []
    for f in files:
        if f.name.endswith('Entity.cs'):
            templates.append(f)
        elif f.name.endswith('ViewModel.cs'):
            templates.append(f)
    # Hard-coded patterns
    return templates

# ✅ GOOD (AI-based file selection)
def select_template_files(codebase_analysis):
    return ai.analyze("""
        Which files would make good reusable templates?
        Consider:
        - Representative of common patterns
        - Clear, well-structured
        - Useful across features
    """)
```

## Architectural Constraints

### Hard Limits
- **Max Pattern Matching LOC**: 0 (zero tolerance)
- **Max Hard-Coded Patterns**: 0 (use AI for all patterns)
- **Max Parsing Logic LOC**: 10 (simple JSON.loads only)

### Code Review Triggers
Any PR that includes:
- File extension checks (`.py`, `.cs`, etc.)
- Dependency name checks (`'react'`, `'fastapi'`)
- Pattern name checks (`'Repository'`, `'Service'`)
- Multi-strategy parsing (fallbacks, regex)

Must be flagged for AI-first review.

## Migration Strategy

For existing code with pattern matching:

1. **Identify**: List all pattern matching logic
2. **Measure**: Count LOC of hard-coding
3. **Prioritize**: High-impact areas first
4. **Replace**: Convert to AI analysis
5. **Test**: Verify works on diverse codebases
6. **Delete**: Remove pattern matching code

## Enforcement

### Pre-Commit Hook
```bash
# Check for pattern matching
if grep -r "if.*\.suffix" *.py; then
    echo "❌ Pattern matching detected. Use AI instead."
    exit 1
fi
```

### CI/CD Checks
- Pattern matching LOC count
- Hard-coded string detection
- Maintainability score

### Code Review Checklist
- [ ] No file extension checks
- [ ] No dependency name matching
- [ ] No pattern name hard-coding
- [ ] AI prompts used for intelligence
- [ ] Simple orchestration only

---

**Document created**: 2025-11-14
**Based on**: Template-Create Forensic Analysis
**Status**: Draft for review
```

### 2. Create Decision Framework Document

**File**: `docs/architecture/ai-vs-python-decision-tree.md`

**Visual decision tree for developers**

### 3. Create Code Review Checklist

**File**: `.github/PULL_REQUEST_TEMPLATE.md` (update)

**Add AI-First section**:
```markdown
## AI-First Architecture Review

- [ ] No hard-coded pattern matching (file extensions, dependencies)
- [ ] All intelligence comes from AI analysis
- [ ] Python code is orchestration only
- [ ] Passes all 4 AI-first tests (see docs/architecture/ai-first-principles.md)
- [ ] Zero maintenance needed for new frameworks/patterns
```

### 4. Create Training Materials

**File**: `docs/guides/ai-first-development.md`

**Content**:
- Why AI-first matters
- Common pitfalls
- How to refactor pattern matching to AI
- Examples from template-create

### 5. Create Architecture Tests

**File**: `tests/architecture/test_ai_first_compliance.py`

**Tests**:
```python
def test_no_file_extension_checks():
    """Verify no hard-coded file extension checks exist"""
    
def test_no_dependency_name_matching():
    """Verify no hard-coded dependency names"""
    
def test_no_pattern_name_hard_coding():
    """Verify no hard-coded pattern names"""
    
def test_maintainability_score():
    """Calculate lines of pattern matching code (should be 0)"""
```

### 6. Integration with /task-create

**Update**: `installer/core/commands/task-create.md`

**Add section**: "AI-First Design Review"
- Automatically check task description for pattern matching
- Warn if task involves hard-coding
- Suggest AI-first alternative

---

## Files to Create/Update (Checklist)

### Core Documentation
- [ ] `docs/architecture/ai-first-principles.md` - Main guidelines
- [ ] `docs/architecture/ai-vs-python-decision-tree.md` - Visual decision aid
- [ ] `docs/guides/ai-first-development.md` - Training material
- [ ] `docs/architecture/examples/` - Good vs bad code examples

### Process Integration
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` - Add AI-first checklist
- [ ] `.github/workflows/ai-first-check.yml` - Automated checks
- [ ] `installer/core/commands/task-create.md` - Design review prompt

### Testing
- [ ] `tests/architecture/test_ai_first_compliance.py` - Architecture tests
- [ ] `tests/architecture/conftest.py` - Test fixtures
- [ ] `.pre-commit-config.yaml` - Pre-commit hooks

### Reference Materials
- [ ] `docs/investigations/template-create-forensic-analysis.md` - Already exists ✅
- [ ] `docs/architecture/case-studies/template-create-lessons.md` - Lessons learned

---

## Acceptance Criteria

### Functional Requirements
- [ ] Complete AI-first principles documented
- [ ] Four tests clearly explained with examples
- [ ] Decision framework: when to use AI vs Python
- [ ] Code review checklist integrated
- [ ] Architecture tests implemented
- [ ] Pre-commit hooks configured

### Quality Requirements
- [ ] Examples for each principle (good vs bad)
- [ ] Visual decision tree
- [ ] Training materials for team
- [ ] Integration with existing workflow
- [ ] Measurable compliance metrics

### Documentation Requirements
- [ ] Why AI-first matters
- [ ] Common pitfalls documented
- [ ] Migration strategy for existing code
- [ ] Enforcement mechanisms explained

---

## Testing Requirements

### Documentation Validation
```bash
# 1. Verify all sections present
grep "The Four Tests" docs/architecture/ai-first-principles.md
grep "When to Use Python vs AI" docs/architecture/ai-first-principles.md
grep "Examples: Good vs Bad" docs/architecture/ai-first-principles.md

# 2. Check decision tree exists
ls docs/architecture/ai-vs-python-decision-tree.md

# 3. Verify code review checklist
grep "AI-First Architecture Review" .github/PULL_REQUEST_TEMPLATE.md
```

### Architecture Tests
```bash
# Run architecture compliance tests
pytest tests/architecture/test_ai_first_compliance.py -v

# Expected: All tests pass
# - No file extension checks
# - No dependency matching
# - No pattern hard-coding
# - Maintainability score: 0 LOC pattern matching
```

---

## Success Metrics

**Quantitative**:
- Pattern matching LOC: 0 (after cleanup)
- Architecture tests: 100% passing
- Pre-commit checks: Enabled and enforced
- Code reviews: AI-first checklist used

**Qualitative**:
- Team understands AI-first principles
- New code follows guidelines
- No new pattern matching added
- Existing pattern matching identified for removal

---

## Related Tasks

- **TASK-AI-FIRST-AUDIT**: Audit current code for violations (prerequisite for cleanup)
- **TASK-077E**: Original template-create implementation (reference)
- **TASK-9039**: SmartDefaultsDetector (example of what NOT to do)
- **TASK-E8F4**: JSON parsing (example of parsing trap)

---

## Implementation Notes

### Priority Order
1. Create core principles document (2 hours)
2. Create decision framework (1 hour)
3. Create code review checklist (30 min)
4. Create architecture tests (1.5 hours)
5. Create training materials (1 hour)

### Templates to Include
Use real examples from template-create degradation:
- SmartDefaultsDetector (TASK-9039) - what NOT to do
- JSON parsing (TASK-E8F4) - parsing trap
- Original TASK-077E - what TO do

### Enforcement Strategy
- **Immediate**: Code review checklist (soft enforcement)
- **Short-term**: Architecture tests (automated detection)
- **Long-term**: Pre-commit hooks (hard enforcement)

---

## Next Steps After Completion

1. Run TASK-AI-FIRST-AUDIT to measure current state
2. Train team on guidelines
3. Create cleanup tasks for existing violations
4. Monitor compliance in code reviews
5. Update guidelines based on lessons learned

---

**Document Status**: Ready for Implementation
**Created**: 2025-11-14
**Parent**: Template-Create Recovery
**Note**: Prevents future architectural drift
