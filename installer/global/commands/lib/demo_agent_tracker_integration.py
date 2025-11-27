#!/usr/bin/env python3
"""
Demonstration of AgentInvocationTracker integration with task-work.

This script demonstrates how the tracker would be used during a typical
task-work execution flow, showing agent discovery with source tracking
and invocation logging.

Task Reference: TASK-ENF2
"""

import time
from agent_invocation_tracker import AgentInvocationTracker, add_pending_phases
from agent_discovery import discover_agent_with_source


def simulate_task_work_execution():
    """
    Simulate a task-work execution with agent tracking.

    This demonstrates the integration pattern that would be used in
    the actual task-work.md command implementation.
    """
    print("\n" + "=" * 70)
    print("DEMONSTRATION: task-work with Agent Invocation Tracking")
    print("=" * 70)
    print("\nTask: TASK-042 - Implement user authentication API endpoint")
    print("Stack: Python (FastAPI)")
    print("Mode: Standard workflow\n")

    # Step 1: Initialize tracker
    print("Step 1: Initializing tracker and adding pending phases...")
    tracker = AgentInvocationTracker()
    add_pending_phases(tracker, workflow_mode="standard")
    time.sleep(1)

    # Step 2: Phase 2 - Implementation Planning
    print("\nStep 2: Phase 2 - Implementation Planning")
    agent_name, agent_source = discover_agent_with_source(
        phase="implementation",
        stack=["python"],
        keywords=["fastapi", "api", "async"]
    )
    print(f"  → Discovered agent: {agent_name} (source: {agent_source})")

    tracker.record_invocation(
        phase="2",
        agent_name=agent_name,
        phase_description="Planning",
        agent_source=agent_source
    )

    # Simulate agent execution
    print("  → Invoking agent...")
    time.sleep(1)

    # Mark complete
    tracker.mark_complete(phase="2", duration_seconds=45)
    print("  → Phase 2 complete!\n")
    time.sleep(1)

    # Step 3: Phase 2.5B - Architectural Review
    print("\nStep 3: Phase 2.5B - Architectural Review")
    agent_name, agent_source = discover_agent_with_source(
        phase="review",
        stack=["cross-stack"],
        keywords=["architecture", "solid", "patterns"]
    )
    print(f"  → Discovered agent: {agent_name} (source: {agent_source})")

    tracker.record_invocation(
        phase="2.5B",
        agent_name=agent_name,
        phase_description="Arch Review",
        agent_source=agent_source
    )

    # Simulate agent execution
    print("  → Invoking agent...")
    time.sleep(1)

    # Mark complete
    tracker.mark_complete(phase="2.5B", duration_seconds=30)
    print("  → Phase 2.5B complete!\n")
    time.sleep(1)

    # Step 4: Phase 3 - Implementation
    print("\nStep 4: Phase 3 - Implementation")
    agent_name, agent_source = discover_agent_with_source(
        phase="implementation",
        stack=["python"],
        keywords=["fastapi", "async", "pydantic"]
    )
    print(f"  → Discovered agent: {agent_name} (source: {agent_source})")

    tracker.record_invocation(
        phase="3",
        agent_name=agent_name,
        phase_description="Implementation",
        agent_source=agent_source
    )

    # Simulate agent execution
    print("  → Invoking agent...")
    time.sleep(1)

    # Mark complete
    tracker.mark_complete(
        phase="3",
        duration_seconds=120,
        files_modified=[
            "src/api/auth.py",
            "src/models/user.py",
            "src/schemas/auth.py"
        ]
    )
    print("  → Phase 3 complete!\n")
    time.sleep(1)

    # Step 5: Phase 4 - Testing
    print("\nStep 5: Phase 4 - Testing")
    agent_name, agent_source = discover_agent_with_source(
        phase="testing",
        stack=["python"],
        keywords=["pytest", "testing", "coverage"]
    )
    print(f"  → Discovered agent: {agent_name} (source: {agent_source})")

    tracker.record_invocation(
        phase="4",
        agent_name=agent_name,
        phase_description="Testing",
        agent_source=agent_source
    )

    # Simulate agent execution
    print("  → Invoking agent...")
    time.sleep(1)

    # Mark complete
    tracker.mark_complete(phase="4", duration_seconds=60)
    print("  → Phase 4 complete!\n")
    time.sleep(1)

    # Step 6: Phase 5 - Code Review
    print("\nStep 6: Phase 5 - Code Review")
    agent_name, agent_source = discover_agent_with_source(
        phase="review",
        stack=["cross-stack"],
        keywords=["code-quality", "review", "best-practices"]
    )
    print(f"  → Discovered agent: {agent_name} (source: {agent_source})")

    tracker.record_invocation(
        phase="5",
        agent_name=agent_name,
        phase_description="Review",
        agent_source=agent_source
    )

    # Simulate agent execution
    print("  → Invoking agent...")
    time.sleep(1)

    # Mark complete
    tracker.mark_complete(phase="5", duration_seconds=25)
    print("  → Phase 5 complete!\n")
    time.sleep(1)

    # Final summary
    print("\n" + "=" * 70)
    print("TASK EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Total Phases Completed: {tracker.get_completed_count()}/5")
    print(f"Total Duration: {sum(inv.get('duration', 0) for inv in tracker.invocations)}s")
    print("\nAgent Sources Used:")
    sources = {}
    for inv in tracker.invocations:
        if inv["status"] == "completed":
            source = inv.get("agent_source", "unknown")
            sources[source] = sources.get(source, 0) + 1

    for source, count in sorted(sources.items()):
        icon = tracker._get_source_icon(source)
        print(f"  {icon} {source}: {count} agent(s)")

    print("\nFinal Invocation Log:")
    tracker.display_log()


def simulate_blocked_task():
    """
    Simulate a task that gets blocked during Phase 3.

    This demonstrates how the tracker handles skipped phases.
    """
    print("\n" + "=" * 70)
    print("DEMONSTRATION: Blocked Task (Phase 3 fails)")
    print("=" * 70)
    print("\nTask: TASK-043 - Implement payment processing")
    print("Stack: Python (FastAPI)")
    print("Mode: Standard workflow\n")

    tracker = AgentInvocationTracker()
    add_pending_phases(tracker, workflow_mode="standard")
    time.sleep(1)

    # Phase 2 - Planning
    print("\nPhase 2: Planning")
    agent_name, agent_source = discover_agent_with_source(
        phase="implementation",
        stack=["python"]
    )
    tracker.record_invocation("2", agent_name, "Planning", agent_source)
    time.sleep(1)
    tracker.mark_complete("2", 40)

    # Phase 2.5B - Architectural Review
    print("\nPhase 2.5B: Architectural Review")
    agent_name, agent_source = discover_agent_with_source(
        phase="review",
        stack=["cross-stack"]
    )
    tracker.record_invocation("2.5B", agent_name, "Arch Review", agent_source)
    time.sleep(1)
    tracker.mark_complete("2.5B", 35)

    # Phase 3 - Implementation (BLOCKED)
    print("\nPhase 3: Implementation")
    agent_name, agent_source = discover_agent_with_source(
        phase="implementation",
        stack=["python"]
    )
    tracker.record_invocation("3", agent_name, "Implementation", agent_source)
    time.sleep(1)

    # Simulate failure
    print("  ❌ Implementation failed! Compilation errors detected.")
    tracker.mark_skipped("3", "Compilation failed")

    # Phases 4 and 5 are not executed
    tracker.mark_skipped("4", "Phase 3 blocked")
    tracker.mark_skipped("5", "Phase 3 blocked")

    print("\n" + "=" * 70)
    print("TASK BLOCKED - Fix compilation errors and retry")
    print("=" * 70)


if __name__ == '__main__':
    # Run standard workflow demo
    simulate_task_work_execution()

    print("\n\n")
    time.sleep(2)

    # Run blocked task demo
    simulate_blocked_task()

    print("\n" + "=" * 70)
    print("Demonstration complete!")
    print("=" * 70 + "\n")
