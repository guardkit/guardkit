---
id: TASK-51B2-C
title: Fix AI-native agent generation in /template-create
status: in_review
created: 2025-11-12T12:45:00Z
updated: 2025-11-12T14:30:00Z
priority: critical
tags: [template-create, ai-native, agents]
complexity: 2
test_results:
  status: passed
  total_tests: 26
  passed: 26
  failed: 0
  coverage_line: 83.0
  coverage_branch: 78.7
  last_run: 2025-11-12T14:30:00Z
architectural_review:
  score: 78
  status: approved_with_recommendations
code_review:
  score: 9.2
  status: approved
---

# Task: Fix AI-native agent generation in /template-create

## Description

**CRITICAL**: The `/template-create` command is not generating custom AI agents despite having an AI-native agent generation pipeline in Phase 5. Agent generation has **never worked properly** and is now blocking complete template creation.

**Current behavior**:
- Phase 5 "Agent Recommendation" runs
- No agents are generated
- Output: "All capabilities covered by existing agents" (incorrect)

**Expected behavior**:
- AI analyzes codebase and identifies capability needs
- AI generates 5-10 custom agents for stack-specific patterns
- Agents saved to template's `agents/` directory
- Generated agents include domain-specialist, api-specialist, ui-specialist, etc.

**Root Cause**: The AI-native agent generation exists (`_ai_identify_all_agents`) but either:
1. AI prompt is not effectively requesting agent identification
2. AI response parsing is failing
3. Fallback to hard-coded detection is being used (wrong approach)
4. Generated agents not being saved properly

This is a **critical** feature for complete template functionality.

## AI-Native Philosophy

**IMPORTANT**: This task follows the AI-native approach. The fix involves:
- ✅ Enhancing AI prompts to request stack-specific agent identification
- ✅ Improving AI instructions for identifying capability gaps
- ✅ Ensuring AI response parsing is robust
- ✅ Making sure generated agents are saved to template
- ❌ NO hard-coded agent pattern detection
- ❌ NO manual agent selection logic

**The AI analyzes the codebase and determines what agents are needed.**

## Acceptance Criteria

- [ ] AI successfully identifies capability needs from codebase analysis
- [ ] AI recommends 5-10 stack-specific agents for typical projects
- [ ] Agent recommendations include diverse types (domain, api, data, ui, test specialists)
- [ ] Generated agents are properly formatted as markdown
- [ ] Agents are saved to template's `agents/` directory
- [ ] Integration test verifies agent generation
- [ ] No fallback to hard-coded detection (AI-native only)

## Implementation Notes

### Fix 1: Enhance AI Prompt for Agent Identification

**File**: `installer/global/lib/agent_generator/agent_generator.py`

Enhance `_build_ai_analysis_prompt()` method to:
- Clearly request 7-12 agent recommendations
- Show example agent format with stack-specific examples
- Explain agents will assist developers with this specific stack
- Request coverage across all architectural layers

### Fix 2: Robust Response Parsing

Ensure `_parse_ai_agent_response()`:
- Handles JSON parsing errors gracefully
- Validates required fields (name, description, priority)
- Logs detailed errors if parsing fails
- Doesn't fall back to hard-coded detection

### Fix 3: Ensure Agents Are Saved

Verify Phase 7 (Package Assembly) copies generated agents to output directory.

### Fix 4: Remove Hard-Coded Fallback

Update `_identify_capability_needs()` to return empty list on failure instead of using hard-coded fallback.

## Test Requirements

- [ ] Test AI agent identification on React TypeScript codebase
- [ ] Test AI agent identification on FastAPI Python codebase
- [ ] Test AI agent identification on .NET MAUI codebase
- [ ] Verify agents are saved to template's `agents/` directory
- [ ] Verify no fallback to hard-coded detection

## Implementation Estimate

**Duration**: 3-5 hours
**Complexity**: 6/10 (Medium-High)

## Success Criteria

✅ AI identifies 7-12 capability needs for typical projects
✅ Agent generation succeeds without falling back to hard-coded
✅ Generated agents are saved to template's `agents/` directory
✅ Agent definitions are properly formatted markdown
✅ Integration tests pass for React, Python, .NET stacks
✅ Generated agents are usable in taskwright workflows
✅ No hard-coded pattern detection used
✅ Maintains AI-native approach throughout

## Test Execution Log

_Automatically populated by /task-work_
