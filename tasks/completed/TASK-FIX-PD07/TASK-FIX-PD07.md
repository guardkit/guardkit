---
id: TASK-FIX-PD07
title: Fix agent-enhance output formatting issues from TASK-REV-TC03 review
status: completed
created: 2024-12-07T12:35:00Z
updated: 2024-12-07T13:30:00Z
completed: 2024-12-07T13:30:00Z
priority: medium
tags: [fix, progressive-disclosure, agent-enhance, formatting]
complexity: 2
related_tasks: [TASK-REV-TC03]
estimated_effort: 15min
actual_effort: 20min
completed_location: tasks/completed/TASK-FIX-PD07/
---

# Fix: Agent-Enhance Output Formatting Issues

## Background

Review TASK-REV-TC03 identified 3 minor formatting/documentation issues in the agent-enhance output that should be addressed in the enhancement workflow.

**Source**: [TASK-REV-TC03 Review Report](.claude/reviews/TASK-REV-TC03-review-report.md)
**Score**: 8.65/10 (issues are minor)

## Issues to Fix

### 1. Add Emoji Prefixes to Boundary Rules

**Current** (in enhanced agent files):
```markdown
### ALWAYS
- Guard all CRUD operations with auth.currentUser check
```

**Expected**:
```markdown
### ALWAYS
- ✅ Guard all CRUD operations with auth.currentUser check
```

**Files Affected**:
- Agent enhancement template/prompts
- All enhanced agent files (core files)

**Effort**: 5 minutes

### 2. Use Discovered Template Paths (Not Hardcoded)

**Issue**: The extended reference showed assumed paths (`templates/firebase/`) instead of actual discovered paths.

**Root Cause**: The AI may be inferring paths based on content rather than using the actual file paths discovered during template analysis.

**Fix**: Ensure agent-content-enhancer prompts explicitly instruct to:
- Use the actual file paths from the discovery phase
- Never assume or infer paths based on file content or naming conventions
- Reference the manifest.json or discovery results for accurate paths

**Effort**: 5 minutes

### 3. Derive Framework Context from Codebase Analysis (Not Hardcoded)

**Issue**: Some examples referenced React patterns, but the actual codebase uses different patterns.

**Root Cause**: The AI may have included generic examples from training data rather than deriving patterns purely from the analyzed codebase.

**Fix**: Ensure agent-content-enhancer prompts explicitly instruct to:
- Derive ALL examples from the actual template source files provided
- Never include framework-specific patterns not found in the analyzed code
- If framework-specific integration examples are needed, analyze package.json/imports to determine actual frameworks used
- State what was found in analysis, not what might be expected

**Effort**: 5 minutes

## Acceptance Criteria

- [x] Boundary rules in enhanced agents use ✅/❌/⚠️ emoji prefixes
- [x] Template paths in Related Templates section come from actual discovery (not inferred)
- [x] All code examples are derived from analyzed source files (no generic training data patterns)
- [x] Changes applied to agent-content-enhancer agent prompts

## Implementation Notes

These fixes should be applied to:
1. `installer/global/agents/agent-content-enhancer.md` - Update enhancement prompts ✅
2. Optionally: Re-run enhancement on kartlog template to verify fixes

## Implementation Summary

**Files Modified**:
1. `installer/global/agents/agent-content-enhancer.md`:
   - Added explicit "CRITICAL - EMOJI PREFIXES ARE MANDATORY" section with exact format requirements
   - Added new "Critical Content Guidelines" section with:
     - "Use Discovered Paths Only" guidelines with examples
     - "Derive Framework Context From Codebase Analysis" guidelines with examples

2. `installer/global/agents/agent-content-enhancer-ext.md`:
   - Updated boundary section with mandatory emoji prefix note
   - Added new "Critical Content Guidelines (TASK-FIX-PD07)" section with detailed requirements

3. `installer/global/lib/agent_enhancement/prompt_builder.py`:
   - Added 3 new critical notes to the enhancement prompt:
     - Emoji prefixes mandatory
     - Use discovered paths only
     - Derive framework context from code

## Test Plan

1. Run `/agent-enhance` on a test agent
2. Verify boundary rules have emoji prefixes
3. Verify template paths match actual discovered file locations
4. Verify all code examples can be traced back to analyzed source files
5. Verify no generic framework patterns (React/Vue/Angular) appear unless actually found in codebase
