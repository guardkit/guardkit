# TASK-AGENT-EXAMPLES: Increase Code Example Density to 40-50%

**Task ID**: TASK-AGENT-EXAMPLES-20251121-120200
**Priority**: HIGH (P1)
**Status**: BACKLOG
**Created**: 2025-11-21
**Tags**: agents, code-examples, show-dont-tell, github-best-practices

---

## Overview

Increase code example density from current 20-25% to GitHub's recommended 40-50%, following their finding: **"One real code snippet showing your style beats three paragraphs describing it"**.

**Current Problem**:
- task-manager: 15% examples (TOO LOW)
- code-reviewer: 30% examples (BELOW TARGET)
- architectural-reviewer: 40% examples (MEETS TARGET - use as template)
- Overall: Heavy on theory, light on practical demonstrations

**GitHub's Finding from 2,500+ Repos**:
> Developers learn faster from code examples than descriptions. Target: 50% examples in first 200 lines, 40% overall.

**Impact**: Faster onboarding, better pattern adoption, reduced confusion

---

## Acceptance Criteria

### AC1: Example Density Targets

**Overall File**:
- [ ] ≥40% code examples (measured in lines)
- [ ] Code examples use ✅/❌ comparison format
- [ ] Each example has one-sentence rationale

**Quick Start Section** (lines 21-150):
- [ ] ≥60% code examples
- [ ] 10-20 examples per agent
- [ ] Examples show common patterns developers will encounter

**Measurement Formula**:
```python
code_lines = count_lines_in_code_blocks()
text_lines = count_lines_outside_code_blocks()
example_ratio = code_lines / (code_lines + text_lines)
# Target: example_ratio >= 0.40
```

---

### AC2: Example Format Consistency

All code examples MUST use this format:

```markdown
### ❌ DON'T: [Anti-Pattern Name]
```[language]
[Bad code example - realistic, not trivial]
```
**Problem**: [One-sentence explanation of what's wrong]

### ✅ DO: [Best Practice Name]
```[language]
[Good code example - showing the fix]
```
**Why**: [One-sentence rationale for this approach]
**Impact**: [Quantified benefit if possible: time saved, bugs prevented, etc.]
```

**Acceptance**:
- [ ] All examples use ✅/❌ format
- [ ] Each example has Problem/Why/Impact explanation
- [ ] Language specified for syntax highlighting
- [ ] Examples are realistic (not pseudocode)

---

### AC3: Example Coverage by Category

Each agent MUST have examples covering:

**For code-reviewer.md** (add 30 examples, ~120 lines):
1. **Security** (6 examples):
   - SQL injection prevention
   - XSS protection
   - CSRF tokens
   - Authentication patterns
   - Authorization checks
   - Sensitive data handling

2. **Performance** (5 examples):
   - N+1 query prevention
   - Caching strategies
   - Async/await optimization
   - Memory management
   - Database indexing

3. **Testing** (5 examples):
   - Test structure (AAA pattern)
   - Mocking strategies
   - Edge case coverage
   - Integration test patterns
   - Test data management

4. **Error Handling** (4 examples):
   - Try-catch patterns
   - Error propagation
   - Logging strategies
   - Graceful degradation

5. **Code Quality** (10 examples):
   - Magic numbers → constants
   - Nested callbacks → async/await
   - God classes → SRP
   - Long methods → extraction
   - Code duplication → DRY

**For architectural-reviewer.md** (add 20 examples, ~80 lines):
1. **SOLID Principles** (10 examples - 2 per principle):
   - SRP: Class with multiple responsibilities → Single responsibility
   - OCP: Hard-coded logic → Extension points
   - LSP: Violation of substitution → Correct inheritance
   - ISP: Fat interface → Segregated interfaces
   - DIP: Concrete dependency → Abstraction

2. **Anti-Patterns** (10 examples):
   - God class → Decomposition
   - Shotgun surgery → Cohesion
   - Primitive obsession → Value objects
   - Feature envy → Move method
   - Data clumps → Extract class

**For task-manager.md** (add 40 examples, ~160 lines):
1. **Task States** (5 examples):
   - Valid state transitions
   - Invalid state transitions
   - State validation logic
   - Metadata updates
   - Error handling

2. **Phase Execution** (10 examples):
   - Phase 2.5 trigger conditions
   - Phase 2.7 complexity scoring
   - Phase 2.8 checkpoint decisions
   - Phase 4.5 auto-fix loop
   - Phase 5.5 plan audit

3. **Error Scenarios** (5 examples):
   - Build failures
   - Test failures
   - Timeout handling
   - Validation errors
   - Rollback procedures

4. **MCP Integration** (5 examples):
   - context7 usage
   - design-patterns usage
   - Token budget management
   - Error handling
   - Fallback strategies

5. **Task Metadata** (5 examples):
   - YAML frontmatter
   - Acceptance criteria
   - Implementation plans
   - Test results
   - Review feedback

---

### AC4: Stack-Specific Examples

Each example MUST be technology-appropriate:

**Python** (FastAPI, pytest):
```python
# ❌ DON'T: Synchronous blocking
def get_user(user_id: int):
    return db.query(User).filter(User.id == user_id).first()

# ✅ DO: Async non-blocking
async def get_user(user_id: int):
    return await db.query(User).filter(User.id == user_id).first()
```

**TypeScript** (React, Vitest):
```typescript
// ❌ DON'T: useState for derived state
const [fullName, setFullName] = useState('');
useEffect(() => {
  setFullName(`${firstName} ${lastName}`);
}, [firstName, lastName]);

// ✅ DO: Computed value
const fullName = `${firstName} ${lastName}`;
```

**C#** (.NET, xUnit):
```csharp
// ❌ DON'T: Throwing exceptions for flow control
public User GetUser(int id) {
    if (!userExists) throw new Exception("Not found");
}

// ✅ DO: ErrorOr pattern
public ErrorOr<User> GetUser(int id) {
    if (!userExists) return Error.NotFound("User.NotFound");
    return user;
}
```

**Acceptance**:
- [ ] Examples use correct language syntax
- [ ] Examples use stack-specific frameworks/patterns
- [ ] Examples match template technology choices

---

## Implementation Plan

### Step 1: Audit Current Example Density (2 hours)

**Script**: `scripts/count-example-density.py`

```python
#!/usr/bin/env python3
"""Calculate code example density per agent."""
import re
from pathlib import Path

def count_lines(file_path: Path) -> dict:
    """Count code vs text lines."""
    with open(file_path) as f:
        content = f.read()
    
    # Split into code blocks and text
    code_pattern = r'```[^\n]*\n(.*?)```'
    code_blocks = re.findall(code_pattern, content, re.DOTALL)
    code_lines = sum(len(block.split('\n')) for block in code_blocks)
    
    # Remove code blocks to count text
    text_content = re.sub(code_pattern, '', content, flags=re.DOTALL)
    text_lines = len([line for line in text_content.split('\n') if line.strip()])
    
    total_lines = code_lines + text_lines
    ratio = code_lines / total_lines if total_lines > 0 else 0
    
    return {
        "file": file_path.name,
        "code_lines": code_lines,
        "text_lines": text_lines,
        "total_lines": total_lines,
        "example_ratio": ratio,
        "status": "✅ PASS" if ratio >= 0.40 else "❌ FAIL"
    }

agents_dir = Path("installer/global/agents")
results = []

for agent_file in agents_dir.glob("*.md"):
    result = count_lines(agent_file)
    results.append(result)
    print(f"{result['status']} {result['file']}: {result['example_ratio']:.1%} "
          f"({result['code_lines']} code / {result['total_lines']} total)")

# Summary
pass_count = sum(1 for r in results if r['example_ratio'] >= 0.40)
print(f"\n{'='*70}")
print(f"SUMMARY: {pass_count}/{len(results)} agents meet 40% target")
print(f"{'='*70}")
```

**Run**:
```bash
python3 scripts/count-example-density.py
```

**Expected Output**:
```
❌ FAIL task-manager.md: 15% (180 code / 1200 total)
❌ FAIL code-reviewer.md: 30% (120 code / 400 total)
✅ PASS architectural-reviewer.md: 40% (200 code / 500 total)
...
SUMMARY: 3/15 agents meet 40% target
```

**Action**: Identify agents needing most examples (lowest ratios)

---

### Step 2: Create Example Library (4 hours)

**For each agent**, create comprehensive example library:

#### 2.1: Security Examples (`examples/security-patterns.md`)

```markdown
# Security Pattern Examples

## SQL Injection Prevention

### ❌ DON'T: String concatenation
```python
query = f"SELECT * FROM users WHERE id = {user_id}"
db.execute(query)
```
**Problem**: User input directly in SQL (injection risk)

### ✅ DO: Parameterized query
```python
query = "SELECT * FROM users WHERE id = ?"
db.execute(query, [user_id])
```
**Why**: Database escapes parameters automatically
**Impact**: Prevents SQL injection attacks (OWASP #1)

[Add 20 more security examples]
```

#### 2.2: Performance Examples (`examples/performance-patterns.md`)
[20 examples for N+1, caching, async, indexing]

#### 2.3: Testing Examples (`examples/testing-patterns.md`)
[20 examples for AAA, mocking, edge cases, integration]

#### 2.4: Architecture Examples (`examples/architecture-patterns.md`)
[20 examples for SOLID, anti-patterns, refactoring]

**Total**: 80-100 reusable examples across all categories

---

### Step 3: Add Examples to Agents (Week 1-3, 30 hours)

**Process per agent** (2 hours each × 15 agents):

#### 3.1: Select Relevant Examples

From example library, choose 20-30 examples relevant to agent:
- code-reviewer: Security + Performance + Testing + Quality
- architectural-reviewer: SOLID + Anti-patterns
- task-manager: Workflow + States + Error handling

#### 3.2: Insert into Quick Start Section

**Location**: Lines 40-120 (after role, before boundaries)

**Format**:
```markdown
## Quick Start

### Common Patterns

[Insert 10 examples here - most frequently encountered]

### Security Patterns

[Insert 5 security examples - if relevant]

### Performance Patterns

[Insert 5 performance examples - if relevant]

### Testing Patterns

[Insert 5 testing examples - if relevant]
```

#### 3.3: Verify Density Target

```bash
python3 scripts/count-example-density.py installer/global/agents/code-reviewer.md
# Target: ≥40% (was 30%, now should be 40%+)
```

---

### Step 4: Validation (2 hours)

**Automated Check**:
```bash
# Run density script on all agents
python3 scripts/count-example-density.py

# Expected: 15/15 agents ≥40%
```

**Manual Review**:
- [ ] Pick 3 random agents
- [ ] Read Quick Start section
- [ ] Verify: Can you find 10 examples in first 100 lines?
- [ ] Verify: Each example has ✅/❌ comparison?
- [ ] Verify: Rationales are one-sentence and clear?

---

## Testing

### Test 1: Developer Learning Speed

**Before** (Current 20-25% examples):
- Give developer agent file
- Ask: "Show me 5 patterns this agent checks for"
- Time: How long to find 5 patterns?
- **Baseline**: ~5 minutes (lots of reading)

**After** (Target 40-50% examples):
- Give developer updated agent file
- Ask: "Show me 5 patterns this agent checks for"
- Time: How long to find 5 patterns?
- **Target**: ~1 minute (examples visible immediately)

**Success**: 80% time reduction

---

### Test 2: Pattern Recall

**Setup**:
- Developer reads agent file for 10 minutes
- Close file, wait 30 minutes
- Ask: "Name 5 anti-patterns this agent flags"

**Before**: Recall ~30% (mostly theory, not sticky)
**After**: Recall ~70% (examples are memorable)

**Success**: 2x improvement in pattern retention

---

### Test 3: Example Format Consistency

**Automated Check**:
```bash
# Check all examples have language specifiers
grep -A 1 '```' installer/global/agents/*.md | \
grep -v '^```[a-z]' | \
grep '```' | \
wc -l
# Expected: 0 (all code blocks have language)

# Check ✅/❌ format usage
grep -c '### ✅' installer/global/agents/*.md
grep -c '### ❌' installer/global/agents/*.md
# Expected: Equal counts (paired examples)
```

---

## Success Metrics

### Before (Current State)
- **Example density**: 20-25% overall
- **Quick Start examples**: 0-5 per agent
- **Learning time**: 5 min to find patterns
- **Pattern recall**: 30% after 30 min

### After (Target)
- **Example density**: 40-50% overall ✅
- **Quick Start examples**: 10-20 per agent ✅
- **Learning time**: 1 min to find patterns (80% faster) ✅
- **Pattern recall**: 70% after 30 min (2x better) ✅

### ROI Calculation
- **Example creation**: 30 hours × $200/hr = $6,000
- **Time saved per developer**: 4 min/lookup × 10 lookups/week = 40 min/week
- **Annual savings** (10 devs): 347 hours × $200/hr = $69,400
- **ROI**: 11.6:1 in first year

---

## Files to Update

### Priority 1 (Lowest Current Density - Week 1)
1. `installer/global/agents/task-manager.md` (15% → 40%, add 40 examples)
2. `installer/global/agents/code-reviewer.md` (30% → 40%, add 30 examples)
3. `installer/global/agents/test-verifier.md` (est. 25% → 40%, add 35 examples)

### Priority 2 (Medium Density - Week 2)
4. `installer/global/agents/test-orchestrator.md` (35% → 45%, add 20 examples)
5. `installer/global/agents/complexity-evaluator.md` (est. 30% → 40%, add 25 examples)
6. `installer/global/agents/build-validator.md` (est. 30% → 40%, add 25 examples)

### Priority 3 (Close to Target - Week 3)
7-15. Remaining agents (add 10-15 examples each to reach 40-50%)

### New Files to Create
- `examples/security-patterns.md`
- `examples/performance-patterns.md`
- `examples/testing-patterns.md`
- `examples/architecture-patterns.md`
- `scripts/count-example-density.py`

---

## Related Documents

- **Source**: GitHub AGENTS.md best practices
- **Gap Analysis**: `docs/analysis/github-agent-best-practices-comparison.md`
- **Current Examples**: architectural-reviewer.md (40% - template for others)

---

## Workflow

```bash
# 1. Create task
/task-work TASK-AGENT-EXAMPLES

# 2. Audit current density
python3 scripts/count-example-density.py

# 3. Create example library (4 hours)
# - Security patterns
# - Performance patterns
# - Testing patterns
# - Architecture patterns

# 4. Week 1: Priority 1 agents (10 hours)
# Add 30-40 examples to lowest-density agents

# 5. Week 2: Priority 2 agents (10 hours)
# Add 20-30 examples to medium-density agents

# 6. Week 3: Priority 3 agents (10 hours)
# Add 10-15 examples to near-target agents

# 7. Validation (2 hours)
python3 scripts/count-example-density.py
# Expected: 15/15 agents ≥40%

# 8. Complete task
/task-complete TASK-AGENT-EXAMPLES
```

---

## Notes

**Why 40-50% Target?**
- GitHub's research: Developers learn faster from code than descriptions
- Code examples are memorable (visual, concrete)
- Descriptions are forgettable (abstract, theoretical)

**Pattern**: Show → Explain (not Explain → Show)

**Developer Impact**:
- **Before**: "I read 10 paragraphs, still don't know what good code looks like"
- **After**: "I saw 10 examples, I know exactly what to do"

---

**Created**: 2025-11-21
**Estimated Effort**: 36 hours (3 weeks, 12 hours/week)
**Expected Improvement**: Example density 25% → 45% (80% increase)
**Status**: BACKLOG
**Ready for Implementation**: YES
