#!/usr/bin/env python3
"""
Demonstration script for task completion in Conductor workspaces.

This script demonstrates that the fixed task completion logic works correctly
in both the main repository and Conductor worktrees.

Usage:
    # From main repo
    python3 tests/demo_task_completion.py TASK-XXX

    # From Conductor worktree
    cd .conductor/carthage
    python3 tests/demo_task_completion.py TASK-XXX

Author: Claude (Anthropic)
Created: 2025-11-27
"""

import sys
import os
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "installer" / "global" / "commands" / "lib"))

from task_completion_helper import find_task_file, complete_task
from git_state_helper import get_git_root


def demo_find_task(task_id: str):
    """Demonstrate finding a task from any directory."""
    print("\n" + "=" * 60)
    print("DEMO: Finding Task File (Conductor-aware)")
    print("=" * 60)

    print(f"\nCurrent working directory: {os.getcwd()}")

    try:
        git_root = get_git_root()
        print(f"Git repository root: {git_root}")

        if ".conductor" in os.getcwd():
            print("✅ Running from Conductor worktree")
        else:
            print("✅ Running from main repository")

    except Exception as e:
        print(f"⚠️  Not in git repository: {e}")

    print(f"\nSearching for task: {task_id}")

    try:
        task_path = find_task_file(task_id)
        print(f"✅ Found task: {task_path}")
        print(f"   Directory: {task_path.parent}")
        print(f"   Filename: {task_path.name}")

        # Check if path is in main repo or worktree
        if ".conductor" in str(task_path):
            print("   ❌ WARNING: Task found in worktree (should be in main repo!)")
        else:
            print("   ✅ Task correctly found in main repository")

        return task_path

    except FileNotFoundError as e:
        print(f"❌ Task not found: {e}")
        return None


def demo_complete_task(task_id: str, dry_run: bool = True):
    """Demonstrate completing a task."""
    print("\n" + "=" * 60)
    print("DEMO: Complete Task (Conductor-aware)")
    print("=" * 60)

    if dry_run:
        print("⚠️  DRY RUN MODE - No actual changes will be made")
        print("   Set dry_run=False to perform actual completion")

    print(f"\nTask ID: {task_id}")

    if dry_run:
        # Just demonstrate finding and showing what would happen
        try:
            task_path = find_task_file(task_id)
            print(f"\n✅ Task found: {task_path}")

            print("\nWhat would happen:")
            print(f"1. Move task file to: tasks/completed/YYYY-MM/{task_path.name}")
            print(f"2. Update task metadata: status → 'completed'")
            print(f"3. Archive implementation plan (if exists)")
            print(f"4. Archive implementation summary (if exists)")
            print(f"5. Archive completion report (if exists)")

            # Check for documents
            try:
                git_root = get_git_root()

                plan_path = git_root / ".claude" / "task-plans" / f"{task_id}-implementation-plan.md"
                summary_path = git_root / f"{task_id}-IMPLEMENTATION-SUMMARY.md"
                report_path = git_root / f"{task_id}-COMPLETION-REPORT.md"

                print("\nDocument check:")
                if plan_path.exists():
                    print(f"   ✅ Implementation plan found: {plan_path}")
                else:
                    print(f"   ⚪ No implementation plan")

                if summary_path.exists():
                    print(f"   ✅ Implementation summary found: {summary_path}")
                else:
                    print(f"   ⚪ No implementation summary")

                if report_path.exists():
                    print(f"   ✅ Completion report found: {report_path}")
                else:
                    print(f"   ⚪ No completion report")

            except Exception as e:
                print(f"   ⚠️  Could not check for documents: {e}")

        except FileNotFoundError as e:
            print(f"❌ Cannot complete - task not found: {e}")

    else:
        # Actually complete the task
        try:
            result = complete_task(task_id)
            print("\n" + "=" * 60)
            print("✅ TASK COMPLETED SUCCESSFULLY")
            print("=" * 60)
            print(f"Task ID: {result['task_id']}")
            print(f"New location: {result['new_path']}")
            print(f"Documents archived: {result['documents_archived']}")
            print(f"Completed at: {result['completed_at']}")

        except Exception as e:
            print(f"❌ Task completion failed: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main demonstration."""
    if len(sys.argv) < 2:
        print("Usage: python3 demo_task_completion.py TASK-XXX [--complete]")
        print("\nExamples:")
        print("  python3 demo_task_completion.py TASK-001          # Dry run (find only)")
        print("  python3 demo_task_completion.py TASK-001 --complete  # Actually complete")
        sys.exit(1)

    task_id = sys.argv[1]
    do_complete = "--complete" in sys.argv

    # Demo 1: Find task
    task_path = demo_find_task(task_id)

    if task_path and do_complete:
        # Demo 2: Complete task (actual completion)
        response = input("\n⚠️  This will actually complete the task. Continue? (y/N): ")
        if response.lower() == 'y':
            demo_complete_task(task_id, dry_run=False)
        else:
            print("Cancelled.")
    elif task_path:
        # Demo 2: Show what would happen (dry run)
        demo_complete_task(task_id, dry_run=True)

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
