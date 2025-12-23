#!/usr/bin/env python3
"""
Demo script for ProgressDisplay

Shows real-time turn-by-turn progress visualization.
Run: python3 examples/progress_display_demo.py
"""

import time
from guardkit.orchestrator.progress import ProgressDisplay


def demo_successful_workflow():
    """Demo: Successful 2-turn workflow with approval."""
    print("\n" + "="*70)
    print("Demo 1: Successful Workflow (2 turns → approved)")
    print("="*70 + "\n")

    with ProgressDisplay(max_turns=5) as display:
        # Turn 1: Player Implementation
        display.start_turn(1, "Player Implementation")
        time.sleep(0.5)

        display.update_turn("Reading requirements...", progress=20)
        time.sleep(0.3)

        display.update_turn("Writing code...", progress=40)
        time.sleep(0.4)

        display.update_turn("Writing tests...", progress=70)
        time.sleep(0.3)

        display.update_turn("Running tests...", progress=90)
        time.sleep(0.4)

        display.complete_turn("success", "3 files created, 2 tests passing")
        time.sleep(0.5)

        # Turn 2: Coach Validation
        display.start_turn(2, "Coach Validation")
        time.sleep(0.3)

        display.update_turn("Validating requirements...", progress=30)
        time.sleep(0.4)

        display.update_turn("Running tests independently...", progress=60)
        time.sleep(0.5)

        display.update_turn("Checking code quality...", progress=90)
        time.sleep(0.3)

        display.complete_turn("success", "All requirements met, approved")
        time.sleep(0.5)

        # Final Summary
        display.render_summary(
            total_turns=2,
            final_status="approved",
            details="Task completed successfully. All requirements met, tests passing."
        )


def demo_feedback_workflow():
    """Demo: Workflow with feedback iteration."""
    print("\n" + "="*70)
    print("Demo 2: Feedback Workflow (3 turns → approved)")
    print("="*70 + "\n")

    with ProgressDisplay(max_turns=5) as display:
        # Turn 1: Player Implementation
        display.start_turn(1, "Player Implementation")
        display.update_turn("Implementing OAuth2 flow...", progress=50)
        time.sleep(0.3)
        display.complete_turn("success", "OAuth2 implemented")
        time.sleep(0.3)

        # Turn 2: Coach finds issues
        display.start_turn(2, "Coach Validation")
        display.update_turn("Checking security...", progress=50)
        time.sleep(0.3)
        display.complete_turn("feedback", "2 issues: Missing HTTPS enforcement, no token refresh")
        time.sleep(0.5)

        # Turn 3: Player addresses feedback
        display.start_turn(3, "Player Implementation (Addressing Feedback)")
        display.update_turn("Adding HTTPS enforcement...", progress=30)
        time.sleep(0.3)
        display.update_turn("Implementing token refresh...", progress=70)
        time.sleep(0.3)
        display.complete_turn("success", "Fixed both issues")
        time.sleep(0.3)

        # Turn 4: Coach approves
        display.start_turn(4, "Coach Validation")
        display.update_turn("Re-validating security...", progress=50)
        time.sleep(0.3)
        display.complete_turn("success", "All issues resolved, approved")
        time.sleep(0.5)

        # Final Summary
        display.render_summary(
            total_turns=4,
            final_status="approved",
            details="Task completed after 2 feedback iterations. All security issues resolved."
        )


def demo_max_turns_exceeded():
    """Demo: Max turns exceeded workflow."""
    print("\n" + "="*70)
    print("Demo 3: Max Turns Exceeded (requires human review)")
    print("="*70 + "\n")

    with ProgressDisplay(max_turns=3) as display:
        # Turn 1
        display.start_turn(1, "Player Implementation")
        display.update_turn("Implementing feature...", progress=50)
        time.sleep(0.2)
        display.complete_turn("success", "Initial implementation")
        time.sleep(0.2)

        # Turn 2: Feedback
        display.start_turn(2, "Coach Validation")
        display.update_turn("Validating...", progress=50)
        time.sleep(0.2)
        display.complete_turn("feedback", "3 issues found")
        time.sleep(0.2)

        # Turn 3: Fixes
        display.start_turn(3, "Player Implementation (Iteration 2)")
        display.update_turn("Addressing issues...", progress=50)
        time.sleep(0.2)
        display.complete_turn("success", "Fixed 2/3 issues")
        time.sleep(0.2)

        # Turn 4: Still has issues
        display.start_turn(3, "Coach Validation")  # Note: Using turn 3 (max)
        display.update_turn("Re-validating...", progress=50)
        time.sleep(0.2)
        display.complete_turn("feedback", "1 issue remaining")
        time.sleep(0.5)

        # Final Summary
        display.render_summary(
            total_turns=3,
            final_status="max_turns_exceeded",
            details="Max turns reached without approval. Requires human review and intervention."
        )


def demo_error_handling():
    """Demo: Error handling during execution."""
    print("\n" + "="*70)
    print("Demo 4: Error Handling")
    print("="*70 + "\n")

    with ProgressDisplay(max_turns=3) as display:
        # Turn 1: Player Implementation
        display.start_turn(1, "Player Implementation")
        display.update_turn("Writing code...", progress=40)
        time.sleep(0.3)
        display.update_turn("Running tests...", progress=70)
        time.sleep(0.3)

        # Simulate error
        display.handle_error("Build failed: pytest exited with code 1\n  test_auth.py::test_login FAILED")
        time.sleep(0.5)

        display.complete_turn("error", "Build failed", error="pytest exited with code 1")
        time.sleep(0.5)

        # Final Summary
        display.render_summary(
            total_turns=1,
            final_status="error",
            details="Orchestration failed due to build error. Worktree preserved for debugging."
        )


if __name__ == "__main__":
    # Run all demos
    demo_successful_workflow()
    time.sleep(2)

    demo_feedback_workflow()
    time.sleep(2)

    demo_max_turns_exceeded()
    time.sleep(2)

    demo_error_handling()

    print("\n" + "="*70)
    print("Demo Complete")
    print("="*70 + "\n")
