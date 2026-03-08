---
id: TASK-INST-014
title: Create role-specific digest files for Player, Coach, Resolver, Router
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 5
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-INST-007
autobuild:
  enabled: true
  max_turns: 5
  mode: standard
consumer_context:
- task: TASK-INST-007
  consumes: DIGEST_SYSTEM
  framework: DigestLoader + DigestValidator
  driver: guardkit.orchestrator.instrumentation.digests
  format_note: Files must be at .guardkit/digests/{role}.md; validated at startup with 700 token hard limit
status: completed
completed: 2026-03-08T12:00:00Z
---

# Task: Create Role-Specific Digest Files

## Description

The digest loading and validation infrastructure (TASK-INST-007) is merged, but the actual digest content files do not exist yet. Without these files, `DigestLoader.load()` raises `DigestLoadError` and the prompt profile system cannot switch away from the full rules bundle.

This task creates the four role-specific digest markdown files that serve as minimal system prompts (~300–600 tokens each) for the Player, Coach, Resolver, and Router agent roles. These are prompt engineering artefacts, not code.

## Scope

This task ONLY creates:
- `.guardkit/digests/player.md`
- `.guardkit/digests/coach.md`
- `.guardkit/digests/resolver.md`
- `.guardkit/digests/router.md`

It does NOT:
- Modify the DigestLoader or DigestValidator code (already merged)
- Change prompt assembly logic (PromptProfileAssembler already handles digests)
- Switch the default prompt profile (remains `digest+rules_bundle` until A/B testing validates)
- Modify any Python source files

## Requirements

### Token Budget

- Target: 300–600 tokens per digest
- Hard limit: 700 tokens (enforced by `DigestValidator`)
- Token counting uses tiktoken `cl100k_base` encoding (with word-based fallback)

### Player Digest (`player.md`)

Core directives for the implementation agent:
- Make minimal, focused changes — only what the task requires
- No unrelated refactoring, no scope creep
- Stop and ask if requirements are ambiguous
- Do not claim untested outcomes
- Output contract: summary, files changed, how to verify, risks/assumptions

### Coach Digest (`coach.md`)

Core directives for the validation agent:
- Strict comparison against task acceptance criteria
- Categorise failures using controlled vocabulary: `knowledge_gap | context_missing | spec_ambiguity | test_failure | env_failure | dependency_issue | rate_limit | timeout | tool_error | other`
- Return minimal actionable feedback
- Output contract: verdict (pass|fail), failure category, issues list, next action

### Resolver Digest (`resolver.md`)

Core directives for the root cause analysis agent:
- Retrieval-first: query knowledge graph before guessing
- Structured remediation plan with specific file/line targets
- Identify what context should be persisted back to Graphiti
- Escalate to human if confidence is low after retrieval

### Router Digest (`router.md`)

Core directives for the model selection agent:
- Default to smallest capable model
- Escalate to frontier only for: cross-cutting architectural changes, repeated failures (3+ turns), security-sensitive logic
- Log routing decision rationale for instrumentation

### File Format

Each digest file should be a concise markdown document with:
- A brief `# {Role} Agent Digest` heading
- A `## Directives` section with numbered rules
- A `## Output Contract` section specifying required output fields
- No examples, no verbose explanations — these are operational prompts, not documentation

## Acceptance Criteria

- [x] All four digest files exist at `.guardkit/digests/{role}.md`
- [x] Each file is under 700 tokens (validated by `DigestValidator.validate_all()`)
- [x] Each file is between 300–600 tokens (target range)
- [x] `DigestLoader.load(role)` returns content without raising for all four roles
- [x] `DigestValidator.validate_all()` passes without warnings
- [x] Content accurately reflects the role descriptions from the feature input document
- [x] Failure category vocabulary in coach.md matches `FailureCategory` enum in schemas.py

## File Location

New files:
- `.guardkit/digests/player.md`
- `.guardkit/digests/coach.md`
- `.guardkit/digests/resolver.md`
- `.guardkit/digests/router.md`

## Test Location

`tests/orchestrator/instrumentation/test_digest_content.py` — validates token counts and loading for all four files

## Completion Notes

### Changes Made

1. **Fixed `coach.md`** (`.guardkit/digests/coach.md:10`) - Added 4 missing FailureCategory values (`rate_limit`, `timeout`, `tool_error`, `other`) to the controlled vocabulary line. The existing list only had 6 of 10 categories.

2. **Created `test_digest_content.py`** (`tests/orchestrator/instrumentation/test_digest_content.py`) - 30 tests across 5 test classes:
   - `TestDigestTokenBudgets` - Validates 300-600 target range and 700 hard limit
   - `TestDigestLoaderIntegration` - Verifies `DigestLoader.load()` for all roles
   - `TestDigestValidatorIntegration` - Verifies `validate_all()` passes without warnings
   - `TestDigestContentAccuracy` - Checks output contract fields and key directives
   - `TestCoachFailureCategoryVocabulary` - Ensures all 10 FailureCategory values present

### Test Results

- 30/30 new tests passed
- 45/45 existing digest tests passed (no regressions)
