"""
Implement Orchestrator for /task-review [I]mplement Flow

Orchestrates the complete enhanced [I]mplement flow that integrates all auto-detection
and generation components.

Dependencies (from Wave 2 tasks):
  • FW-002: extract_feature_slug() from id_generator.py
  • FW-003: extract_subtasks_from_review() from review_parser.py
  • FW-004: assign_implementation_modes() from implementation_mode_analyzer.py
  • FW-005: detect_parallel_groups() from parallel_analyzer.py
  • FW-006: generate_guide_content() from guide_generator.py
  • FW-007: generate_feature_readme() from readme_generator.py

This module provides the high-level orchestration that coordinates all these
components into a seamless workflow.

Usage:
    from lib.implement_orchestrator import handle_implement_option

    await handle_implement_option(
        review_task={"id": "TASK-REV-FW01", "title": "Review feature workflow"},
        review_report_path=".claude/reviews/TASK-REV-FW01-review-report.md"
    )

    # Creates:
    #   tasks/backlog/feature-workflow-streamlining/
    #   ├── README.md
    #   ├── IMPLEMENTATION-GUIDE.md
    #   ├── TASK-FW-001-create-feature-plan.md
    #   ├── TASK-FW-002-feature-slug-detection.md
    #   └── ...
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# Import dependencies from Wave 2 tasks
from lib.review_parser import extract_subtasks_from_review
from lib.implementation_mode_analyzer import assign_implementation_modes, get_mode_summary
from lib.parallel_analyzer import detect_parallel_groups, generate_workspace_names
from lib.guide_generator import generate_guide_content, write_guide_to_file
from lib.readme_generator import generate_feature_readme

# Import task type detection
from guardkit.lib.task_type_detector import detect_task_type


def extract_feature_slug(title: str) -> str:
    """
    Extract feature slug from review task title.

    Simple implementation that converts title to slug format.
    For more sophisticated logic, see FW-002 implementation.

    Examples:
        "Review feature workflow streamlining" → "feature-workflow-streamlining"
        "Review authentication architecture" → "authentication-architecture"
        "Architectural review of dark mode" → "dark-mode"

    Args:
        title: Review task title

    Returns:
        Feature slug (lowercase, hyphenated)
    """
    # Remove common review prefixes
    slug = title.lower()
    prefixes = [
        "review ",
        "architectural review of ",
        "review of ",
        "assess ",
        "evaluate ",
        "analyze "
    ]
    for prefix in prefixes:
        if slug.startswith(prefix):
            slug = slug[len(prefix):]
            break

    # Convert to slug: lowercase, spaces to hyphens, remove special chars
    slug = slug.replace(' ', '-').replace('_', '-')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')

    # Remove multiple consecutive hyphens
    while '--' in slug:
        slug = slug.replace('--', '-')

    # Trim hyphens from ends
    slug = slug.strip('-')

    return slug


class ImplementOrchestrator:
    """
    Orchestrates the enhanced [I]mplement flow for /task-review.

    Responsibilities:
      1. Extract feature slug from review task title
      2. Parse subtasks from review recommendations
      3. Assign implementation modes to subtasks
      4. Detect parallel execution groups
      5. Generate workspace names for Conductor
      6. Create subfolder structure
      7. Generate subtask files
      8. Generate IMPLEMENTATION-GUIDE.md
      9. Generate README.md
      10. Display summary and next steps
    """

    def __init__(self, review_task: Dict, review_report_path: str):
        """
        Initialize orchestrator with review task and report.

        Args:
            review_task: Review task dictionary with id, title, etc.
            review_report_path: Path to review report markdown file
        """
        self.review_task = review_task
        self.review_report_path = review_report_path
        self.feature_slug = None
        self.feature_name = None
        self.subtasks = []
        self.subfolder_path = None

    def extract_feature_info(self) -> None:
        """
        Extract feature slug and name from review task title.

        Uses FW-002 functionality.
        """
        # Extract slug using FW-002 function
        self.feature_slug = extract_feature_slug(self.review_task["title"])

        # Extract feature name (cleaned title without "Review" prefix)
        title = self.review_task["title"]
        # Remove common review prefixes
        for prefix in ["Review ", "Architectural review of ", "Review of "]:
            if title.startswith(prefix):
                title = title[len(prefix):]
        self.feature_name = title.strip()

    def parse_subtasks(self) -> None:
        """
        Parse subtasks from review report recommendations.

        Uses FW-003 functionality.
        """
        try:
            self.subtasks = extract_subtasks_from_review(
                self.review_report_path,
                self.feature_slug
            )
        except FileNotFoundError as e:
            print(f"❌ Error: Review report not found: {self.review_report_path}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error parsing review report: {e}")
            sys.exit(1)

        if not self.subtasks:
            print("⚠️  Warning: No subtasks found in review report recommendations.")
            print("    The review report may not contain a recommendations section.")
            sys.exit(1)

    def assign_modes(self) -> None:
        """
        Assign implementation modes to subtasks.

        Uses FW-004 functionality.
        """
        self.subtasks = assign_implementation_modes(self.subtasks)

    def detect_parallelism(self) -> None:
        """
        Detect parallel execution groups (waves).

        Uses FW-005 functionality.
        """
        self.subtasks = detect_parallel_groups(self.subtasks)

    def assign_workspaces(self) -> None:
        """
        Generate Conductor workspace names for parallel tasks.

        Uses FW-005 functionality.
        """
        workspace_map = generate_workspace_names(self.subtasks, self.feature_slug)

        # Update subtasks with workspace names
        for subtask in self.subtasks:
            task_id = subtask["id"]
            if task_id in workspace_map:
                subtask["conductor_workspace"] = workspace_map[task_id]

    def display_detection_summary(self) -> None:
        """
        Display auto-detected values before proceeding.
        """
        # Count waves
        waves = set(s.get("parallel_group") for s in self.subtasks if s.get("parallel_group"))
        wave_count = len(waves)

        # Get mode summary
        mode_summary = get_mode_summary(self.subtasks)

        print("\n" + "="*80)
        print("✅ Auto-detected Configuration:")
        print("="*80)
        print(f"   Feature slug: {self.feature_slug}")
        print(f"   Feature name: {self.feature_name}")
        print(f"   Subtasks: {len(self.subtasks)} (from review recommendations)")
        print(f"   Parallel groups: {wave_count} waves")
        print(f"\n   Implementation modes:")
        print(f"     • /task-work: {mode_summary['task-work']} tasks")
        print(f"     • Direct: {mode_summary['direct']} tasks")
        print(f"     • Manual: {mode_summary['manual']} tasks")
        print("="*80 + "\n")

    def create_subfolder(self) -> None:
        """
        Create subfolder for feature tasks.

        Creates: tasks/backlog/{feature-slug}/
        """
        self.subfolder_path = f"tasks/backlog/{self.feature_slug}"
        os.makedirs(self.subfolder_path, exist_ok=True)

    def generate_subtask_files(self) -> None:
        """
        Generate markdown files for each subtask.

        Each file includes:
          - Frontmatter with all metadata
          - Title, description
          - Files to modify
          - Dependencies
          - Implementation mode
          - Task type (auto-detected)
        """
        for subtask in self.subtasks:
            task_id = subtask["id"]
            title = subtask["title"]
            description = subtask.get("description", title)
            files = subtask.get("files", [])
            complexity = subtask.get("complexity", 5)
            implementation_mode = subtask.get("implementation_mode", "task-work")
            parallel_group = subtask.get("parallel_group")
            conductor_workspace = subtask.get("conductor_workspace", "")
            dependencies = subtask.get("dependencies", [])

            # Auto-detect task type based on title and description
            task_type = detect_task_type(title, description)

            # Generate filename
            slug = self._slugify(title)
            filename = f"{task_id}-{slug}.md"
            filepath = os.path.join(self.subfolder_path, filename)

            # Generate content
            content = f"""---
id: {task_id}
title: {title}
status: backlog
created: {self.review_task.get('created', '2025-12-04T00:00:00Z')}
updated: {self.review_task.get('created', '2025-12-04T00:00:00Z')}
priority: medium
tags: [{self.feature_slug}]
complexity: {complexity}
task_type: {task_type.value}
implementation_mode: {implementation_mode}
parallel_group: {parallel_group if parallel_group else 'null'}
conductor_workspace: {conductor_workspace if conductor_workspace else 'null'}
parent_review: {self.review_task['id']}
dependencies: {dependencies if dependencies else '[]'}
---

# {title}

## Description

{description}

## Acceptance Criteria

- [ ] Implementation complete
- [ ] Tests passing
- [ ] Code reviewed
- [ ] Documentation updated

## Files to Modify

{self._format_files_list(files)}

## Implementation Details

{self._get_implementation_guidance(implementation_mode)}

## Dependencies

{self._format_dependencies(dependencies)}

## Notes

Auto-generated from {self.review_task['id']} recommendations.
"""

            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

    def generate_implementation_guide(self) -> None:
        """
        Generate IMPLEMENTATION-GUIDE.md using FW-006 functionality.
        """
        output_path = os.path.join(self.subfolder_path, "IMPLEMENTATION-GUIDE.md")

        # Convert subtasks to format expected by guide_generator
        formatted_subtasks = []
        for subtask in self.subtasks:
            formatted = {
                "id": subtask["id"],
                "title": subtask["title"],
                "implementation_method": subtask.get("implementation_mode", "task-work"),
                "complexity": subtask.get("complexity", 5),
                "estimated_effort_days": subtask.get("effort_estimate", "1d"),
                "parallel_group": subtask.get("parallel_group"),
                "conductor_workspace": subtask.get("conductor_workspace", ""),
                "dependencies": subtask.get("dependencies", []),
            }
            formatted_subtasks.append(formatted)

        # Generate guide content
        guide_content = generate_guide_content(self.feature_name, formatted_subtasks)

        # Write to file
        write_guide_to_file(guide_content, output_path)

    def generate_readme(self) -> None:
        """
        Generate README.md using FW-007 functionality.
        """
        output_path = os.path.join(self.subfolder_path, "README.md")

        readme_content = generate_feature_readme(
            feature_name=self.feature_name,
            feature_slug=self.feature_slug,
            review_task_id=self.review_task["id"],
            review_report_path=self.review_report_path,
            subtasks=self.subtasks,
            output_path=output_path
        )

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)

    def generate_implementation_plans(self) -> None:
        """
        Generate implementation plan files for each subtask.

        Creates minimal implementation plans at .claude/task-plans/{task_id}-implementation-plan.md
        leveraging the "hot" AI context from the review analysis.

        Plan structure includes:
          - Task title and overview
          - Files to create/modify
          - Implementation approach
          - Dependencies
          - Test strategy
          - Estimated effort
        """
        # Ensure .claude/task-plans/ directory exists
        plans_dir = Path(".claude/task-plans")
        plans_dir.mkdir(parents=True, exist_ok=True)

        for subtask in self.subtasks:
            task_id = subtask["id"]
            title = subtask["title"]
            description = subtask.get("description", title)
            files = subtask.get("files", [])
            complexity = subtask.get("complexity", 5)
            dependencies = subtask.get("dependencies", [])
            implementation_mode = subtask.get("implementation_mode", "task-work")

            # Format files section
            files_section = self._format_plan_files(files)

            # Format dependencies section
            deps_section = self._format_plan_dependencies(dependencies)

            # Generate implementation approach based on task info
            approach_section = self._generate_implementation_approach(subtask)

            # Generate test strategy
            test_strategy = self._generate_test_strategy(implementation_mode, files)

            # Estimate effort
            loc_estimate = self._estimate_loc(complexity, len(files))
            duration_estimate = self._estimate_duration(complexity)

            # Generate plan content
            plan_content = f"""# Implementation Plan: {task_id}

## Task
{title}

## Overview
{description}

## Files to Create/Modify
{files_section}

## Implementation Approach
{approach_section}

## Dependencies
{deps_section}

## Test Strategy
{test_strategy}

## Estimated Effort
- LOC: ~{loc_estimate}
- Duration: {duration_estimate}
- Complexity: {complexity}/10
"""

            # Write plan file
            plan_path = plans_dir / f"{task_id}-implementation-plan.md"
            plan_path.write_text(plan_content, encoding='utf-8')

    def _format_plan_files(self, files: List[str]) -> str:
        """Format files list for implementation plan."""
        if not files:
            return "Files will be determined during implementation based on task requirements."
        return '\n'.join(f"- `{f}` - Implementation target" for f in files)

    def _format_plan_dependencies(self, dependencies: List[str]) -> str:
        """Format dependencies for implementation plan."""
        if not dependencies:
            return "None"
        return '\n'.join(f"- {dep}" for dep in dependencies)

    def _generate_implementation_approach(self, subtask: Dict) -> str:
        """Generate numbered implementation steps based on subtask info."""
        title = subtask.get("title", "")
        description = subtask.get("description", "")
        files = subtask.get("files", [])
        implementation_mode = subtask.get("implementation_mode", "task-work")

        steps = []

        # Step 1: Always start with understanding
        steps.append("1. Review task requirements and acceptance criteria")

        # Step 2: File-specific steps
        if files:
            if len(files) == 1:
                steps.append(f"2. Implement changes in `{files[0]}`")
            else:
                steps.append(f"2. Implement changes across {len(files)} files")
        else:
            steps.append("2. Identify and create/modify necessary files")

        # Step 3: Testing based on mode
        if implementation_mode == "task-work":
            steps.append("3. Write unit tests for new functionality")
            steps.append("4. Run tests and verify all pass")
            steps.append("5. Review code quality and architecture compliance")
        elif implementation_mode == "direct":
            steps.append("3. Verify changes work as expected")
            steps.append("4. Run existing tests to ensure no regressions")
        else:  # manual
            steps.append("3. Manually verify implementation")
            steps.append("4. Document any manual steps required")

        return '\n'.join(steps)

    def _generate_test_strategy(self, implementation_mode: str, files: List[str]) -> str:
        """Generate test strategy based on implementation mode."""
        if implementation_mode == "task-work":
            return """- Unit tests for new functionality
- Integration tests if multiple components affected
- Ensure 80%+ code coverage for new code
- Run full test suite to verify no regressions"""
        elif implementation_mode == "direct":
            return """- Run existing tests to verify no regressions
- Manual verification of changes
- Spot-check edge cases"""
        else:  # manual
            return """- Manual verification required
- Document test results
- Peer review recommended"""

    def _estimate_loc(self, complexity: int, file_count: int) -> int:
        """Estimate lines of code based on complexity and file count."""
        base_loc = 50
        complexity_multiplier = complexity / 5  # 0.2 to 2.0
        file_multiplier = max(1, file_count * 0.5)
        return int(base_loc * complexity_multiplier * file_multiplier)

    def _estimate_duration(self, complexity: int) -> str:
        """Estimate duration based on complexity."""
        if complexity <= 3:
            return "30 minutes - 1 hour"
        elif complexity <= 5:
            return "1-2 hours"
        elif complexity <= 7:
            return "2-4 hours"
        else:
            return "4-8 hours"

    def display_summary(self) -> None:
        """
        Display final summary and next steps.
        """
        # Build tree structure
        tree_lines = self._build_tree_structure()

        # Count waves
        waves = defaultdict(list)
        for subtask in self.subtasks:
            wave = subtask.get("parallel_group")
            if wave:
                waves[wave].append(subtask)

        print("\n" + "="*80)
        print("✅ Feature Implementation Structure Created")
        print("="*80)
        print(f"\nCreated: {self.subfolder_path}/")
        print("  ├── README.md")
        print("  ├── IMPLEMENTATION-GUIDE.md")
        for line in tree_lines:
            print(f"  {line}")

        print("\n" + "-"*80)
        print("📋 Execution Strategy:")
        print("-"*80)

        for wave_num in sorted(waves.keys()):
            wave_tasks = waves[wave_num]
            print(f"\nWave {wave_num}: {len(wave_tasks)} task{'s' if len(wave_tasks) > 1 else ''}")

            if len(wave_tasks) > 1:
                print(f"  ⚡ Parallel execution (Conductor recommended)")
                for task in wave_tasks:
                    workspace = task.get("conductor_workspace", "")
                    mode = task.get("implementation_mode", "task-work")
                    print(f"     • {task['id']}: {task['title']}")
                    if workspace:
                        print(f"       Workspace: {workspace}")
                    print(f"       Method: {mode}")
            else:
                task = wave_tasks[0]
                mode = task.get("implementation_mode", "task-work")
                print(f"  → Sequential execution")
                print(f"     • {task['id']}: {task['title']}")
                print(f"       Method: {mode}")

        print("\n" + "="*80)
        print("🚀 Next Steps:")
        print("="*80)
        print(f"1. Review: {self.subfolder_path}/IMPLEMENTATION-GUIDE.md")
        print(f"2. Review: {self.subfolder_path}/README.md")
        print(f"3. Start with Wave 1 tasks")
        if len(waves) > 1 and len(waves[1]) > 1:
            print(f"4. Use Conductor for parallel Wave 1 execution")
        print("="*80 + "\n")

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        # Convert to lowercase
        slug = text.lower()
        # Replace spaces and special chars with hyphens
        slug = slug.replace(' ', '-').replace('/', '-').replace('_', '-')
        # Remove non-alphanumeric except hyphens
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        # Remove multiple consecutive hyphens
        while '--' in slug:
            slug = slug.replace('--', '-')
        # Trim hyphens from ends
        slug = slug.strip('-')
        # Limit length
        if len(slug) > 50:
            slug = slug[:50].rstrip('-')
        return slug

    def _format_files_list(self, files: List[str]) -> str:
        """Format files list for markdown."""
        if not files:
            return "No files specified (will be determined during implementation)."
        return '\n'.join(f"- `{f}`" for f in files)

    def _format_dependencies(self, dependencies: List[str]) -> str:
        """Format dependencies list for markdown."""
        if not dependencies:
            return "No dependencies."
        return '\n'.join(f"- {dep}" for dep in dependencies)

    def _get_implementation_guidance(self, mode: str) -> str:
        """Get implementation guidance based on mode."""
        guidance = {
            "task-work": "Execute with `/task-work {task_id}` for full quality gates (architecture review, tests, code review).",
            "direct": "Implement directly with Claude Code. Changes are straightforward with clear acceptance criteria.",
            "manual": "Execute manually. Review output and verify correctness before proceeding."
        }
        return guidance.get(mode, "See IMPLEMENTATION-GUIDE.md for details.")

    def _build_tree_structure(self) -> List[str]:
        """Build tree structure for file display."""
        lines = []
        for idx, subtask in enumerate(self.subtasks):
            task_id = subtask["id"]
            title = subtask["title"]
            slug = self._slugify(title)
            filename = f"{task_id}-{slug}.md"

            # Determine tree character
            if idx == len(self.subtasks) - 1:
                lines.append(f"└── {filename}")
            else:
                lines.append(f"├── {filename}")

        return lines


async def handle_implement_option(review_task: Dict, review_report_path: str) -> None:
    """
    Enhanced [I]mplement handler with full auto-detection pipeline.

    This is the main entry point that orchestrates all Wave 2 functionality
    into a cohesive workflow.

    Args:
        review_task: Review task dictionary (from /task-review)
        review_report_path: Path to review report markdown file

    Workflow:
        1. Extract feature slug (FW-002)
        2. Parse subtasks from recommendations (FW-003)
        3. Assign implementation modes (FW-004)
        4. Detect parallel groups (FW-005)
        5. Generate Conductor workspaces (FW-005)
        6. Display auto-detected summary
        7. Create subfolder structure
        8. Generate subtask files
        9. Generate IMPLEMENTATION-GUIDE.md (FW-006)
        10. Generate README.md (FW-007)
        11. Display final summary and next steps

    Example:
        >>> await handle_implement_option(
        ...     review_task={"id": "TASK-REV-FW01", "title": "Review feature workflow"},
        ...     review_report_path=".claude/reviews/TASK-REV-FW01-review-report.md"
        ... )
        ✅ Auto-detected:
           Feature slug: feature-workflow
           Subtasks: 8 (from recommendations)
           Parallel groups: 3 waves

        Creating tasks/backlog/feature-workflow/
          ├── README.md
          ├── IMPLEMENTATION-GUIDE.md
          ├── TASK-FW-001-create-feature-plan.md
          └── ...
    """
    print("\n" + "="*80)
    print("🔄 Enhanced [I]mplement Flow - Auto-Detection Pipeline")
    print("="*80 + "\n")

    # Initialize orchestrator
    orchestrator = ImplementOrchestrator(review_task, review_report_path)

    # Step 1: Extract feature info
    print("Step 1/10: Extracting feature slug...")
    orchestrator.extract_feature_info()
    print(f"   ✓ Feature slug: {orchestrator.feature_slug}")
    print(f"   ✓ Feature name: {orchestrator.feature_name}")

    # Step 2: Parse subtasks
    print("\nStep 2/10: Parsing subtasks from review recommendations...")
    orchestrator.parse_subtasks()
    print(f"   ✓ Found {len(orchestrator.subtasks)} subtasks")

    # Step 3: Assign modes
    print("\nStep 3/10: Assigning implementation modes...")
    orchestrator.assign_modes()
    mode_summary = get_mode_summary(orchestrator.subtasks)
    print(f"   ✓ /task-work: {mode_summary['task-work']}, Direct: {mode_summary['direct']}, Manual: {mode_summary['manual']}")

    # Step 4: Detect parallelism
    print("\nStep 4/10: Detecting parallel execution groups...")
    orchestrator.detect_parallelism()
    waves = set(s.get("parallel_group") for s in orchestrator.subtasks if s.get("parallel_group"))
    print(f"   ✓ Organized into {len(waves)} waves")

    # Step 5: Assign workspaces
    print("\nStep 5/10: Generating Conductor workspace names...")
    orchestrator.assign_workspaces()
    workspace_count = sum(1 for s in orchestrator.subtasks if s.get("conductor_workspace"))
    print(f"   ✓ Assigned {workspace_count} workspace names")

    # Step 6: Display summary
    print("\nStep 6/10: Displaying auto-detected configuration...")
    orchestrator.display_detection_summary()

    # Step 7: Create subfolder
    print("Step 7/10: Creating subfolder structure...")
    orchestrator.create_subfolder()
    print(f"   ✓ Created {orchestrator.subfolder_path}/")

    # Step 8: Generate subtask files
    print("\nStep 8/10: Generating subtask files...")
    orchestrator.generate_subtask_files()
    print(f"   ✓ Generated {len(orchestrator.subtasks)} task files")

    # Step 8b: Generate implementation plans
    print("   Generating implementation plans...")
    orchestrator.generate_implementation_plans()
    print(f"   ✓ Generated {len(orchestrator.subtasks)} implementation plans")

    # Step 9: Generate implementation guide
    print("\nStep 9/10: Generating IMPLEMENTATION-GUIDE.md...")
    orchestrator.generate_implementation_guide()
    print("   ✓ Guide generated")

    # Step 10: Generate README
    print("\nStep 10/10: Generating README.md...")
    orchestrator.generate_readme()
    print("   ✓ README generated")

    # Final summary
    orchestrator.display_summary()


# Synchronous wrapper for non-async contexts
def handle_implement_option_sync(review_task: Dict, review_report_path: str) -> None:
    """
    Synchronous wrapper for handle_implement_option.

    Use this when calling from non-async code.
    """
    import asyncio
    asyncio.run(handle_implement_option(review_task, review_report_path))
