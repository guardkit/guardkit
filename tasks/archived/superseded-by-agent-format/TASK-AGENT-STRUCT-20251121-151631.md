# TASK-AGENT-STRUCT: Restructure All Agents for Early Actionability

**Task ID**: TASK-AGENT-STRUCT-20251121-120000
**Priority**: CRITICAL (P0)
**Status**: BACKLOG
**Created**: 2025-11-21
**Tags**: agents, usability, developer-experience, github-best-practices

---

## Overview

Restructure all 15 global agents to follow GitHub's best practices from their analysis of 2,500+ repositories. Primary goal: **reduce time-to-first-code-example from 150-280 lines to <30 lines**.

**Current Problem**:
- Developers waste 5 minutes per agent lookup finding actionable information
- Code examples buried after 200+ lines of documentation level configuration
- First 150 lines are metadata/config instead of practical guidance
- 10-person team loses 343 hours/year = $68,600/year (at $200/hr)

**GitHub's Key Finding**: 
> "One real code snippet showing your style beats three paragraphs describing it"

**Impact**: This restructuring will save **40 minutes/week per developer** (4 min per lookup × 10 lookups/week)

---

## Acceptance Criteria

### AC1: New Agent File Structure

Every agent file MUST follow this structure:

```markdown
---
[YAML frontmatter - lines 1-11]
---

# Agent Name

## What I Do (Lines 13-20)
[One-sentence role description]
[3-5 bullet points of key responsibilities]

## Quick Start (Lines 21-150)

### ✅ Do This (Good Patterns)
[5-10 copy-pasteable code examples showing approved patterns]

### ❌ Not This (Anti-Patterns)
[5-10 examples showing what will be rejected/flagged]

### Why These Matter
[One-sentence rationale per pattern]

## Boundaries (Lines 151-200)

### ALWAYS (Non-Negotiable)
[5-7 rules that must never be violated]

### NEVER (Will Be Rejected)
[5-7 absolute prohibitions]

### ASK (Escalate to Human)
[3-5 situations requiring human decision]

## When to Use Me (Lines 201-220)
[3-5 specific scenarios with triggers]

---

## How It Works (Lines 221-500)
[Detailed process documentation - MOVE CURRENT CONTENT HERE]

---

## Reference (Lines 501+)
[Documentation level awareness, advanced topics, agent context - MOVE CURRENT CONTENT HERE]
```

**Acceptance**:
- [ ] All 15 global agents follow new structure
- [ ] First code example appears by line 30
- [ ] Role description appears by line 20
- [ ] Quick Start section contains 10-20 code examples
- [ ] Boundaries section uses ALWAYS/NEVER/ASK framework
- [ ] Documentation level details moved to Reference section (500+)

---

### AC2: Time-to-Clarity Metrics

**Target**: Developer understands agent role in ≤10 seconds

**Measurement**:
- [ ] Role visible in first screen (no scrolling)
- [ ] One-sentence "What I Do" at line 13-15
- [ ] Key responsibilities as bullet points (3-5 max)
- [ ] No YAML/config blocks before role description

**Before** (Current):
```
Lines 1-11:  YAML frontmatter ✅ (keep)
Lines 12-150: Documentation level awareness ❌ (move to Reference)
Lines 151-165: Role description ❌ (TOO LATE)
Lines 166+:    Code examples ❌ (TOO LATE)
```

**After** (Target):
```
Lines 1-11:  YAML frontmatter ✅
Lines 13-20: What I Do + responsibilities ✅
Lines 21-150: Quick Start with code examples ✅
Lines 151-200: Boundaries (ALWAYS/NEVER/ASK) ✅
Lines 201-220: When to Use Me ✅
Lines 221+:   Detailed process + Reference ✅
```

---

### AC3: Example:Description Ratio

**Target**: 40-50% code examples in first 200 lines

**Current State** (from analysis):
- task-manager: 15% examples (FAIL)
- code-reviewer: 30% examples (PARTIAL)
- architectural-reviewer: 40% examples (GOOD)

**Measurement**:
- [ ] Quick Start section (lines 21-150): ≥60% code examples
- [ ] Overall file: ≥40% code examples
- [ ] Use ✅/❌ comparison format consistently
- [ ] Each example has one-sentence rationale

**Example Format**:
```markdown
### ❌ DON'T: Magic Numbers
```typescript
if (retries > 3) {  // What is 3?
    throw new Error("Too many retries");
}
```

### ✅ DO: Named Constants
```typescript
const MAX_RETRIES = 3;
if (retries > MAX_RETRIES) {
    throw new Error(`Exceeded ${MAX_RETRIES} retry attempts`);
}
```

**Why**: Self-documenting code prevents maintenance confusion
```

---

### AC4: Documentation Level Condensation

**Target**: Reduce documentation level sections from 140-180 lines to 20-30 lines

**Current Problem**:
- code-reviewer: 180 lines (lines 12-191) on doc levels BEFORE any code
- architectural-reviewer: 140 lines (lines 12-151) on doc levels BEFORE role

**Solution**:
1. Create `.claude/agents/README-AGENT-MODES.md` with full documentation level details
2. Replace 140-180 line sections with 20-30 line summary + link

**Format**:
```markdown
## Documentation Level Support

This agent adapts output based on task complexity:
- **minimal**: Essential info only (complexity 1-3, <15 min tasks)
- **standard**: Balanced detail (complexity 4-6, 15-60 min tasks)
- **comprehensive**: Full analysis (complexity 7-10, >60 min tasks)

The level is automatically determined from task metadata. Manual override:
```bash
/task-work TASK-XXX --doc-level=minimal
```

For implementation details: [README-AGENT-MODES.md](.claude/agents/README-AGENT-MODES.md)
```

**Acceptance**:
- [ ] Documentation level sections ≤30 lines
- [ ] Full details in `.claude/agents/README-AGENT-MODES.md`
- [ ] Link from each agent to README
- [ ] Developer sees role/examples BEFORE doc level details

---

## Files to Update (15 Global Agents)

### Priority 1 (Most Used - Week 1)
1. `installer/global/agents/task-manager.md` (1,156 lines → ~600 lines target)
2. `installer/global/agents/code-reviewer.md` (595 lines → ~400 lines target)
3. `installer/global/agents/architectural-reviewer.md` (867 lines → ~500 lines target)
4. `installer/global/agents/test-verifier.md` (est. 400 lines → ~300 lines target)
5. `installer/global/agents/test-orchestrator.md` (est. 300 lines → ~250 lines target)

### Priority 2 (Supporting Agents - Week 2)
6. `installer/global/agents/build-validator.md`
7. `installer/global/agents/complexity-evaluator.md`
8. `installer/global/agents/pattern-advisor.md`
9. `installer/global/agents/debugging-specialist.md`
10. `installer/global/agents/software-architect.md`

### Priority 3 (Specialized Agents - Week 3)
11. `installer/global/agents/qa-tester.md`
12. `installer/global/agents/devops-specialist.md`
13. `installer/global/agents/security-specialist.md`
14. `installer/global/agents/database-specialist.md`
15. `installer/global/agents/agent-content-enhancer.md`

### New Files to Create
16. `.claude/agents/README-AGENT-MODES.md` (documentation level reference)

---

## Implementation Plan

### Step 1: Create Documentation Level Reference (2 hours)

**File**: `.claude/agents/README-AGENT-MODES.md`

**Content** (extract from all agents):
```markdown
# Agent Documentation Levels

## Overview
Taskwright agents adapt output detail based on task complexity (TASK-035).

## The Three Levels

### Level 1: Minimal (Complexity 1-3)
**When**: Simple, straightforward tasks (<15 minutes)
**Output**: Essential findings only, bullet points
**Example**: "✅ 3 issues found: missing null check (line 42), unused variable (line 67), TODO comment (line 89)"

### Level 2: Standard (Complexity 4-6)
**When**: Typical development tasks (15-60 minutes)
**Output**: Balanced detail with context
**Example**: Includes issue description, code snippet, recommended fix, severity

### Level 3: Comprehensive (Complexity 7-10)
**When**: Complex, high-risk tasks (>60 minutes)
**Output**: Full analysis with alternatives, trade-offs, architectural context
**Example**: Includes issue + alternatives + trade-off analysis + pattern recommendations

## How Agents Determine Level

```python
if complexity_score <= 3:
    level = "minimal"
elif complexity_score <= 6:
    level = "standard"
else:
    level = "comprehensive"
```

## Manual Override

```bash
# Force minimal output (quick feedback)
/task-work TASK-XXX --doc-level=minimal

# Force comprehensive (learning/high-risk)
/task-work TASK-XXX --doc-level=comprehensive
```

## Agent Context Format

Agents receive this metadata:
```xml
<AGENT_CONTEXT>
documentation_level: minimal|standard|comprehensive
complexity_score: 1-10
task_id: TASK-XXX
stack: python|react|maui|go
phase: 2.5|3|4|4.5|5|5.5
</AGENT_CONTEXT>
```

## Output Format Examples

[Include 3 examples per level for each agent type]
```

**Acceptance**:
- [ ] README created with all 3 levels documented
- [ ] Examples from all major agents included
- [ ] Manual override commands documented
- [ ] Agent context format specified

---

### Step 2: Restructure Priority 1 Agents (Week 1, 15 hours)

**Process for each agent** (3 hours per agent × 5 agents):

#### 2.1: Extract Current Sections

**Identify**:
- Lines 1-11: YAML frontmatter (KEEP in place)
- Lines 12-150: Documentation level awareness (MOVE to Reference section)
- Lines 151-165: Role description (MOVE to line 13)
- Lines 166-400: Code examples (MOVE to Quick Start)
- Lines 401-600: Process details (KEEP in "How It Works")
- Lines 601+: Advanced topics (KEEP in Reference)

#### 2.2: Create New Structure

**Template** (`installer/global/agents/TEMPLATE-NEW-STRUCTURE.md`):
```markdown
---
name: [agent-name]
description: [One-sentence description]
---

# [Agent Name]

## What I Do

[One-sentence role description]

**Key Responsibilities**:
- [Responsibility 1 with specific threshold/metric]
- [Responsibility 2 with specific threshold/metric]
- [Responsibility 3 with specific threshold/metric]
- [Responsibility 4 with specific threshold/metric]
- [Responsibility 5 with specific threshold/metric]

**When I Run**: [Phase X.X of /task-work workflow]

## Quick Start

### Common Patterns

#### ✅ DO: [Pattern Name]
```[language]
[Good code example]
```
**Why**: [One-sentence rationale]

#### ❌ DON'T: [Anti-Pattern Name]
```[language]
[Bad code example]
```
**Problem**: [One-sentence explanation]

[Repeat for 10-20 examples]

## Boundaries

### ALWAYS (Non-Negotiable)
These actions happen automatically without asking:
- [Action 1 with threshold: e.g., "Block task if compilation fails"]
- [Action 2 with threshold]
- [Action 3 with threshold]
- [Action 4 with threshold]
- [Action 5 with threshold]

### NEVER (Will Be Rejected)
These actions are prohibited:
- [Prohibition 1: e.g., "Approve code with <80% line coverage"]
- [Prohibition 2]
- [Prohibition 3]
- [Prohibition 4]
- [Prohibition 5]

### ASK (Escalate to Human)
These situations require human decision:
- [Situation 1: e.g., "Complexity >7 + security sensitive"]
- [Situation 2]
- [Situation 3]

## When to Use Me

### ✅ Use This Agent When:
- [Scenario 1 with trigger]
- [Scenario 2 with trigger]
- [Scenario 3 with trigger]

### ❌ Don't Use This Agent For:
- [Scenario 1 + which agent to use instead]
- [Scenario 2 + which agent to use instead]
- [Scenario 3 + which agent to use instead]

## Documentation Level Support

This agent adapts output based on task complexity (minimal/standard/comprehensive).

**Current Level**: Determined from `<AGENT_CONTEXT>` block
**Manual Override**: `/task-work TASK-XXX --doc-level=minimal`

For details: [README-AGENT-MODES.md](.claude/agents/README-AGENT-MODES.md)

---

## How It Works

[MOVE: Current process documentation here - lines 221-500]

### Workflow Overview

```
[Add ASCII/Mermaid diagram showing phase flow]
```

### Integration Points
[Document how this agent integrates with others]

### Quality Gates
[Document thresholds, metrics, decision points]

---

## Reference

### Advanced Topics
[MOVE: Current advanced topics here - lines 501+]

### Agent Context Format
[MOVE: Current agent context documentation here]

### Output Examples by Documentation Level
See [README-AGENT-MODES.md](.claude/agents/README-AGENT-MODES.md) for detailed examples.

### Troubleshooting
[Common issues and solutions]
```

#### 2.3: Populate Template for Each Agent

**For code-reviewer.md**:
1. Copy YAML frontmatter (keep as-is)
2. Write "What I Do" (line 13):
   ```markdown
   Reviews implemented code in Phase 5, enforcing quality standards and requirements compliance.
   ```
3. Extract 10 best code examples from current lines 280-505:
   - Magic numbers vs constants
   - SQL injection prevention
   - Async/await patterns
   - Error handling
   - Testing patterns
   - Security patterns
   - Performance patterns
4. Create Boundaries from implicit rules:
   - ALWAYS: Build verification first, 80% coverage, 100% test pass
   - NEVER: Approve without tests, skip security checks
   - ASK: Complexity >7 + critical, coverage 70-79%
5. Move documentation level section (lines 27-207) to Reference
6. Keep process details in "How It Works"

**Repeat for**:
- architectural-reviewer.md (extract SOLID examples for Quick Start)
- task-manager.md (extract workflow examples for Quick Start)
- test-verifier.md (extract test command examples for Quick Start)
- test-orchestrator.md (extract build commands for Quick Start)

---

### Step 3: Restructure Priority 2 Agents (Week 2, 10 hours)

Repeat Step 2 process for 5 supporting agents (2 hours each)

---

### Step 4: Restructure Priority 3 Agents (Week 3, 10 hours)

Repeat Step 2 process for 5 specialized agents (2 hours each)

---

### Step 5: Validation & Testing (Week 4, 5 hours)

#### 5.1: Automated Checks (2 hours)

**Create**: `scripts/validate-agent-structure.py`

```python
#!/usr/bin/env python3
"""Validate agent files follow new structure."""

def validate_agent(file_path: Path) -> dict:
    """
    Check agent file against structure requirements.
    
    Returns dict with:
    - first_code_line: line number of first code block
    - role_description_line: line number of "What I Do"
    - has_boundaries: bool
    - has_quick_start: bool
    - example_ratio: float (0.0-1.0)
    """
    with open(file_path) as f:
        lines = f.readlines()
    
    results = {
        "file": file_path.name,
        "total_lines": len(lines),
        "first_code_line": None,
        "role_line": None,
        "has_boundaries": False,
        "has_quick_start": False,
        "code_lines": 0,
        "text_lines": 0
    }
    
    in_code_block = False
    for i, line in enumerate(lines, 1):
        # Find first code block
        if line.strip().startswith("```") and not in_code_block:
            if results["first_code_line"] is None:
                results["first_code_line"] = i
            in_code_block = True
            continue
        elif line.strip().startswith("```") and in_code_block:
            in_code_block = False
            continue
        
        # Count code vs text
        if in_code_block:
            results["code_lines"] += 1
        else:
            results["text_lines"] += 1
        
        # Find key sections
        if "## What I Do" in line:
            results["role_line"] = i
        if "## Boundaries" in line:
            results["has_boundaries"] = True
        if "## Quick Start" in line:
            results["has_quick_start"] = True
    
    # Calculate ratio
    total = results["code_lines"] + results["text_lines"]
    results["example_ratio"] = results["code_lines"] / total if total > 0 else 0.0
    
    return results

def main():
    agents_dir = Path("installer/global/agents")
    results = []
    
    for agent_file in agents_dir.glob("*.md"):
        if agent_file.name == "TEMPLATE-NEW-STRUCTURE.md":
            continue
        result = validate_agent(agent_file)
        results.append(result)
        
        # Check against targets
        passed = True
        issues = []
        
        if result["first_code_line"] is None or result["first_code_line"] > 50:
            passed = False
            issues.append(f"❌ First code at line {result['first_code_line']} (target: <50)")
        else:
            issues.append(f"✅ First code at line {result['first_code_line']}")
        
        if result["role_line"] is None or result["role_line"] > 20:
            passed = False
            issues.append(f"❌ Role at line {result['role_line']} (target: <20)")
        else:
            issues.append(f"✅ Role at line {result['role_line']}")
        
        if not result["has_boundaries"]:
            passed = False
            issues.append("❌ Missing Boundaries section")
        else:
            issues.append("✅ Has Boundaries section")
        
        if not result["has_quick_start"]:
            passed = False
            issues.append("❌ Missing Quick Start section")
        else:
            issues.append("✅ Has Quick Start section")
        
        if result["example_ratio"] < 0.30:
            passed = False
            issues.append(f"❌ Example ratio {result['example_ratio']:.1%} (target: ≥40%)")
        else:
            issues.append(f"✅ Example ratio {result['example_ratio']:.1%}")
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status} - {result['file']}")
        for issue in issues:
            print(f"  {issue}")
    
    # Summary
    passed_count = sum(1 for r in results if all([
        r["first_code_line"] and r["first_code_line"] <= 50,
        r["role_line"] and r["role_line"] <= 20,
        r["has_boundaries"],
        r["has_quick_start"],
        r["example_ratio"] >= 0.30
    ]))
    
    print(f"\n{'='*70}")
    print(f"SUMMARY: {passed_count}/{len(results)} agents passed")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
```

**Run**:
```bash
python3 scripts/validate-agent-structure.py
```

**Target**: 15/15 agents pass

---

#### 5.2: Manual Review (2 hours)

**Checklist per agent**:
- [ ] Open agent file, read first 100 lines
- [ ] Time yourself: Can you understand role in <10 seconds?
- [ ] Can you find a copy-pasteable code example in first screen?
- [ ] Are boundaries clear (ALWAYS/NEVER/ASK)?
- [ ] Is documentation level section ≤30 lines?
- [ ] Does "How It Works" section have process details?
- [ ] Does Reference section have advanced topics?

**Review 5 random agents**, fix any issues found

---

#### 5.3: Developer Testing (1 hour)

**A/B Test**:
1. Give 3 developers OLD code-reviewer.md
2. Give 3 developers NEW code-reviewer.md
3. Ask: "What does this agent do? Show me an example."
4. Time: How long to answer?

**Target**:
- OLD: ~5 minutes average
- NEW: ~1 minute average (80% improvement)

**Survey Questions**:
- "How clear was the agent's role?" (1-10)
- "How quickly did you find an actionable example?" (1-10)
- "How clear were the boundaries (what it will/won't do)?" (1-10)

**Target**: ≥8/10 average on all questions

---

## Success Metrics

### Before Restructuring (Baseline)
- **Time to clarity**: 15-20 seconds (reading through config)
- **Time to first code**: 150-280 lines
- **Example density**: 20-25% overall
- **Boundary clarity**: 6-7/10 (implicit in text)
- **Developer satisfaction**: (baseline survey)

### After Restructuring (Target)
- **Time to clarity**: ≤10 seconds (50% improvement) ✅
- **Time to first code**: ≤30 lines (80-90% improvement) ✅
- **Example density**: 40-50% overall (2x improvement) ✅
- **Boundary clarity**: 9-10/10 (explicit ALWAYS/NEVER/ASK) ✅
- **Developer satisfaction**: ≥8/10 on clarity/actionability/boundaries ✅

### ROI Calculation
- **Developer time saved**: 4 min/lookup × 10 lookups/week × 10 devs = 6.6 hours/week
- **Annual savings**: 343 hours × $200/hr = **$68,600**
- **Restructure effort**: 40 hours × $200/hr = **$8,000**
- **ROI**: **8.6:1 in first year**, **9:1 payback in 6 weeks**

---

## Testing

### Automated Tests

```bash
# 1. Validate all agents pass structure checks
python3 scripts/validate-agent-structure.py
# Expected: 15/15 agents pass

# 2. Check first code line is early
for agent in installer/global/agents/*.md; do
    first_code=$(grep -n '```' "$agent" | head -1 | cut -d: -f1)
    if [ "$first_code" -gt 50 ]; then
        echo "❌ $agent: First code at line $first_code (target: <50)"
    else
        echo "✅ $agent: First code at line $first_code"
    fi
done

# 3. Check all agents have Boundaries section
for agent in installer/global/agents/*.md; do
    if grep -q "## Boundaries" "$agent"; then
        echo "✅ $agent: Has Boundaries"
    else
        echo "❌ $agent: Missing Boundaries"
    fi
done

# 4. Check Quick Start sections exist
for agent in installer/global/agents/*.md; do
    if grep -q "## Quick Start" "$agent"; then
        echo "✅ $agent: Has Quick Start"
    else
        echo "❌ $agent: Missing Quick Start"
    fi
done
```

### Manual Testing

**Test Scenario**: New developer joins team

1. Give them restructured code-reviewer.md
2. Ask: "Review this pull request using this agent guide"
3. Observe: How quickly do they understand what to look for?

**Success Criteria**:
- Finds first code example in <30 seconds
- Understands boundaries in <1 minute
- Can articulate agent role in <10 seconds
- Satisfaction: ≥8/10

---

## Related Documents

**Source Analysis**:
- GitHub Blog: "How to write a great AGENTS.md" (2,500+ repo analysis)
- `docs/analysis/github-agent-best-practices-comparison.md` (our gap analysis)

**Implementation Reviews**:
- Architectural review (software-architect agent)
- Code quality review (code-reviewer agent)
- QA testing review (qa-tester agent)

---

## Workflow

```bash
# 1. Create task
/task-work TASK-AGENT-STRUCT

# 2. Week 1: Priority 1 agents
# - Create README-AGENT-MODES.md
# - Restructure top 5 agents

# 3. Week 2: Priority 2 agents
# - Restructure 5 supporting agents

# 4. Week 3: Priority 3 agents
# - Restructure 5 specialized agents

# 5. Week 4: Validation
# - Run automated checks
# - Manual review
# - Developer testing
# - A/B test results

# 6. Complete task
/task-complete TASK-AGENT-STRUCT
```

---

## Notes

**Why This Matters**:
GitHub's research of 2,500+ repositories found that:
1. **Specificity > Vagueness**: We're already good at this ✅
2. **Show > Tell**: We fail this (20% examples vs 50% recommended) ❌
3. **Examples First**: We fail this (examples at line 150-280 vs <30) ❌
4. **Explicit Boundaries**: We fail this (no ALWAYS/NEVER/ASK) ❌

This restructuring addresses our 3 critical gaps while preserving our architectural strengths.

**Developer Impact**:
- **Before**: "I spent 5 minutes finding an example in the docs"
- **After**: "I found 10 examples in the first screen"

**Business Impact**:
- **Cost**: 40 hours ($8,000)
- **Savings**: 343 hours/year ($68,600/year)
- **Payback**: 6 weeks

---

**Created**: 2025-11-21
**Estimated Effort**: 40 hours (3 weeks)
**Expected ROI**: 8.6:1 in first year
**Status**: BACKLOG
**Ready for Implementation**: YES
