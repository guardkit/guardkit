#!/usr/bin/env python3
"""
Demo script showing phase gate validation integration with task-work workflow.

This demonstrates how phase gates catch protocol violations during execution
(early detection) rather than waiting until the final report.

Task Reference: TASK-ENF4
Epic: agent-invocation-enforcement
"""

from agent_invocation_tracker import AgentInvocationTracker, add_pending_phases
from phase_gate_validator import PhaseGateValidator, ValidationError


def simulate_successful_workflow():
    """Simulate a successful task-work execution with all gates passing."""
    print("=" * 60)
    print("SCENARIO 1: Successful Workflow (All Gates Pass)")
    print("=" * 60)
    print()

    # Initialize tracker and validator (Step 3.5 from task-work.md)
    tracker = AgentInvocationTracker()
    add_pending_phases(tracker, workflow_mode="standard")
    validator = PhaseGateValidator(tracker)

    print("🟢 Starting task-work execution...")
    print()

    # Phase 2: Planning
    print("📋 Phase 2: Implementation Planning")
    tracker.record_invocation("2", "task-manager", "Planning", "global")
    # [Agent executes...]
    tracker.mark_complete("2", duration_seconds=45)

    try:
        validator.validate_phase_completion("2", "Implementation Planning")
        print("   ✅ Phase 2 gate PASSED - Proceeding to Phase 2.5A\n")
    except ValidationError as e:
        print(f"   ❌ Phase 2 gate FAILED:\n{e}\n")
        return

    # Phase 2.5B: Architectural Review
    print("🏗️  Phase 2.5B: Architectural Review")
    tracker.record_invocation("2.5B", "architectural-reviewer", "Arch Review", "global")
    # [Agent executes...]
    tracker.mark_complete("2.5B", duration_seconds=30)

    try:
        validator.validate_phase_completion("2.5B", "Architectural Review")
        print("   ✅ Phase 2.5B gate PASSED - Proceeding to Phase 3\n")
    except ValidationError as e:
        print(f"   ❌ Phase 2.5B gate FAILED:\n{e}\n")
        return

    # Phase 3: Implementation
    print("💻 Phase 3: Implementation")
    tracker.record_invocation("3", "python-api-specialist", "Implementation", "local")
    # [Agent executes...]
    tracker.mark_complete("3", duration_seconds=120)

    try:
        validator.validate_phase_completion("3", "Implementation")
        print("   ✅ Phase 3 gate PASSED - Proceeding to Phase 4\n")
    except ValidationError as e:
        print(f"   ❌ Phase 3 gate FAILED:\n{e}\n")
        return

    # Phase 4: Testing
    print("🧪 Phase 4: Testing")
    tracker.record_invocation("4", "test-orchestrator", "Testing", "global")
    # [Agent executes...]
    tracker.mark_complete("4", duration_seconds=60)

    try:
        validator.validate_phase_completion("4", "Testing")
        print("   ✅ Phase 4 gate PASSED - Proceeding to Phase 4.5\n")
    except ValidationError as e:
        print(f"   ❌ Phase 4 gate FAILED:\n{e}\n")
        return

    # Phase 5: Code Review
    print("🔍 Phase 5: Code Review")
    tracker.record_invocation("5", "code-reviewer", "Review", "global")
    # [Agent executes...]
    tracker.mark_complete("5", duration_seconds=25)

    try:
        validator.validate_phase_completion("5", "Code Review")
        print("   ✅ Phase 5 gate PASSED - Proceeding to Phase 5.5\n")
    except ValidationError as e:
        print(f"   ❌ Phase 5 gate FAILED:\n{e}\n")
        return

    print("=" * 60)
    print("✅ SUCCESS: All phase gates passed!")
    print("=" * 60)
    print()


def simulate_phase3_violation():
    """Simulate Phase 3 gate violation (agent not invoked)."""
    print("=" * 60)
    print("SCENARIO 2: Phase 3 Gate Violation (Agent Not Invoked)")
    print("=" * 60)
    print()

    # Initialize tracker and validator
    tracker = AgentInvocationTracker()
    add_pending_phases(tracker, workflow_mode="standard")
    validator = PhaseGateValidator(tracker)

    print("🟢 Starting task-work execution...")
    print()

    # Phase 2: Planning (successful)
    print("📋 Phase 2: Implementation Planning")
    tracker.record_invocation("2", "task-manager", "Planning", "global")
    tracker.mark_complete("2", duration_seconds=45)

    try:
        validator.validate_phase_completion("2", "Implementation Planning")
        print("   ✅ Phase 2 gate PASSED - Proceeding to Phase 2.5B\n")
    except ValidationError as e:
        print(f"   ❌ Phase 2 gate FAILED:\n{e}\n")
        return

    # Phase 2.5B: Architectural Review (successful)
    print("🏗️  Phase 2.5B: Architectural Review")
    tracker.record_invocation("2.5B", "architectural-reviewer", "Arch Review", "global")
    tracker.mark_complete("2.5B", duration_seconds=30)

    try:
        validator.validate_phase_completion("2.5B", "Architectural Review")
        print("   ✅ Phase 2.5B gate PASSED - Proceeding to Phase 3\n")
    except ValidationError as e:
        print(f"   ❌ Phase 2.5B gate FAILED:\n{e}\n")
        return

    # Phase 3: Implementation (VIOLATION - no agent invocation)
    print("💻 Phase 3: Implementation")
    print("   ⚠️  WARNING: Claude implemented code directly without invoking agent!")
    print("   (This is the protocol violation we're trying to catch)\n")

    # NO tracker.record_invocation() call - this is the violation!
    # Claude did the work directly instead of using Task tool

    # Attempt to validate Phase 3
    try:
        validator.validate_phase_completion("3", "Implementation")
        print("   ✅ Phase 3 gate PASSED - Proceeding to Phase 4\n")
    except ValidationError as e:
        print("   ❌ Phase 3 gate FAILED!")
        print()
        print(str(e))
        print()
        print("=" * 60)
        print("🛑 EXECUTION STOPPED: Task moved to BLOCKED state")
        print("=" * 60)
        return

    print("   This line should never be reached!")


def simulate_comparison_without_gates():
    """Show what happens WITHOUT phase gates (old behavior)."""
    print("=" * 60)
    print("SCENARIO 3: Without Phase Gates (Old Behavior)")
    print("=" * 60)
    print()

    print("🟢 Starting task-work execution (without phase gates)...")
    print()

    print("📋 Phase 2: Claude does planning directly (no agent invocation)")
    print("   ⚠️  No validation - violation not detected!\n")

    print("🏗️  Phase 2.5B: Claude does arch review directly (no agent invocation)")
    print("   ⚠️  No validation - violation not detected!\n")

    print("💻 Phase 3: Claude implements directly (no agent invocation)")
    print("   ⚠️  No validation - violation not detected!\n")

    print("🧪 Phase 4: Claude writes tests directly (no agent invocation)")
    print("   ⚠️  No validation - violation not detected!\n")

    print("🔍 Phase 5: Claude reviews code directly (no agent invocation)")
    print("   ⚠️  No validation - violation not detected!\n")

    print("=" * 60)
    print("❌ PROBLEM: All violations reach final report generation!")
    print("=" * 60)
    print()
    print("Without phase gates:")
    print("  - Violations detected LATE (at end of execution)")
    print("  - No opportunity to correct mid-execution")
    print("  - Protocol bypassed completely")
    print()
    print("With phase gates (TASK-ENF4):")
    print("  - Violations detected EARLY (after each phase)")
    print("  - Immediate feedback and blocking")
    print("  - Task moved to BLOCKED state at point of violation")
    print()


def main():
    """Run all demo scenarios."""
    print("\n" + "=" * 60)
    print("PHASE GATE VALIDATION DEMO (TASK-ENF4)")
    print("=" * 60)
    print()

    # Scenario 1: Successful workflow
    simulate_successful_workflow()
    # input("Press Enter to continue to next scenario...\n")

    # Scenario 2: Phase 3 violation
    simulate_phase3_violation()
    # input("Press Enter to continue to next scenario...\n")

    # Scenario 3: Comparison without gates
    simulate_comparison_without_gates()

    print("=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print()
    print("Key Takeaways:")
    print("  1. Phase gates validate AFTER each phase completes")
    print("  2. Violations are caught EARLY (not at end)")
    print("  3. Task is moved to BLOCKED immediately on violation")
    print("  4. Clear error messages explain what's required")
    print()
    print("See TASK-ENF4 for implementation details.")
    print()


if __name__ == "__main__":
    main()
