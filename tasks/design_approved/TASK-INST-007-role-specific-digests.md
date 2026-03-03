---
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
autobuild_state:
  base_branch: main
  current_turn: 1
  last_updated: '2026-03-02T13:47:50.465823'
  max_turns: 30
  started_at: '2026-03-02T13:36:04.692385'
  turns:
  - coach_success: true
    decision: approve
    feedback: null
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-03-02T13:36:04.692385'
    turn: 1
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
complexity: 5
dependencies:
- TASK-INST-001
feature_id: FEAT-INST
id: TASK-INST-007
implementation_mode: task-work
parent_review: TASK-REV-2FE2
status: design_approved
task_type: feature
title: Implement role-specific digest system
wave: 2
---

# Task: Implement Role-Specific Digest System

## Description

Create the role-specific digest system that replaces the full always-on rules bundle with minimal, targeted system prompts for each agent role. Includes digest files, validation, loading, and prompt profile switching.

## Requirements

### Stack-Agnostic Requirement

Digest content MUST be technology-agnostic. AutoBuild runs against any project stack (Python, TypeScript, .NET, Go, Rust, etc.). Digests must NOT reference specific tools (e.g., "run pytest"), test frameworks, or language idioms. Use generic terms like "run tests", "verify compilation", "check coverage". Stack-specific details are handled by task-work's stack specialist, not the digest.

### Digest Files

Create four role-specific digest files under `.guardkit/digests/`:

1. **player.md** (~300-600 tokens):
   - Implementation rules: minimal changes, no unrelated refactoring
   - Stop and ask if ambiguous
   - Do not claim untested outcomes
   - Output contract: summary, files changed, how to verify, risks/assumptions

2. **coach.md** (~300-600 tokens):
   - Validation rules: strict comparison against acceptance criteria
   - Categorise failures using controlled vocabulary
   - Return minimal next action
   - Output contract: verdict (pass|fail), failure category, issues list, next action

3. **resolver.md** (~300-600 tokens):
   - Root cause analysis rules: retrieval-first before guessing
   - Structured remediation plan
   - Identify what context to persist back to Graphiti

4. **router.md** (~300-600 tokens):
   - Model selection rules: smallest capable model
   - Escalate to frontier for cross-cutting/security/repeated failures

### DigestValidator

- Validate token count of each digest at startup (fail-fast)
- Maximum 700 tokens per digest (boundary from BDD spec)
- Exactly 700 tokens: accepted without warning
- 701+ tokens: warning indicating digest exceeds maximum
- Missing digest file: clear error (NOT silent fallback to full rules bundle)
- Token counting via tiktoken (or word-based estimate as fallback)

### DigestLoader

- Load role-specific digest during prompt assembly
- Select digest based on `agent_role` parameter
- Return digest content as string for injection into system prompt

### Integration with Prompt Builder Pattern

The Player's prompt is assembled in `_build_autobuild_implementation_prompt()` which loads `autobuild_execution_protocol.md` via `load_protocol()`. The DigestLoader should integrate at this assembly point:
- Player: Digest injected as a preamble section in `_build_autobuild_implementation_prompt()`
- Coach: Digest injected as a preamble section in `_build_coach_prompt()`
- Resolver/Router: Digest injected in their respective prompt builders (when implemented)

The `prompt_profile` is determined at assembly time based on which context sources are included (digest only, digest + Graphiti context section, digest + rules bundle, etc.).

### Prompt Profile Switching

Support four profiles:
- `digest_only`: Role digest only, no rules bundle, no Graphiti
- `digest+graphiti`: Role digest plus retrieved Graphiti context
- `digest+rules_bundle`: Role digest plus full rules bundle (Phase 1 baseline)
- `digest+graphiti+rules_bundle`: Transitional phase

### Phase 1 Migration

- Keep full rules bundle alongside digest (no removal yet)
- Default profile: `digest+rules_bundle`
- Instrumentation events tagged with active prompt profile
- No two role digests should be identical

## Acceptance Criteria

- [ ] Four digest files created (player, coach, resolver, router)
- [ ] Each digest under 700 tokens
- [ ] DigestValidator accepts exactly 700 tokens, warns at 701+
- [ ] Missing digest file produces clear error (no silent fallback)
- [ ] DigestLoader returns correct digest for each role
- [ ] Prompt profile switching supports all four profiles
- [ ] Phase 1: full rules bundle injected alongside digest
- [ ] No two digests are identical
- [ ] Token counting implemented (tiktoken or word-based fallback)
- [ ] Digest content is stack-agnostic (no Python/Node/.NET-specific references)
- [ ] Unit tests cover validation boundaries (700/701), loading, profiles

## File Location

- Digest files: `.guardkit/digests/player.md`, `coach.md`, `resolver.md`, `router.md`
- Validator/Loader: `guardkit/orchestrator/instrumentation/digests.py`
- Prompt profile: `guardkit/orchestrator/instrumentation/prompt_profile.py`

## Test Location

`tests/orchestrator/instrumentation/test_digests.py`