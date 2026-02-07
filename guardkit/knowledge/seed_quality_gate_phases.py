"""
Quality gate phases seeding for GuardKit knowledge graph.

Seeds knowledge about the 5-phase quality gate structure into Graphiti
for context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_quality_gate_phases(client) -> None:
    """Seed knowledge about the 5-phase quality gate structure.

    Creates 12 episodes covering all phases from 1 through 5.5.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("phases_overview", {
            "entity_type": "architecture",
            "name": "Quality Gate Phases",
            "description": "task-work executes through 5 major phases with quality gates",
            "phases": [
                "Phase 1: Load Task Context",
                "Phase 2: Implementation Planning",
                "Phase 2.5: Architectural Review + Pattern Suggestions",
                "Phase 2.7: Complexity Evaluation",
                "Phase 2.8: Human Checkpoint (design approval)",
                "Phase 3: Implementation",
                "Phase 4: Testing",
                "Phase 4.5: Fix Loop (up to 3 iterations)",
                "Phase 5: Code Review",
                "Phase 5.5: Plan Audit"
            ],
            "critical_gates": [
                "Phase 2.5B: Architectural review blocks if SOLID/DRY/YAGNI violated",
                "Phase 2.8: Human must approve plan before implementation",
                "Phase 4.5: Tests must pass, coverage must meet threshold",
                "Phase 5: Code review must pass quality checks"
            ]
        }),
        ("phase_1_load", {
            "entity_type": "phase",
            "phase_number": "1",
            "name": "Load Task Context",
            "purpose": "Load task file, detect stack, gather requirements",
            "actions": [
                "Read task markdown from tasks/",
                "Parse YAML frontmatter",
                "Detect project technology stack",
                "Identify acceptance criteria"
            ]
        }),
        ("phase_1_6_clarification", {
            "entity_type": "phase",
            "phase_number": "1.6",
            "name": "Clarifying Questions",
            "purpose": "Ask user for clarification on ambiguous requirements",
            "gating": "Only runs if requirements are ambiguous",
            "skip_with": "--no-questions flag"
        }),
        ("phase_2_planning", {
            "entity_type": "phase",
            "phase_number": "2",
            "name": "Implementation Planning",
            "purpose": "Create detailed implementation plan",
            "actions": [
                "Analyze requirements and acceptance criteria",
                "Design solution approach",
                "Identify files to create/modify",
                "Plan test strategy",
                "Estimate complexity"
            ],
            "outputs": "implementation_plan.md in .claude/task-plans/"
        }),
        ("phase_2_5_review", {
            "entity_type": "phase",
            "phase_number": "2.5",
            "name": "Architectural Review + Pattern Suggestions",
            "purpose": "Review plan for architectural soundness",
            "subphases": {
                "2.5A": "Pattern Suggestions - Suggest applicable design patterns",
                "2.5B": "Architectural Review - Check SOLID, DRY, YAGNI compliance"
            },
            "can_block": True,
            "block_conditions": "Major SOLID/DRY/YAGNI violations"
        }),
        ("phase_2_7_complexity", {
            "entity_type": "phase",
            "phase_number": "2.7",
            "name": "Complexity Evaluation",
            "purpose": "Score task complexity 1-10 for process scaling",
            "scoring": {
                "1-3": "Simple - may use --micro mode",
                "4-6": "Medium - standard workflow",
                "7-10": "Complex - may need splitting or extra review"
            }
        }),
        ("phase_2_8_checkpoint", {
            "entity_type": "phase",
            "phase_number": "2.8",
            "name": "Human Checkpoint",
            "purpose": "Human approval of implementation plan before coding",
            "actions": [
                "Display implementation plan summary",
                "Present decision options: [A]pprove / [R]evise / [S]kip",
                "If Approve: Proceed to Phase 3",
                "If Revise: Return to Phase 2 with feedback"
            ],
            "critical": "This is the last stop before implementation begins",
            "design_only_stops_here": "--design-only flag stops at this phase"
        }),
        ("phase_3_implementation", {
            "entity_type": "phase",
            "phase_number": "3",
            "name": "Implementation",
            "purpose": "Execute the implementation plan",
            "actions": [
                "Create/modify files per plan",
                "Write production code",
                "Write tests (TDD: tests first, Standard: code first)"
            ],
            "implement_only_starts_here": "--implement-only flag starts at this phase"
        }),
        ("phase_4_testing", {
            "entity_type": "phase",
            "phase_number": "4",
            "name": "Testing",
            "purpose": "Run tests and verify coverage",
            "actions": [
                "Execute test suite",
                "Check coverage threshold",
                "Verify all acceptance criteria testable"
            ],
            "thresholds": {
                "coverage": "80% minimum (configurable)",
                "tests_passing": "100% required"
            }
        }),
        ("phase_4_5_fixloop", {
            "entity_type": "phase",
            "phase_number": "4.5",
            "name": "Fix Loop",
            "purpose": "Iterate to fix failing tests or coverage gaps",
            "max_iterations": 3,
            "actions": [
                "If tests fail: Analyze failure, apply fix, re-run",
                "If coverage low: Add tests, re-run",
                "Repeat until pass or max iterations"
            ],
            "failure_handling": "If still failing after 3 iterations, task is blocked"
        }),
        ("phase_5_review", {
            "entity_type": "phase",
            "phase_number": "5",
            "name": "Code Review",
            "purpose": "Review implemented code for quality",
            "checks": [
                "SOLID principles adherence",
                "DRY (no duplication)",
                "YAGNI (no over-engineering)",
                "Code style and conventions",
                "Security considerations"
            ]
        }),
        ("phase_5_5_audit", {
            "entity_type": "phase",
            "phase_number": "5.5",
            "name": "Plan Audit",
            "purpose": "Verify implementation matches plan",
            "actions": [
                "Compare implemented files to planned files",
                "Verify all acceptance criteria addressed",
                "Check for scope creep"
            ]
        })
    ]

    await _add_episodes(client, episodes, "quality_gate_phases", "quality gate phases", entity_type="quality_gate_phase")
