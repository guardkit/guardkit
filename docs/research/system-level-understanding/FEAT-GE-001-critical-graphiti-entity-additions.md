# Feature: Critical Graphiti Entity Additions

> **Feature ID**: FEAT-GE-001
> **Priority**: P0 (Addresses top-5 AutoBuild problems directly)
> **Estimated Effort**: 2-3 days
> **Dependencies**: Graphiti prerequisites (PRE-000 through PRE-003) — already implemented
> **Blocks**: FEAT-SP-001 (`/system-plan`), FEAT-SC-001 (system context read commands)

---

## Summary

Specify the four entity types identified by TASK-REV-1505 as critical gaps in the Graphiti knowledge graph: `role_constraints`, `quality_gate_configs`, `turn_states`, and `implementation_modes`. Three of these (role_constraints, quality_gate_configs, turn_states) already have schemas and seeding implemented. This spec completes the picture by: (1) documenting what exists as the canonical reference, (2) filling the `implementation_modes` gap, (3) defining the runtime enforcement patterns that make these entities actually useful during player-coach sessions, (4) specifying the per-project override mechanism, and (5) defining the turn state lifecycle including retention policy.

Without runtime enforcement, having these entities in Graphiti is inert — the coach must query and act on role constraints, quality gate configs must be loaded before threshold checks, and turn states must be written and read at precise points in the feature-build loop. This spec bridges the gap between "data exists" and "data changes behaviour."

---

## Current State

### What Exists

| Entity | Schema | Seeding | Enforcement | Status |
|--------|--------|---------|-------------|--------|
| `role_constraints` | ✅ `RoleConstraintsEpisode` in seeding module | ✅ Default player/coach constraints seeded | ❌ Coach prompt doesn't query or enforce | Partial |
| `quality_gate_configs` | ✅ `QualityGateConfigEpisode` with task-type profiles | ✅ 6 profiles seeded (scaffolding, feature×3, testing, documentation) | ❌ Quality gates use hardcoded thresholds, not Graphiti | Partial |
| `turn_states` | ✅ `TurnStateEntity` dataclass defined | ✅ Group ID registered | ❌ Feature-build doesn't write or read turn states | Partial |
| `implementation_modes` | ✅ `ImplementationModeEpisode` schema defined | ✅ Default direct/task-work modes defined | ❌ No seeding, no enforcement, no query path | Gap |

### The Core Problem

The entities exist as data definitions but aren't wired into the runtime execution path. During a player-coach session today:

- The coach doesn't know its role boundaries → role reversal (writes code, makes implementation decisions)
- Quality gate thresholds are hardcoded in `gates.py` → threshold drift when someone adjusts code but not config
- Turn N+1 starts from zero → repeated mistakes, circular debugging
- No guidance on when to use direct mode vs task-work → file location confusion

---

## Entity Schemas (Canonical Reference)

### role_constraints

**Group ID**: `role_constraints` (system-scoped, not project-prefixed)

**Scope Decision**: Global defaults with per-project overrides. Player/coach roles don't change per project, but specific constraints might — e.g., a compliance-heavy project might add "must verify regulatory alignment" to the coach's `must_do` list.

```python
@dataclass
class RoleConstraintsEpisode:
    entity_type: str = "role_constraints"
    role: str = ""  # "player" | "coach"
    must_do: List[str] = field(default_factory=list)
    must_not_do: List[str] = field(default_factory=list)
    ask_before: List[str] = field(default_factory=list)
    escalate_when: List[str] = field(default_factory=list)
```

**Default Player Constraints** (seeded):
- Must do: Implement code, follow implementation plans, write tests, report blockers with evidence
- Must not do: Validate quality gates, make architectural decisions without ADR, modify quality profiles, ask for human guidance mid-feature
- Ask before: Changing architecture from plan, modifying external deps, skipping acceptance criteria

**Default Coach Constraints** (seeded):
- Must do: Validate against acceptance criteria, run quality gates, provide actionable feedback, track AC status
- Must not do: Write implementation code, modify implementation directly, make implementation decisions, change AC mid-task
- Escalate when: Test failures persist after 3 attempts, architecture violations detected, AC cannot be met as written

### quality_gate_configs

**Group ID**: `quality_gate_configs` (system-scoped)

**Storage Decision**: Config files are authoritative (human-editable at `.guardkit/config/quality-gates.yaml`), Graphiti is populated from them during seeding. This gives transparency — developers can see and edit thresholds in a familiar format — while providing queryability for the coach at runtime.

```python
@dataclass
class QualityGateConfigEpisode:
    entity_type: str = "quality_gate_config"
    task_type: str = ""  # "scaffolding" | "feature" | "testing" | "documentation" | "bugfix"
    complexity_range: Tuple[int, int] = (1, 10)
    arch_review_required: bool = True
    arch_review_threshold: int = 60
    coverage_required: bool = True
    coverage_threshold: float = 0.80
    tests_required: bool = True
    tests_must_pass: bool = True
    effective_from: str = ""
```

**Default Profiles** (6 seeded):

| Task Type | Complexity | Arch Review | Coverage | Tests |
|-----------|-----------|-------------|----------|-------|
| scaffolding | 1-10 | No | No | No |
| feature | 1-3 | Yes (50) | 70% | Yes |
| feature | 4-6 | Yes (60) | 80% | Yes |
| feature | 7-10 | Yes (70) | 85% | Yes |
| testing | 1-10 | No | 90% | Yes |
| documentation | 1-10 | No | No | No |

### turn_states

**Group ID**: `turn_states` (project-scoped: `{project}__turn_states`)

**Lifecycle Decision**: Turn states are project-scoped because they track feature-build progress within a specific project. They're retained as historical record after feature completion (valuable for retrospectives and pattern learning) with a configurable retention limit.

```python
@dataclass
class TurnStateEpisode:
    entity_type: str = "turn_state"
    feature_id: str = ""          # FEAT-XXX being built
    task_id: str = ""             # TASK-XXX currently executing
    turn_number: int = 0
    player_decision: str = ""     # What the player chose to do
    coach_decision: str = ""      # Coach verdict: "approve" | "revise" | "escalate"
    blockers_found: List[str] = field(default_factory=list)
    progress_summary: str = ""
    acceptance_criteria_status: Dict[str, str] = field(default_factory=dict)
    # ^ {criterion_id: "verified" | "pending" | "rejected" | "blocked"}
    mode: str = "FRESH_START"     # "FRESH_START" | "RECOVERING_STATE" | "CONTINUING_WORK"
    quality_gate_results: Optional[Dict] = None  # Last gate run results
    timestamp: str = ""
```

### implementation_modes (NEW — requires implementation)

**Group ID**: `implementation_modes` (system-scoped)

**Enforcement Decision**: Advisory only. The system recommends the appropriate mode based on task characteristics and displays it to the user, but does not gate behaviour. Rationale: forcing mode selection adds ceremony that violates the "least ceremony" principle. The developer knows their task best — the system provides guidance, not gates.

```python
@dataclass
class ImplementationModeEpisode:
    entity_type: str = "implementation_mode"
    mode: str = ""                    # "direct" | "task_work" | "autobuild"
    invocation_method: str = ""       # "inline" | "sdk_query" | "orchestrated"
    result_location_pattern: str = "" # Where output files end up
    state_recovery_strategy: str = "" # "git_check_first" | "resume_from_checkpoint"
    when_to_use: List[str] = field(default_factory=list)
    pitfalls: List[str] = field(default_factory=list)
    complexity_range: Tuple[int, int] = (1, 10)  # Recommended complexity range
    ceremony_level: str = ""          # "minimal" | "standard" | "full"
```

**Default Modes to Seed** (3):

| Mode | Complexity | Ceremony | When |
|------|-----------|----------|------|
| direct | 1-3 | minimal | Simple file ops, config changes, doc updates |
| task_work | 3-7 | standard | Feature work needing quality gates, multi-file changes |
| autobuild | 5-10 | full | Multi-task features needing player-coach adversarial cooperation |

**Critical Pitfalls** (seeded per mode):
- direct: Don't use for complex implementations; check git status first
- task_work: MUST use SDK `query()`, NOT subprocess (ADR-FB-001); paths use FEAT-XXX worktree ID, not TASK-XXX (ADR-FB-002); implementation plan MUST exist before execution (ADR-FB-003)
- autobuild: Requires feature-plan output; don't mix with manual edits during execution

---

## Per-Project Override Mechanism

### Config File Structure

```yaml
# .guardkit/config/entity-overrides.yaml (optional, per-project)

role_constraints:
  coach:
    must_do_additions:
      - "Verify OPG registration compliance"
      - "Check Moneyhub API contract alignment"
    escalate_when_additions:
      - "Financial data handling inconsistency detected"

quality_gate_configs:
  feature:
    overrides:
      - complexity_range: [4, 6]
        coverage_threshold: 0.85  # Higher than default 0.80 for this project
```

### Override Resolution

```python
async def resolve_role_constraints(
    client: "GraphitiClient",
    role: str,
    project_id: str
) -> RoleConstraintsEpisode:
    """
    Resolve role constraints with per-project overrides.
    
    Priority: project overrides > global defaults > hardcoded fallback.
    """
    # 1. Load global defaults from Graphiti
    defaults = await _load_role_defaults(client, role)
    
    # 2. Load project overrides from config file
    overrides = _load_project_overrides(project_id, "role_constraints", role)
    
    # 3. Merge: additions extend lists, replacements override values
    if overrides:
        if "must_do_additions" in overrides:
            defaults.must_do.extend(overrides["must_do_additions"])
        if "escalate_when_additions" in overrides:
            defaults.escalate_when.extend(overrides["escalate_when_additions"])
    
    return defaults
```

### Hardcoded Fallbacks

When Graphiti is unavailable (graceful degradation), use hardcoded defaults identical to the seeded values. This ensures GuardKit works without Graphiti while providing queryable, overridable values when it's available.

```python
FALLBACK_ROLE_CONSTRAINTS = {
    "player": RoleConstraintsEpisode(role="player", must_do=[...], ...),
    "coach": RoleConstraintsEpisode(role="coach", must_do=[...], ...),
}

FALLBACK_QUALITY_GATES = {
    ("feature", 4, 6): QualityGateConfigEpisode(task_type="feature", ...),
    # ... other profiles
}
```

---

## Feature-Build Runtime Integration

This is the critical missing layer — how the entities change behaviour during player-coach sessions.

### Coach Receives Role Constraints

**Integration point**: Coach prompt construction in `feature_build.py` / `coach.py`.

At the start of each coach validation turn, the coach prompt includes role constraints loaded from Graphiti:

```python
async def build_coach_prompt(task, turn_number, client, project_id):
    """Construct coach prompt with role constraints and quality gate config."""
    
    # Load role constraints (with override resolution)
    constraints = await resolve_role_constraints(client, "coach", project_id)
    
    # Load quality gate config for this task type and complexity
    gate_config = await resolve_quality_gate_config(
        client, task.task_type, task.complexity, project_id
    )
    
    # Load previous turn state (if continuing)
    prev_turn = await load_latest_turn_state(
        client, task.feature_id, project_id
    ) if turn_number > 1 else None
    
    prompt_sections = [
        format_role_constraints(constraints),
        format_quality_gates(gate_config),
    ]
    
    if prev_turn:
        prompt_sections.append(format_previous_turn(prev_turn))
    
    return "\n\n".join(prompt_sections)
```

**Injected format** (in coach prompt):

```
## Your Role: Coach
You MUST: Validate against acceptance criteria | Run quality gates | ...
You MUST NOT: Write implementation code | Modify implementation | ...
ESCALATE when: Test failures persist after 3 attempts | ...

## Quality Gates for This Task
Task type: feature | Complexity: 5
Architecture review: required (threshold: 60)
Coverage: required (threshold: 80%)
Tests: required, must pass
DO NOT adjust these thresholds during this session.

## Previous Turn Context (Turn 2 of 3)
Player implemented authentication middleware.
AC status: {login: verified, logout: pending, session-timeout: pending}
Blockers: None
Coach decision: REVISE — missing session timeout handling
```

### Coach Enforces Quality Gates from Config

**Integration point**: `quality/gates.py` → replace hardcoded thresholds with Graphiti lookup.

```python
async def get_gate_thresholds(
    task_type: str,
    complexity: int,
    client: Optional["GraphitiClient"] = None,
    project_id: Optional[str] = None,
) -> QualityGateConfigEpisode:
    """
    Load quality gate thresholds from Graphiti, falling back to hardcoded defaults.
    
    Matches by task_type and complexity within complexity_range.
    """
    if client and client.enabled:
        configs = await _search_quality_configs(client, task_type)
        for config in configs:
            low, high = config.complexity_range
            if low <= complexity <= high:
                return config
    
    # Fallback to hardcoded defaults
    return _get_fallback_config(task_type, complexity)
```

### Player-Coach Turn State Tracking

**Write lifecycle**: End of each player-coach turn, after coach renders verdict.

```python
async def record_turn_state(
    client: "GraphitiClient",
    project_id: str,
    feature_id: str,
    task_id: str,
    turn_number: int,
    player_decision: str,
    coach_decision: str,
    blockers: List[str],
    progress: str,
    ac_status: Dict[str, str],
    mode: str,
    gate_results: Optional[Dict] = None,
):
    """Record turn state at end of player-coach turn."""
    state = TurnStateEpisode(
        feature_id=feature_id,
        task_id=task_id,
        turn_number=turn_number,
        player_decision=player_decision,
        coach_decision=coach_decision,
        blockers_found=blockers,
        progress_summary=progress,
        acceptance_criteria_status=ac_status,
        mode=mode,
        quality_gate_results=gate_results,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    
    entity_id = f"TURN-{feature_id}-{task_id}-T{turn_number}"
    
    await client.upsert_episode(
        name=f"Turn {turn_number}: {task_id}",
        episode_body=json.dumps(asdict(state)),
        group_id=client.get_group_id("turn_states", scope="project"),
        entity_id=entity_id,
        source="feature_build",
        entity_type="turn_state",
    )
```

**Read lifecycle**: Start of each turn (after turn 1), and during state recovery.

```python
async def load_latest_turn_state(
    client: "GraphitiClient",
    feature_id: str,
    project_id: str,
) -> Optional[TurnStateEpisode]:
    """Load the most recent turn state for a feature-build session."""
    if not client or not client.enabled:
        return None
    
    results = await client.search(
        query=f"turn state {feature_id} latest",
        group_ids=[client.get_group_id("turn_states", scope="project")],
        num_results=1,
    )
    
    if not results:
        return None
    
    # Parse from search result fact string (heuristic extraction)
    return _parse_turn_state_from_result(results[0])
```

**Retention policy**: Retain all turn states for completed features. Apply a configurable maximum (default: 50 turns per feature, 200 turns total per project). On exceeding the limit, oldest turns from completed features are pruned first. In-progress features are never pruned.

### Implementation Mode Advisory

**Integration point**: Task creation and task-work startup.

When a task is created or `task-work` begins, display the recommended mode:

```python
async def suggest_implementation_mode(
    client: "GraphitiClient",
    task_type: str,
    complexity: int,
) -> Optional[str]:
    """Suggest implementation mode based on task characteristics. Advisory only."""
    if not client or not client.enabled:
        return _fallback_mode_suggestion(task_type, complexity)
    
    modes = await _search_implementation_modes(client)
    for mode in modes:
        low, high = mode.complexity_range
        if low <= complexity <= high:
            return f"💡 Suggested mode: {mode.mode} ({mode.ceremony_level} ceremony)\n" \
                   f"   {', '.join(mode.when_to_use[:2])}\n" \
                   f"   ⚠️  {mode.pitfalls[0] if mode.pitfalls else ''}"
    
    return None
```

---

## Seeding Integration

### Changes to Existing Seeding

`implementation_modes` must be added to the seeding module alongside the already-seeded entities:

```python
# In guardkit/knowledge/seeding/ (new module or extend existing)

async def seed_implementation_modes(client: "GraphitiClient"):
    """Seed default implementation mode guidance."""
    for mode in DEFAULT_IMPLEMENTATION_MODES:
        await client.upsert_episode(
            name=f"Implementation Mode: {mode.mode}",
            episode_body=json.dumps(asdict(mode)),
            group_id="implementation_modes",
            entity_id=f"MODE-{mode.mode}",
            source="system_seeding",
            entity_type="implementation_mode",
        )
```

### Seeding Commands

Add `implementation_modes` to the existing `guardkit graphiti seed` command's entity list. No new CLI commands needed — the existing seeding infrastructure handles this.

### Re-seeding Safety

All entities use `upsert_episode()` with stable entity IDs. Re-running `guardkit graphiti seed` is idempotent — it updates existing episodes rather than creating duplicates. Entity IDs:

| Entity | ID Format | Example |
|--------|-----------|---------|
| Role constraints | `ROLE-{role}` | `ROLE-player`, `ROLE-coach` |
| Quality gate config | `QG-{task_type}-{complexity_range}` | `QG-feature-4-6` |
| Turn state | `TURN-{feature}-{task}-T{n}` | `TURN-FEAT-001-TASK-003-T2` |
| Implementation mode | `MODE-{mode}` | `MODE-direct`, `MODE-task_work` |

---

## Backward Compatibility

**Principle**: Projects that haven't re-seeded after these entities are added must continue working identically to today.

1. **Missing role_constraints** → Use `FALLBACK_ROLE_CONSTRAINTS` (identical to seeded defaults). Coach prompt omits role section rather than failing.
2. **Missing quality_gate_configs** → Use hardcoded thresholds in `gates.py` (current behaviour preserved).
3. **Missing turn_states** → Turn N+1 starts fresh (current behaviour). No crash, no warning — just no cross-turn context.
4. **Missing implementation_modes** → No mode suggestion displayed. Task proceeds normally.

All new code paths check `if client and client.enabled` before Graphiti operations and fall back gracefully.

---

## Acceptance Criteria

- [ ] `implementation_modes` entity seeded with 3 default modes (direct, task_work, autobuild)
- [ ] Re-seeding is idempotent — `guardkit graphiti seed` doesn't create duplicate entities
- [ ] Coach prompt includes role constraints loaded from Graphiti (with fallback)
- [ ] Coach prompt includes quality gate config for the task's type and complexity (with fallback)
- [ ] Coach prompt includes previous turn state when continuing a multi-turn session
- [ ] Quality gate threshold checks in `gates.py` read from Graphiti configs (with hardcoded fallback)
- [ ] Turn state written at end of each player-coach turn with correct entity_id
- [ ] Turn state read at start of subsequent turns
- [ ] Per-project override file (`.guardkit/config/entity-overrides.yaml`) extends defaults when present
- [ ] Mode suggestion displayed during task-work startup (advisory, non-blocking)
- [ ] All new code paths degrade gracefully when Graphiti is unavailable
- [ ] Projects without these entities continue working identically to current behaviour
- [ ] Turn state retention: max 50 per feature, 200 per project, oldest-completed pruned first

---

## Testing Approach

### Unit Tests

```python
# Role constraint resolution
def test_resolve_role_defaults_without_overrides():
    """Global defaults returned when no project overrides exist."""

def test_resolve_role_with_project_additions():
    """Project additions extend (not replace) global must_do list."""

def test_resolve_role_fallback_when_graphiti_unavailable():
    """Hardcoded fallback used when Graphiti disabled."""

# Quality gate config resolution
def test_gate_config_matches_complexity_range():
    """Correct profile returned for task_type='feature', complexity=5."""

def test_gate_config_fallback_preserves_current_behaviour():
    """Hardcoded fallback matches current gates.py thresholds exactly."""

# Turn state lifecycle
def test_turn_state_entity_id_deterministic():
    """Same feature/task/turn always produces same entity_id."""

def test_turn_state_not_written_when_graphiti_unavailable():
    """Graceful skip when Graphiti disabled — no error, no crash."""

def test_previous_turn_loaded_for_turn_2():
    """Turn 2 receives turn 1's state in coach prompt."""

def test_no_previous_turn_for_turn_1():
    """Turn 1 starts fresh — no turn state in prompt."""

# Implementation mode advisory
def test_mode_suggestion_for_simple_task():
    """Complexity 2 suggests 'direct' mode."""

def test_mode_suggestion_for_complex_feature():
    """Complexity 7 suggests 'autobuild' mode."""

def test_mode_suggestion_absent_when_graphiti_unavailable():
    """No suggestion displayed when Graphiti disabled — no error."""

# Backward compatibility
def test_coach_prompt_works_without_role_constraints():
    """Coach prompt generates successfully with empty constraints."""

def test_quality_gates_work_without_graphiti_config():
    """Current hardcoded thresholds used when Graphiti has no configs."""
```

### Integration Tests

```python
async def test_full_turn_lifecycle():
    """Write turn state → read in next turn → verify in coach prompt."""

async def test_seed_and_query_implementation_modes():
    """Seed modes → query by task characteristics → verify correct mode returned."""

async def test_reseed_idempotency():
    """Seed twice → verify no duplicate episodes created."""

async def test_project_override_integration():
    """Create override file → resolve constraints → verify additions merged."""
```

---

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `guardkit/knowledge/entity_resolution.py` | Resolve entities with per-project overrides and fallbacks |
| `guardkit/knowledge/seeding/implementation_modes.py` | Seed default implementation mode episodes |
| `guardkit/knowledge/turn_state_manager.py` | Turn state write/read/prune lifecycle |
| `.guardkit/config/entity-overrides.yaml.example` | Example override file with documentation |
| `tests/unit/test_entity_resolution.py` | Unit tests for resolution logic |
| `tests/unit/test_turn_state_manager.py` | Unit tests for turn state lifecycle |
| `tests/integration/test_entity_integration.py` | Integration tests for full lifecycle |

### Modified Files

| File | Change |
|------|--------|
| `guardkit/autobuild/coach.py` (or equivalent) | Add role constraints and quality gate config to coach prompt |
| `guardkit/autobuild/feature_build.py` | Add turn state write after each turn, read at turn start |
| `guardkit/quality/gates.py` | Replace hardcoded thresholds with Graphiti lookup + fallback |
| `guardkit/knowledge/seeding/seeding.py` | Add `seed_implementation_modes()` to seeding orchestrator |
| `guardkit/tasks/work.py` | Add mode suggestion display at task-work startup |
| `guardkit/cli/graphiti.py` | Register `implementation_modes` group in seed command |

---

## Design Decision Summary

| # | Question (from Kickoff) | Decision | Rationale |
|---|------------------------|----------|-----------|
| 1 | Role constraints scope | Global defaults + per-project overrides via config file | Player/coach roles are universal; project-specific compliance needs can extend them |
| 2 | Quality gate config storage | Config files authoritative, Graphiti populated from them | Transparency (human-editable YAML) + queryability (Graphiti for coach) |
| 3 | Turn state lifecycle | Written end-of-turn, read start-of-next, retained with limits | Enables cross-turn learning and retrospectives; limits prevent unbounded growth |
| 4 | Implementation modes enforcement | Advisory only (display suggestion, don't gate) | Least ceremony principle; developer knows their task best |
| 5 | Relationship to GR features | Integration point is FEAT-GR-001 seeding; enforcement is new work | Schemas exist, seeding mostly exists; enforcement is the deliverable |
| 6 | Backward compatibility | Graceful degradation with hardcoded fallbacks | Projects without Graphiti or without re-seeding must work identically to today |

---

## References

- `guardkit-requirekit-evolution-strategy.md` — Section 5: Critical Graphiti Entity Gaps
- `TASK-REV-1505-review-report.md` — Parts 3-6: AutoBuild lessons alignment, findings, recommendations
- `FEAT-GR-000-gap-analysis.md` — Gaps 8-11: role constraints, quality gate configs, implementation modes, turn states
- `FEAT-GR-001-project-knowledge-seeding.md` — Existing entity schemas and default values
- `FEAT-GR-PRE-002-episode-metadata-schema.md` — Episode metadata conventions
- `FEAT-SP-001-system-plan-command.md` — Entity conventions (to_episode_body, entity_id, upsert patterns)
- `guardkit-evolution-spec-kickoff.md` — Spec 3 requirements and key questions
- `docs/reviews/graphiti_baseline/graphiti-technical-reference.md` — Graphiti API surface
- `docs/reviews/graphiti_baseline/graphiti-storage-theory.md` — Episode structure, content fidelity
