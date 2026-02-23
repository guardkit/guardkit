# Review Report: TASK-REV-5FA4

## Executive Summary

The Graphiti seed function has **significant gaps** that need addressing. The `/feature-spec` command is completely absent from seed data, and the Coach's new capabilities (Promise Verification, Honesty Verification, `criteria_verification`) are not reflected in any seed module. The Assumptions Manifest workflow from `/feature-spec` to Coach validation is not captured anywhere.

**Architecture Score: 58/100** (below the 60-point threshold — changes recommended before next seeding run)

**Impact**: Any Graphiti-powered context retrieval for `/feature-spec` or Coach validation workflows will return no results, causing Claude Code sessions to lack critical context about these capabilities.

---

## Review Details

- **Mode**: Architectural Review
- **Depth**: Comprehensive
- **Duration**: Full analysis of 12 seed modules + 4 source-of-truth files
- **Reviewer**: architectural-reviewer agent (manual analysis)

---

## Findings

### Finding 1: CRITICAL — No `/feature-spec` Episode in `seed_command_workflows.py`

**Evidence**: [seed_command_workflows.py](guardkit/knowledge/seed_command_workflows.py) contains 19 episodes covering all major commands. `/feature-spec` is not among them.

**Current state**: The `workflow_overview` episode (line 27) lists three alternative flows:
```python
"alternative_flows": [
    "Feature flow: /feature-plan -> /feature-build -> /task-complete (bulk)",
    "Review flow: /task-create task_type:review -> /task-review -> /task-complete",
    "Design-first: /task-work --design-only -> approve -> /task-work --implement-only"
]
```
None mention `/feature-spec`. The `workflow_feature_to_build` episode (line 109) also starts at `/feature-plan`, with no mention of `/feature-spec` as an upstream step.

**Impact**: When Claude Code queries "how do I specify a feature?", Graphiti returns nothing about `/feature-spec`. The entire Propose-Review methodology is invisible to context-aware sessions.

**Severity**: Must-fix

---

### Finding 2: CRITICAL — `workflow_overview` Missing Feature Spec Flow

**Evidence**: The `workflow_overview` episode's `alternative_flows` list doesn't include the spec-to-plan-to-build flow.

**Should include**: A fourth alternative flow:
```
"Spec-first flow: /feature-spec -> /feature-plan --context summary.md -> /feature-build"
```

**Impact**: The core workflow overview — the most-queried episode — lacks awareness of the specification-first development pattern.

**Severity**: Must-fix

---

### Finding 3: CRITICAL — `workflow_feature_to_build` Missing `/feature-spec` Step

**Evidence**: [seed_command_workflows.py:113-119](guardkit/knowledge/seed_command_workflows.py#L113-L119) shows the steps starting at `/feature-plan`. The expanded flow should optionally begin with `/feature-spec`.

**Current steps**:
```python
"steps": [
    "1. /feature-plan 'add OAuth2 authentication'",
    "2. /feature-build FEAT-A1B2",
    ...
]
```

**Should become** (or a new parallel episode):
```python
"steps": [
    "0. (Optional) /feature-spec 'add OAuth2 authentication' → generates Gherkin + assumptions",
    "1. /feature-plan 'add OAuth2 authentication' --context features/.../summary.md",
    "2. /feature-build FEAT-A1B2",
    ...
]
```

**Severity**: Must-fix

---

### Finding 4: CRITICAL — Missing Dedicated `/feature-spec` Command Episode

**Evidence**: Every other command has its own episode (`command_task_create`, `command_task_work`, `command_feature_plan`, etc.). `/feature-spec` needs one.

**Proposed episode**: `command_feature_spec` with:
- Purpose: Generate BDD Gherkin specifications using Propose-Review methodology
- Syntax: `/feature-spec "description" [--from file] [--output dir] [--auto] [--stack name] [--context file]`
- Methodology: 6-phase Propose-Review cycle (Context Gathering, Initial Proposal, Human Curation, Edge Case Expansion, Assumption Resolution, Output Generation)
- Outputs: `.feature` file, `_assumptions.yaml`, `_summary.md`
- Integration: Output feeds into `/feature-plan --context`
- Key principle: AI proposes, human curates (inverse of elicitation)

**Severity**: Must-fix

---

### Finding 5: HIGH — Coach's Promise Verification Not in Seed Data

**Evidence**: The [autobuild-coach.md](autobuild-coach.md) agent definition (lines 492-612) describes `criteria_verification` array with `criterion_id`, `result` (verified/rejected), and `notes`. Neither [seed_feature_build_architecture.py](guardkit/knowledge/seed_feature_build_architecture.py) nor [seed_agents.py](guardkit/knowledge/seed_agents.py) captures this.

**Current Coach agent seed** ([seed_agents.py:66-73](guardkit/knowledge/seed_agents.py#L66-L73)):
```python
("agent_autobuild_coach", {
    "capabilities": ["Implementation validation", "Independent test execution", "Acceptance criteria verification"],
    "critical_note": "Coach has READ-ONLY access, validates but cannot modify"
})
```

**Missing**: `"Promise Verification (criteria_verification array with criterion_id tracking)"`, `"Honesty Verification (pre-validated by CoachVerifier)"`

**Impact**: Context queries about "how does the Coach verify acceptance criteria?" miss the structured `criteria_verification` workflow entirely.

**Severity**: High

---

### Finding 6: HIGH — Coach's Honesty Verification Not in Seed Data

**Evidence**: [autobuild-coach.md:141-233](autobuild-coach.md#L141-L233) defines a complete Honesty Verification system: `CoachVerifier` pre-validates Player claims, provides honesty score (0.0-1.0), and surfaces discrepancies by type (test_result, file_existence, test_count).

**Current state**: No seed module references Honesty Verification, honesty_score, or CoachVerifier. The `COACH_CONSTRAINTS` fact in [role_constraint.py](guardkit/knowledge/facts/role_constraint.py) lists "Read task_work_results.json" but not "Factor in Honesty Verification results".

**Missing from**:
1. `seed_feature_build_architecture.py` — `feature_build_coach_agent` episode
2. `seed_agents.py` — `agent_autobuild_coach` episode
3. `seed_role_constraints.py` / `role_constraint.py` — `COACH_CONSTRAINTS`

**Severity**: High

---

### Finding 7: HIGH — Assumptions Manifest Workflow Not Captured Anywhere

**Evidence**: The `/feature-spec` command generates `_assumptions.yaml` (D9 in the feature spec). Per [FEATURE-SPEC-v2.md Section 4.3](docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md), assumptions flow through the pipeline:
```
/feature-spec → /feature-plan → AutoBuild Player → Coach validation
```

The Coach should validate Player implementation against both Gherkin AND the Assumptions Manifest. This workflow is documented in the feature spec but:
- Not seeded in any seed module
- Not referenced in `seed_feature_build_architecture.py`
- Not referenced in `seed_integration_points.py`

**Impact**: The assumptions-to-Coach validation flow — a key design goal of `/feature-spec` — is completely invisible to Graphiti. No session can learn about this workflow from seeded knowledge.

**Severity**: High

---

### Finding 8: MEDIUM — `seed_feature_build_architecture.py` Coach Episode Outdated

**Evidence**: The `feature_build_coach_agent` episode ([seed_feature_build_architecture.py:69-83](guardkit/knowledge/seed_feature_build_architecture.py#L69-L83)) describes a basic Coach:
```python
"validation_approach": [
    "Read task_work_results.json from Player's execution",
    "Run tests independently (trust but verify)",
    "Check acceptance criteria",
    "Either APPROVE or provide FEEDBACK"
]
```

This is accurate but incomplete. Missing from the validation approach:
- "Verify criteria_verification for each completion_promise (criterion_id tracking)"
- "Factor in Honesty Verification results (honesty_score, discrepancies)"
- "Validate against Gherkin scenarios when available (from /feature-spec)"
- "Validate against Assumptions Manifest when available"

**Severity**: Medium

---

### Finding 9: MEDIUM — `seed_integration_points.py` Missing Feature-Spec Integration

**Evidence**: [seed_integration_points.py](guardkit/knowledge/seed_integration_points.py) has only 2 episodes: `autobuild_to_taskwork` and `coach_result_path`. The `/feature-spec` → `/feature-plan` integration point is missing.

**Proposed addition**: An episode for `feature_spec_to_feature_plan` integration:
```python
("integration_feature_spec_to_plan", {
    "issue_type": "integration_point",
    "name": "feature_spec_to_feature_plan",
    "connects": ["/feature-spec", "/feature-plan"],
    "correct_pattern": "/feature-plan 'Feature' --context features/{name}/{name}_summary.md",
    "outputs_consumed": ["{name}.feature", "{name}_assumptions.yaml", "{name}_summary.md"],
    "rule": "feature-plan reads the _summary.md; Coach reads .feature and _assumptions.yaml during AutoBuild"
})
```

**Severity**: Medium

---

### Finding 10: MEDIUM — `seed_patterns.py` Player-Coach Pattern Missing Honesty/Promise Concepts

**Evidence**: The `pattern_player_coach` episode ([seed_patterns.py:62-69](guardkit/knowledge/seed_patterns.py#L62-L69)) describes the basic pattern but doesn't mention Promise Verification or Honesty Verification as capabilities of the pattern.

**Current**:
```python
"description": "Adversarial cooperation where Player implements and Coach validates.",
"benefits": ["Quality assurance", "Iterative improvement", "Trust but verify"]
```

**Should also include**: "Structured criteria tracking via Promise/Honesty Verification"

**Severity**: Medium

---

### Finding 11: LOW — `seed_quality_gate_phases.py` Complete But Could Reference Coach Specifics

**Evidence**: [seed_quality_gate_phases.py](guardkit/knowledge/seed_quality_gate_phases.py) covers all phases from 1 through 5.5. The Phase 4.3 (Quick Security Scan) mentioned in the Coach agent definition is not a separate episode but is implicitly part of Phase 4.

No changes strictly needed, but a note could clarify that in the AutoBuild context, Phase 4.3 results feed into Coach validation via `task_work_results.json["security"]`.

**Severity**: Low (informational)

---

### Finding 12: LOW — `COACH_CONSTRAINTS` Fact Missing New Capabilities

**Evidence**: [role_constraint.py:122-155](guardkit/knowledge/facts/role_constraint.py#L122-L155) defines `COACH_CONSTRAINTS`. The `must_do` list should include:
- "Create criteria_verification entry for each completion_promise"
- "Factor Honesty Verification results (honesty_score) into decisions"

**Current `must_do`**:
```python
"Read task_work_results.json from Player's execution",
"Run tests independently (trust but verify)",
"Verify ALL acceptance criteria met",
"Check code quality (SOLID/DRY/YAGNI)",
"Either APPROVE or provide specific FEEDBACK"
```

**Severity**: Low (the agent definition is the source of truth, but seeded facts should stay in sync)

---

## Assumptions Verified

| # | Assumption | Status | Evidence |
|---|------------|--------|----------|
| 1 | "Current seed data assumes no structured specification format exists for features" | **CONFIRMED** | No mention of Gherkin, `.feature` files, or Assumptions Manifest in any seed module |
| 2 | "Current seed data assumes Coach validates against plain-text acceptance criteria only" | **CONFIRMED** | Coach episodes only reference `acceptance_criteria` and `requirements_met` — no Gherkin, no Assumptions Manifest |
| 3 | "Current seed data may not capture the Assumptions Manifest → Coach validation flow" | **CONFIRMED** | Completely absent from all 17 seed modules |
| 4 | "seed_command_workflows episodes were last updated before /feature-spec was added" | **CONFIRMED** | No `/feature-spec` episode exists; workflow episodes don't reference it |

---

## Recommendations

### Must-Have (Priority 1)

| # | Change | Module | Description |
|---|--------|--------|-------------|
| R1 | Add `command_feature_spec` episode | `seed_command_workflows.py` | New episode with full command description, syntax, methodology, and outputs |
| R2 | Update `workflow_overview` | `seed_command_workflows.py` | Add spec-first flow to `alternative_flows` |
| R3 | Update `workflow_feature_to_build` | `seed_command_workflows.py` | Add optional `/feature-spec` as step 0 |
| R4 | Update `feature_build_coach_agent` | `seed_feature_build_architecture.py` | Add Promise Verification, Honesty Verification, and Gherkin/Assumptions validation to Coach description |
| R5 | Update `agent_autobuild_coach` | `seed_agents.py` | Add Promise Verification and Honesty Verification to capabilities |
| R6 | Add assumptions manifest workflow episode | `seed_feature_build_architecture.py` | New episode describing the `/feature-spec` → Assumptions Manifest → Coach validation flow |

### Nice-to-Have (Priority 2)

| # | Change | Module | Description |
|---|--------|--------|-------------|
| R7 | Add `integration_feature_spec_to_plan` | `seed_integration_points.py` | New integration point episode for `/feature-spec` → `/feature-plan` |
| R8 | Update `pattern_player_coach` | `seed_patterns.py` | Add Honesty/Promise Verification to pattern description |
| R9 | Update `COACH_CONSTRAINTS` | `facts/role_constraint.py` | Add `criteria_verification` and `honesty_score` to `must_do` list |
| R10 | Bump `SEEDING_VERSION` | `seed_helpers.py` | Increment version to force re-seed on next `guardkit graphiti seed` |

### Future Consideration (Priority 3)

| # | Change | Module | Description |
|---|--------|--------|-------------|
| R11 | Consider dedicated `seed_specification_workflow.py` | New module | If `/feature-spec` seeding grows beyond 3 episodes, extract to its own module |
| R12 | Add Phase 4.3 (Security Scan) episode | `seed_quality_gate_phases.py` | Currently implicit; could be explicit for AutoBuild context |

---

## Decision Matrix

| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| Address all Must-Have (R1-R6) | 85/100 | ~2-3 hours | Low | **Recommended** |
| Address Must-Have + Nice-to-Have (R1-R10) | 95/100 | ~4-5 hours | Low | Best outcome |
| Must-Have only, defer Nice-to-Have | 85/100 | ~2-3 hours | Low | Acceptable minimum |
| No changes | 58/100 | 0 | High (context gap persists) | Not recommended |

---

## Appendix

### Files Reviewed

| File | Status | Findings |
|------|--------|----------|
| `guardkit/knowledge/seed_command_workflows.py` | Gaps found | Missing `/feature-spec` episode; workflow episodes outdated |
| `guardkit/knowledge/seed_feature_build_architecture.py` | Gaps found | Coach episode missing Promise/Honesty Verification |
| `guardkit/knowledge/seed_quality_gate_phases.py` | Adequate | No changes needed (low-priority Phase 4.3 note only) |
| `guardkit/knowledge/seeding.py` | Adequate | Orchestrator structure fine; no new modules needed for R1-R6 |
| `guardkit/knowledge/seed_agents.py` | Gaps found | Coach agent capabilities list incomplete |
| `guardkit/knowledge/seed_integration_points.py` | Gaps found | Missing feature-spec-to-plan integration point |
| `guardkit/knowledge/seed_patterns.py` | Minor gap | Player-Coach pattern description could be richer |
| `guardkit/knowledge/seed_role_constraints.py` | Minor gap | Coach constraints missing new capabilities |
| `guardkit/knowledge/facts/role_constraint.py` | Minor gap | COACH_CONSTRAINTS `must_do` list incomplete |
| `.claude/agents/autobuild-coach.md` | Source of truth | Promise Verification, Honesty Verification, criteria_verification fully documented |
| `installer/core/commands/feature-spec.md` | Source of truth | Full 6-phase Propose-Review methodology documented |
| `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md` | Source of truth | D9 Assumptions Manifest, pipeline integration fully documented |
| `docs/commands/feature-spec.md` | Source of truth | Command reference documentation complete |

### Specific Episode Content Proposals

**R1: New `command_feature_spec` episode:**
```python
("command_feature_spec", {
    "entity_type": "command",
    "name": "/feature-spec",
    "purpose": "Generate BDD Gherkin specifications using Propose-Review methodology",
    "syntax": '/feature-spec "description" [--from file] [--output dir] [--auto] [--stack name] [--context file]',
    "methodology": "Specification by Example (Gojko Adzic) - AI proposes, human curates",
    "phases": [
        "Phase 1: Context Gathering (stack detection, codebase scan, Graphiti context)",
        "Phase 2: Initial Proposal (grouped scenarios: key-example, boundary, negative, edge-case)",
        "Phase 3: Human Curation (Accept/Reject/Modify/Add/Defer per group)",
        "Phase 4: Edge Case Expansion (security, concurrency, data integrity - optional)",
        "Phase 5: Assumption Resolution (confidence levels: high/medium/low)",
        "Phase 6: Output Generation (write .feature, _assumptions.yaml, _summary.md)"
    ],
    "outputs": {
        "feature_file": "{name}.feature - Gherkin scenarios in domain language",
        "assumptions_manifest": "{name}_assumptions.yaml - structured assumptions with confidence levels",
        "summary": "{name}_summary.md - feature summary for /feature-plan consumption"
    },
    "key_principles": [
        "AI proposes concrete examples, human curates (not elicitation/interrogation)",
        "Scenarios use domain language, not implementation language",
        "Every inferred value is an explicit assumption with confidence level",
        "Purely additive - does not modify existing files"
    ],
    "integration": "/feature-plan --context features/{name}/{name}_summary.md",
    "tags": ["@key-example", "@boundary", "@negative", "@edge-case", "@smoke", "@regression"]
})
```

**R6: New assumptions manifest workflow episode:**
```python
("feature_build_assumptions_flow", {
    "entity_type": "architecture",
    "name": "Assumptions Manifest Pipeline",
    "description": "How /feature-spec assumptions flow through the AutoBuild pipeline",
    "flow": [
        "1. /feature-spec generates _assumptions.yaml with confidence levels (high/medium/low)",
        "2. Human reviews assumptions during Gherkin curation (Phase 5)",
        "3. /feature-plan reads assumptions, flags low-confidence in task metadata",
        "4. AutoBuild Player reads assumptions as Graphiti context",
        "5. Coach validates implementation against BOTH Gherkin AND assumptions manifest",
        "6. If Player silently changed an assumption, Coach detects divergence"
    ],
    "gating_rules": {
        "high_confidence": "Auto-proceed",
        "medium_confidence": "Coach reviews, may auto-approve",
        "low_confidence": "Mandatory human review before implementation"
    },
    "key_insight": "Assumptions are defence-in-depth Layer 1 - they reduce ambiguity upstream before AutoBuild begins"
})
```
