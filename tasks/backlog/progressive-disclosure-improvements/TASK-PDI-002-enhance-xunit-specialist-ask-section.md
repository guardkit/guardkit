---
id: TASK-PDI-002
title: Enhance xunit-nsubstitute-testing-specialist ASK section
status: backlog
created: 2025-12-12T11:45:00Z
updated: 2025-12-12T11:45:00Z
priority: low
tags: [agent-enhance, boundaries, testing, xunit]
complexity: 2
parent_review: TASK-REV-PD01
implementation_mode: direct
---

# Task: Enhance xunit-nsubstitute-testing-specialist ASK section

## Description

The xunit-nsubstitute-testing-specialist agent currently has only 3 ASK items, which is the minimum requirement (3-5). Add 1-2 more ASK scenarios to bring it to 4-5 items for better coverage of edge cases.

## Problem

Current ASK section has only 3 items:
```markdown
### ASK
- ⚠️ Item 1
- ⚠️ Item 2
- ⚠️ Item 3
```

Target: 4-5 items to match other agents (most have 5).

## Acceptance Criteria

- [ ] ASK section has 4-5 items
- [ ] New items follow the ⚠️ emoji format
- [ ] New items are relevant to xUnit/NSubstitute testing decisions
- [ ] Items represent genuine edge cases requiring human judgment

## Suggested Additional ASK Items

Based on common xUnit/NSubstitute decision points:

1. **Test isolation vs integration**: "⚠️ Test requires real database connection: Ask if should use in-memory Realm or actual database for integration test"

2. **Mock complexity**: "⚠️ Mock setup exceeds 15 lines: Ask if test is testing too much or if mock builder pattern would improve readability"

3. **Flaky test handling**: "⚠️ Test fails intermittently: Ask if async timing issue, test isolation problem, or genuine race condition in code under test"

4. **Coverage thresholds**: "⚠️ Branch coverage below 75% but line coverage above 80%: Ask if missing edge case tests are critical or acceptable given risk level"

## Files to Update

1. `~/.agentecflow/templates/mydrive/agents/xunit-nsubstitute-testing-specialist.md`
2. After update, re-run `guardkit init` to propagate changes

## Notes

- Low priority - current state meets minimum requirements
- Improves consistency with other agents
- Direct edit - no complex implementation needed
