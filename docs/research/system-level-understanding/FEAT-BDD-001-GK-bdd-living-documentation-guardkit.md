# Feature: BDD Living Documentation — GuardKit Side

> **Feature ID**: FEAT-BDD-001-GK
> **Priority**: P1 (Phase 3)
> **Estimated Effort**: 2-3 days
> **Target Repo**: GuardKit
> **Dependencies**: FEAT-GE-001 (Graphiti entities), FEAT-BDD-001-RK (RequireKit BDD Graphiti push)

---

## Summary

Integrate BDD scenario awareness into GuardKit's task execution workflow — `/task-work` reads relevant BDD scenarios before implementation, the AutoBuild coach validates against them during player-coach loops, and `/task-complete` updates scenario verification status in Graphiti. This is the **read and verify side** of the BDD feedback loop — GuardKit consumes the BDD scenarios that RequireKit creates, uses them to prevent regressions during implementation, and feeds verification results back to the knowledge graph.

The core value proposition is preventing the "locally correct but globally wrong" problem at the behavioural level: when Claude implements a task, it should know which existing behaviours are validated by BDD scenarios and must not be broken. When the task is complete, those scenarios are re-verified, and their status is updated — closing the loop.

---

## Current State

### What Exists

- **`/task-work`** — Implementation command with Phase 1 (understanding) and Phase 2 (implementation planning). Phase 2 already queries Graphiti for feature specs and project context.
- **`/task-complete`** — Finalization command that runs quality gates (lint, tests, type check). Already validates implementation against acceptance criteria.
- **AutoBuild player-coach loop** — Coach validates player output against acceptance criteria and quality gates. Coach already receives feature context from Graphiti via GR-006.
- **Graphiti integration** — Job-specific context retrieval is operational. `{project}__feature_specs`, `{project}__project_overview`, and other group IDs are in use.
- **Quality gate infrastructure** — Per-feature and per-task-type quality gate configurations (FEAT-GE-001 adds `quality_gate_configs` entity).

### What's Missing

1. **No BDD awareness in task-work** — Phase 2 doesn't query `{project}__bdd_scenarios` for relevant scenarios.
2. **No BDD context for the coach** — The AutoBuild coach doesn't receive BDD scenarios during validation loops.
3. **No scenario verification on task-complete** — Quality gates run tests but don't map results back to specific BDD scenarios.
4. **No regression detection** — When a task breaks a previously-passing BDD scenario, there's no structured way to detect and handle this.
5. **No BDD coverage in impact analysis** — `/impact-analysis` (when implemented via FEAT-SC-001) should show which BDD scenarios a task might affect.

---

## The Feedback Loop (GuardKit's Role)

GuardKit participates in steps 2, 3, and 4 of the living documentation feedback loop:

```
RequireKit: /generate-bdd → .feature files + Graphiti episodes     ← FEAT-BDD-001-RK
GuardKit:   /task-work reads BDD context from Graphiti              ← THIS SPEC (Step 2)
GuardKit:   AutoBuild coach validates against BDD scenarios         ← THIS SPEC (Step 3)
GuardKit:   /task-complete verifies + updates Graphiti status       ← THIS SPEC (Step 4)
RequireKit: /feature-status shows verification state                ← FEAT-BDD-001-RK
```

---

## Step 2: `/task-work` Reads BDD Context

### Where in the Flow

BDD context is injected during `/task-work` Phase 2 (Implementation Planning), after the task is understood but before implementation begins. This is the same point where feature specs and project context are loaded.

### Relevance Matching Strategy

The key challenge is determining *which* BDD scenarios are relevant to a given task. Three matching strategies are used in combination, ordered by precision:

**1. Explicit Reference (highest precision)**

If the task's feature spec or acceptance criteria reference specific requirement IDs (`REQ-XXX`), query for scenarios tagged with those requirements:

```python
# Match by requirement reference
results = graphiti_client.search(
    query=f"BDD scenarios for requirements {', '.join(requirement_refs)}",
    group_ids=[f"{project}__bdd_scenarios"],
    num_results=10
)
```

**2. Feature Association (medium precision)**

If the task belongs to a feature (`FEAT-XXX`), query for all scenarios linked to that feature:

```python
# Match by feature reference
results = graphiti_client.search(
    query=f"BDD scenarios for feature {feature_id}",
    group_ids=[f"{project}__bdd_scenarios"],
    num_results=20
)
```

**3. Semantic Search (broadest, lowest precision)**

Use the task description and affected file paths to find semantically related scenarios:

```python
# Semantic match against task content
task_context = f"{task.description} {' '.join(task.affected_files)}"
results = graphiti_client.search(
    query=f"BDD scenarios related to: {task_context}",
    group_ids=[f"{project}__bdd_scenarios"],
    num_results=10
)
```

### Matching Priority

Strategies are applied in order. If explicit references yield 3+ scenarios, semantic search is skipped. This prevents over-loading context with tangentially related scenarios.

```
if explicit_matches >= 3:
    use explicit_matches only
elif explicit_matches + feature_matches >= 3:
    use explicit + feature matches
else:
    use all three strategies, deduplicate by scenario_id
```

### Context Injection Format

Relevant BDD scenarios are injected into the task-work prompt as structured context:

```markdown
## Existing BDD Scenarios (Protect These Behaviours)

The following BDD scenarios validate existing behaviour that MUST NOT be broken by this task.
If your implementation would change any of these behaviours, flag it for review.

### From Feature: User Authentication (FEAT-001)

**✅ Verified** — Successful login with valid credentials
```gherkin
Scenario: Successful login with valid credentials
  Given I am on the login page
  When I enter "user@example.com" as email
  And I enter "Pass123!" as password
  And I click the login button
  Then I should be authenticated successfully
  And the authentication should complete within 1 second
```
Last verified: 2026-02-09 (TASK-042)

**⚠️ Failing** — Account lockout after failed attempts
```gherkin
Scenario: Account lockout after failed attempts
  Given a user has 2 failed login attempts
  When they fail to login a third time
  Then their account should be locked
```
Failed since: 2026-02-09 (TASK-042) — lockout threshold mismatch

**❓ Unverified** — Multi-factor authentication flow
```gherkin
Scenario: Multi-factor authentication flow
  Given a user has MFA enabled
  When they login with valid credentials
  Then they should be prompted for a second factor
```
Generated: 2026-02-07 (never run)
```

### Token Budget

BDD context should consume no more than **2,000 tokens** within the task-work prompt. This is a subset of the overall context budget (TASK-REV-1505 recommends 15-30KB per task). If more scenarios match than fit the budget:

1. Prioritise verified scenarios (these represent known-good behaviour)
2. Then failing scenarios (these represent known problems)
3. Then unverified scenarios (these are aspirational)
4. Within each priority, prefer scenarios from the same feature
5. Truncate scenario bodies if needed (keep Given-When-Then, drop Background and data tables)

### Complexity Gating

BDD context loading is gated by task complexity:

| Complexity | BDD Context |
|-----------|-------------|
| Low (score 1-3) | Skip BDD context entirely — simple bug fixes don't need it |
| Medium (score 4-6) | Load feature-associated scenarios only (strategy 2) |
| High (score 7-10) | Full matching with all three strategies |

This aligns with the existing complexity scoring that gates other context types (system overview, architecture decisions, etc.).

---

## Step 3: AutoBuild Coach BDD Validation

### Coach Prompt Integration

During player-coach loops, the coach receives BDD scenarios as part of its validation context. The coach uses these to check whether the player's implementation preserves existing behaviour.

**Additional coach instructions** (appended to existing coach prompt):

```markdown
## BDD Scenario Validation

You have been provided with BDD scenarios that validate existing behaviour.
During your review of the player's implementation:

1. **Check for regressions**: Does the implementation change any behaviour described
   by a ✅ verified scenario? If so, flag this as a potential regression.

2. **Check for alignment**: Does the implementation align with the intent of related
   BDD scenarios? Even unverified scenarios represent expected behaviour.

3. **Note coverage gaps**: If the implementation adds new behaviour not covered by
   any existing scenario, note this in your review. The product owner may want to
   add new scenarios.

4. **Do NOT fail solely on BDD**: BDD scenarios are guidance, not hard gates.
   The acceptance criteria for the current task take precedence. But regressions
   should be flagged prominently.
```

### Coach Context Injection

The same BDD context injected into task-work (Step 2) is also provided to the coach. This avoids re-querying Graphiti during the player-coach loop — the context is passed through from the task-work phase.

### Regression Flagging

When the coach identifies a potential BDD regression, it should include a structured flag in its review output:

```markdown
⚠️ BDD REGRESSION DETECTED
Scenario: "Successful login with valid credentials" (BDD-user-auth-a3f7c2)
Issue: Player's implementation changes the authentication endpoint response format.
The scenario expects redirect to dashboard, but the new implementation returns a
JSON response. This will break the existing login flow.
Recommendation: Update the BDD scenario or modify the implementation to preserve
the existing redirect behaviour.
```

This flag is informational — it does not automatically block task completion. The developer makes the final decision about whether the regression is intentional (scenario needs updating) or unintentional (implementation needs fixing).

---

## Step 4: `/task-complete` Updates BDD Status

### Verification Criteria

During `/task-complete`, after quality gates pass (lint, tests, type check), the system determines which BDD scenarios were exercised:

**Automated verification** (preferred): If test output can be mapped to specific BDD scenarios (e.g., through pytest-bdd markers, behave output, or test file naming conventions), the system marks individual scenarios as verified or failed based on actual test results.

```python
# Parse test output for BDD scenario results
# Mapping: test name → scenario_id via @requirement or @feature tags
for scenario_id, test_result in bdd_test_results.items():
    if test_result.passed:
        update_scenario_status(scenario_id, "verified", task_id)
    else:
        update_scenario_status(scenario_id, "failed", task_id)
```

**Declaration-based verification** (fallback): When test output can't be mapped to individual scenarios (common in projects where BDD scenarios haven't been wired to step definitions yet), the coach's assessment during player-coach review serves as the verification. If the coach didn't flag any BDD regressions, feature-associated scenarios retain their current status. If the coach flagged regressions, affected scenarios are marked "failed".

**Manual scenarios**: Some scenarios describe behaviour that can't be automated (e.g., "the user experience should feel responsive"). These remain in "generated" status until explicitly marked by a developer. Task-complete does not touch them.

### Graphiti Status Update

When task-complete updates BDD scenario status, it writes targeted metadata updates to existing Graphiti episodes:

```python
def update_scenario_status(scenario_id, status, task_id, timestamp=None):
    """Update BDD scenario verification status in Graphiti."""
    timestamp = timestamp or datetime.utcnow().isoformat()
    
    # Search for the scenario episode
    episode = graphiti_client.search(
        query=f"BDD scenario {scenario_id}",
        group_ids=[f"{project}__bdd_scenarios"],
        num_results=1
    )
    
    if episode:
        # Update metadata fields
        episode.metadata["status"] = status           # verified | failed
        episode.metadata["last_verified"] = timestamp
        episode.metadata["last_verified_by"] = f"task-complete:{task_id}"
        
        # Upsert with updated metadata
        graphiti_client.add_episode(
            name=episode.name,
            body=episode.content,
            group_id=f"{project}__bdd_scenarios",
            metadata=episode.metadata,
            source_description=f"Status update from {task_id}"
        )
```

### Regression Handling

When task-complete finds previously-verified scenarios now failing:

**Default behaviour**: Warn and continue. The developer sees:

```
⚠️ BDD Regression Warning
2 previously-verified scenarios are now failing:
  - "Successful login with valid credentials" (was ✅, now ⚠️)
  - "Session timeout handling" (was ✅, now ⚠️)

These scenarios have been marked as FAILED in Graphiti.
Consider reviewing these regressions before merging.

Task completion: PROCEEDING (regressions are warnings, not blockers)
```

**Strict mode** (configurable per project): Block task completion when verified scenarios regress:

```yaml
# .guardkit/config.yaml
bdd:
  regression_policy: warn      # warn (default) | block | ignore
  stale_threshold_days: 7      # Scenarios older than this are marked stale
```

When `regression_policy: block`, task-complete returns a failure and the developer must either fix the regression or explicitly override with `--force`.

### What Happens Without BDD Scenarios

If no BDD scenarios exist in Graphiti for the current project (either because RequireKit hasn't pushed them or Graphiti isn't configured), task-complete behaves exactly as it does today — quality gates run, but no BDD status updates occur. No error, no warning — BDD integration is purely additive.

---

## Integration with `/impact-analysis`

When FEAT-SC-001 implements `/impact-analysis`, BDD scenarios should be included in the impact assessment. This is a future integration point, documented here for when FEAT-SC-001 is built.

### Proposed Impact Analysis BDD Section

```
/impact-analysis TASK-055

Impact Assessment for TASK-055: Refactor Authentication Service

Components Affected:
  - auth-service (primary)
  - session-manager (secondary)
  
BDD Scenarios at Risk:
  ✅ 4 verified scenarios in FEAT-001 (User Authentication)
  ✅ 2 verified scenarios in FEAT-005 (Session Management)
  ⚠️ 1 already-failing scenario in FEAT-001

Recommendation: Run full authentication test suite after implementation.
BDD scenarios to watch: BDD-user-auth-a3f7c2, BDD-user-auth-c1d4e5, 
  BDD-session-mgmt-f8a2b3
```

This is **out of scope** for FEAT-BDD-001-GK but recorded here so FEAT-SC-001 can reference it.

---

## Configuration

### New Configuration Section

```yaml
# .guardkit/config.yaml (new section)
bdd:
  enabled: true                    # Master switch for BDD integration
  regression_policy: warn          # warn | block | ignore
  stale_threshold_days: 7          # Days before a scenario is considered stale
  context_token_budget: 2000       # Max tokens for BDD context in task-work
  complexity_gate: 4               # Minimum complexity score to load BDD context
  verification_mode: auto          # auto | declaration | manual
    # auto: Map test results to scenarios when possible, fall back to declaration
    # declaration: Use coach assessment only
    # manual: Never auto-update, require explicit verification
```

### Defaults

All defaults are designed to be non-intrusive — BDD integration adds value without adding friction:

- `regression_policy: warn` — Regressions are visible but don't block
- `complexity_gate: 4` — Simple tasks skip BDD context
- `verification_mode: auto` — Best-effort automated verification with graceful fallback

---

## Acceptance Criteria

### task-work BDD Context (Step 2)
- [ ] `/task-work` queries `{project}__bdd_scenarios` for relevant scenarios during Phase 2
- [ ] Three matching strategies applied in priority order (explicit → feature → semantic)
- [ ] BDD context injected into task-work prompt with status icons and Gherkin text
- [ ] Token budget respected (max 2,000 tokens for BDD context)
- [ ] Complexity gating: low-complexity tasks skip BDD context loading
- [ ] Graceful degradation: no error if Graphiti unavailable or no BDD scenarios exist

### AutoBuild Coach Integration (Step 3)
- [ ] Coach receives BDD scenarios as part of validation context
- [ ] Coach instructions include regression checking and coverage gap identification
- [ ] Coach flags potential BDD regressions with structured output format
- [ ] BDD regressions are informational, not automatic blockers

### task-complete Verification (Step 4)
- [ ] `/task-complete` maps test results to BDD scenarios when possible (auto mode)
- [ ] Falls back to coach declaration when test mapping unavailable
- [ ] Updates `status`, `last_verified`, `last_verified_by` in Graphiti for exercised scenarios
- [ ] Regression warning shown when previously-verified scenarios now fail
- [ ] `regression_policy: block` prevents completion when verified scenarios regress
- [ ] `--force` flag overrides block when developer accepts the regression
- [ ] No errors when BDD integration is unconfigured or Graphiti unavailable

### Configuration
- [ ] `bdd` section in `.guardkit/config.yaml` controls all BDD behaviour
- [ ] All settings have sensible defaults (non-intrusive by default)
- [ ] Configuration documented in GuardKit docs

---

## Testing Approach

### Unit Tests
- Relevance matching: explicit refs → feature association → semantic search priority logic
- Token budget enforcement: truncation when BDD context exceeds budget
- Complexity gating: scenarios loaded/skipped based on complexity score
- Status update construction: correct metadata fields for Graphiti upsert
- Regression detection: identify when verified → failed transition occurs
- Configuration parsing: all `bdd` config options with defaults

### Integration Tests
- Full flow: RequireKit pushes BDD episodes → `/task-work` loads them → verify context includes scenarios
- Coach integration: BDD context passed to coach during player-coach loop → verify coach prompt includes scenarios
- Status update: `/task-complete` runs tests → BDD episode status updated in Graphiti → verify status change
- Regression warning: push verified scenario → task-complete with failing test → verify regression warning and status update
- Block mode: `regression_policy: block` → verified regression → verify task-complete fails → verify `--force` overrides
- No BDD: empty `{project}__bdd_scenarios` → verify all commands work without errors
- No Graphiti: Graphiti unavailable → verify graceful degradation at all integration points

### Manual Verification
- [ ] Run `/task-work` on a task with associated BDD scenarios → verify scenarios appear in prompt
- [ ] Complete a task that passes all BDD-related tests → verify scenarios marked "verified" in Graphiti
- [ ] Complete a task that breaks a BDD scenario → verify regression warning
- [ ] Run `/feature-status` (RequireKit side) → verify it reflects updates from GuardKit

---

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `guardkit/bdd/__init__.py` | BDD integration module |
| `guardkit/bdd/context_loader.py` | Loads relevant BDD scenarios from Graphiti for task-work |
| `guardkit/bdd/relevance_matcher.py` | Implements three-strategy relevance matching |
| `guardkit/bdd/status_updater.py` | Updates BDD scenario status in Graphiti during task-complete |
| `guardkit/bdd/regression_detector.py` | Detects verified → failed transitions and generates warnings |
| `guardkit/bdd/test_mapper.py` | Maps test output (pytest, behave) to BDD scenario IDs |
| `guardkit/bdd/config.py` | BDD configuration parsing and defaults |
| `tests/unit/test_relevance_matcher.py` | Unit tests for relevance matching |
| `tests/unit/test_status_updater.py` | Unit tests for status updates |
| `tests/unit/test_regression_detector.py` | Unit tests for regression detection |
| `tests/unit/test_bdd_config.py` | Unit tests for BDD configuration |
| `tests/integration/test_bdd_feedback_loop.py` | Integration tests for the full BDD loop |
| `docs/guides/bdd-living-documentation.md` | User guide for BDD integration |

### Modified Files

| File | Changes |
|------|---------|
| `.claude/commands/task-work.md` | Add BDD context loading in Phase 2. Add BDD section to prompt template. |
| `.claude/commands/task-complete.md` | Add BDD verification step after quality gates. Add regression warning/blocking. |
| `.claude/agents/coach.md` (or equivalent) | Add BDD validation instructions to coach prompt. |
| `.claude/agents/coach-ext.md` | Add BDD regression flagging format and guidance. |
| `guardkit/orchestrator/autobuild.py` | Pass BDD context through to coach during player-coach loops. |
| `guardkit/knowledge/context_retrieval.py` | Add `{project}__bdd_scenarios` to job-specific retrieval queries. |
| `guardkit/cli/task_complete.py` | Add BDD status update step in completion flow. |
| `.guardkit/config.yaml` (template) | Add `bdd` configuration section with defaults. |
| `docs/reference/task-work.md` | Document BDD context injection behaviour. |
| `docs/reference/task-complete.md` | Document BDD verification and regression handling. |
| `docs/reference/configuration.md` | Document `bdd` configuration options. |

---

## Design Decisions

### Decision 1: BDD as Guidance, Not Hard Gate (Default)
**Chosen over**: Making BDD regression a mandatory blocker
**Rationale**: Walk before running. Many projects won't have complete BDD coverage. Blocking on incomplete scenarios adds friction without value. Strict mode is available for mature projects that want it. Default is warn-only.

### Decision 2: Three-Strategy Relevance Matching
**Chosen over**: Single semantic search, or requiring explicit scenario-task linking
**Rationale**: Explicit references are most precise but not always available. Feature association provides good coverage for most tasks. Semantic search catches cross-cutting scenarios (e.g., auth scenarios relevant to a payment task). The cascade prevents over-loading context with loosely related scenarios.

### Decision 3: Coach-Based Declaration as Verification Fallback
**Chosen over**: Requiring all BDD scenarios to have automated step definitions
**Rationale**: Most real projects have BDD scenarios written before step definitions exist. Requiring automation would make the feature useless until the last mile. Coach-based declaration provides value immediately — the coach reviews whether the implementation aligns with scenario intent even without running the scenarios.

### Decision 4: Token-Budgeted BDD Context
**Chosen over**: Loading all matching BDD scenarios regardless of count
**Rationale**: TASK-REV-1505 identified context budget as a moderate concern. BDD context competes with feature specs, architecture context, and project overview for limited context window. A fixed 2,000-token budget ensures BDD doesn't crowd out other essential context.

### Decision 5: No GuardKit `/feature-status` (Initially)
**Chosen over**: Providing `/feature-status` in both repos
**Rationale**: Avoid command duplication. Product owners use RequireKit; developers use GuardKit. Developers can check BDD status via test output directly or query Graphiti. If demand arises, adding a GuardKit `/feature-status` is trivial since the data is in Graphiti.

---

## References

- `guardkit-requirekit-evolution-strategy.md` — Sections 4.3 (BDD Living Documentation → Graphiti), 7 (Phase 3), 9 (Architecture diagram)
- `guardkit-evolution-spec-kickoff.md` — Spec 5 definition, key questions (BDD episode granularity, verification lifecycle, relevance matching, regression detection)
- `FEAT-BDD-001-RK` — RequireKit side of BDD living documentation (paired spec)
- `FEAT-GE-001-critical-graphiti-entity-additions.md` — Quality gate configs, turn states
- `FEAT-SC-001-system-context-read-commands.md` — Future `/impact-analysis` integration point
- `TASK-REV-1505-review-report.md` — Context budget recommendations, GR-006 job-specific retrieval
- `AutoBuild_Product_Specification.md` — Player-coach loop, coach prompt patterns
