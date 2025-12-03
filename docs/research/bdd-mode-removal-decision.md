# Decision: Remove BDD Mode from GuardKit

**Date:** 2025-11-02
**Status:** Proposed
**Decision Maker:** Project Maintainer

## Context

The `/task-work` command currently documents three development modes:
1. **Standard Mode** - Implementation and tests together
2. **TDD Mode** - Tests first, then implementation
3. **BDD Mode** - Gherkin scenarios → Implementation

However, investigation reveals:
- BDD mode is **documented** but **not fully implemented**
- BDD functionality depends on require-kit installation
- The `bdd-generator` agent is designed for EARS → Gherkin conversion
- No evidence of actual BDD mode usage in the wild

## The Problem

### 1. Scope Creep Without Value

**What BDD Mode Would Actually Require:**

| Component | Effort | Complexity | Maintenance |
|-----------|--------|------------|-------------|
| Multi-framework support (pytest-bdd, SpecFlow, Cucumber, etc.) | 15-20h | High | Ongoing |
| Step definition generation | 10-15h | Medium | Medium |
| Feature implementation from steps | 10-15h | High | Low |
| BDD test execution & parsing | 5-10h | Medium | Ongoing |
| Edge cases (outlines, backgrounds, tags) | 5-10h | High | Medium |
| **TOTAL** | **45-70h** | **High** | **Medium-High** |

### 2. Low Expected Usage

**Questions revealing low demand:**
- How many guardkit users write Gherkin scenarios?
- Of those, how many DON'T use require-kit?
- Of those, how many want AI to implement from scenarios vs just writing code?

**Realistic answer:** Probably <5% of users

**Alternative:** Those users can:
- Use require-kit (full EARS → BDD → Implementation flow)
- Use Standard mode with detailed acceptance criteria
- Use TDD mode for test-first development

### 3. Conceptual Mismatch

**BDD in the real world:**
- **With formal requirements:** EARS → Gherkin → Implementation (require-kit)
- **Without formal requirements:** Just write code with good tests (Standard/TDD)

**Standalone BDD mode** (Gherkin without EARS) is an edge case:
- User manually writes .feature files
- AI generates step definitions
- AI implements features

**But this is solving a problem few people have.**

### 4. Maintenance Burden

BDD frameworks evolve frequently:
- **pytest-bdd** - Python (different versions have breaking changes)
- **SpecFlow** - C#/.NET (v3 → v4 major refactor)
- **Cucumber.js** - TypeScript/JavaScript (v7 → v8 → v9)
- **Cucumber-JVM** - Java

Each requires:
- Different step definition syntax
- Different test execution patterns
- Different output parsing
- Ongoing compatibility testing

## Alternatives Considered

### Option A: Split BDD into Two Concerns ❌
**Create bdd-scenario-implementer in guardkit**
- **Pros:** Full BDD support without require-kit dependency
- **Cons:** 45-70 hours implementation, high complexity, ongoing maintenance
- **Verdict:** Not worth the effort for low expected usage

### Option B: Keep BDD Mode as require-kit Exclusive ❌
**Only support BDD mode when require-kit installed**
- **Pros:** Leverages existing bdd-generator
- **Cons:** Confusing UX (mode sometimes available, sometimes not)
- **Verdict:** Creates inconsistent behavior

### Option C: Remove BDD Mode Entirely ✅ RECOMMENDED
**Document removal, focus on Standard/TDD modes**
- **Pros:** Simplifies codebase, clear messaging, reduces maintenance
- **Cons:** Users wanting BDD must use require-kit
- **Verdict:** Pragmatic choice for lightweight system

## Decision

**Remove BDD mode from guardkit.**

### Rationale

1. **Simplicity over completeness**
   - GuardKit is "lightweight AI-assisted development"
   - BDD mode adds significant complexity
   - Standard and TDD modes cover 95% of use cases

2. **Clear separation of concerns**
   - **require-kit:** Formal requirements engineering (EARS → BDD)
   - **guardkit:** Pragmatic task workflow (Standard/TDD)

3. **Avoid incomplete implementations**
   - BDD mode is currently documented but non-functional
   - Better to remove than leave broken/misleading docs

4. **Resource allocation**
   - 45-70 hours better spent on:
     - Improving test enforcement
     - Enhancing architectural review
     - Better multi-stack support
     - Actual user-requested features

## Implementation Plan

### Phase 1: Documentation Cleanup (30 minutes)

1. **Remove BDD mode from `/task-work` command spec**
   - File: `installer/global/commands/task-work.md`
   - Remove lines 2317-2344 (BDD mode section)
   - Update examples to show only Standard and TDD modes

2. **Update CLAUDE.md**
   - Remove BDD mode references
   - Clarify: "For BDD workflows, use require-kit"

3. **Update task-manager agent**
   - File: `.claude/agents/task-manager.md`
   - Remove BDD mode implementation section (lines 120-145)
   - Keep only Standard and TDD mode logic

4. **Add migration note**
   - Document why BDD mode was removed
   - Point users to require-kit for BDD workflows

### Phase 2: Code Cleanup (15 minutes)

1. **Remove feature detection for BDD**
   - Keep `supports_bdd()` function (returns require-kit status)
   - Update docstring: "BDD generation requires require-kit"

2. **Remove unused BDD templates**
   - Keep: `installer/global/instructions/core/bdd-gherkin.md` (educational)
   - Keep: `bdd-generator` agent (only loads with require-kit)
   - Remove: Any guardkit-specific BDD mode logic

### Phase 3: Communication (ongoing)

**Messaging:**
> **GuardKit focuses on Standard and TDD development modes.**
>
> For Behavior-Driven Development (BDD) workflows:
> - Use **require-kit** for full EARS → Gherkin → Implementation flow
> - Or write Gherkin scenarios manually and use Standard mode
>
> GuardKit's strength is lightweight, pragmatic task workflow—not formal requirements engineering.

## Risks and Mitigations

### Risk 1: User Expectations
**Risk:** Some users may expect BDD mode based on docs
**Mitigation:**
- Clear communication in changelog
- Update docs to point to require-kit
- Provide migration guide for existing users (if any)

### Risk 2: Lost Capability
**Risk:** Users wanting BDD must install require-kit
**Mitigation:**
- This is by design—require-kit provides superior BDD workflow
- Standalone BDD without EARS is edge case
- Users can still write scenarios and implement in Standard mode

### Risk 3: Incomplete Removal
**Risk:** References to BDD mode linger in docs
**Mitigation:**
- Comprehensive grep for "mode=bdd", "BDD mode", etc.
- Update all discovered references
- Add to documentation review checklist

## Success Criteria

After implementation:
- [ ] No references to `--mode=bdd` in command specs
- [ ] No BDD mode implementation in task-manager
- [ ] CLAUDE.md clearly states: "BDD requires require-kit"
- [ ] Migration note added to docs
- [ ] Changelog entry explaining removal
- [ ] All tests passing (no broken references)

## Future Considerations

**If demand emerges later:**
- We have Option A design doc as reference
- Implementation would still require 45-70 hours
- Maintenance burden would still apply
- Would need 3+ confirmed users with real use cases

**Until then:** Keep it simple. Standard + TDD modes are sufficient.

## Related Documents

- [Option A Design](./bdd-mode-design-option-a.md) - Full implementation spec if needed later
- [Feature Detection](../../installer/global/lib/feature_detection.py) - `supports_bdd()` logic
- [Task Work Command](../../installer/global/commands/task-work.md) - Command specification

## Approval

- [x] Technical design reviewed
- [ ] Decision approved by maintainer
- [ ] Implementation plan ready
- [ ] Communication plan ready

---

## Appendix: What Users Lose

**Removed capability:**
```bash
/task-work TASK-042 --mode=bdd
# Error: BDD mode is not available
# For BDD workflows, install require-kit or use Standard mode
```

**Available alternatives:**

1. **Use require-kit for full BDD workflow:**
   ```bash
   # In require-kit
   /generate-bdd REQ-042  # Generate scenarios from EARS
   /task-work TASK-042 --mode=bdd  # Implement scenarios
   ```

2. **Use Standard mode with detailed acceptance criteria:**
   ```bash
   # In guardkit
   /task-create "Implement login feature"
   # Add detailed acceptance criteria to task
   /task-work TASK-042  # Standard mode
   ```

3. **Use TDD mode for test-first development:**
   ```bash
   /task-work TASK-042 --mode=tdd
   # AI writes tests first, then implements
   ```

**What they DON'T lose:**
- Quality gates
- Test enforcement
- Architectural review
- All the value of guardkit

**What they need require-kit for:**
- EARS requirements
- BDD scenario generation
- Formal requirements engineering
- Epic/feature hierarchy

## Conclusion

**Remove BDD mode from guardkit.**

It's the pragmatic choice for a lightweight system. Users needing BDD workflows should use require-kit, which provides a complete EARS → BDD → Implementation flow. GuardKit should focus on what it does well: simple, quality-first task workflow with Standard and TDD modes.
