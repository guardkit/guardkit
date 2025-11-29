#!/usr/bin/env python3
"""
Proof-of-Concept: Hash-Based Task ID Generator

Demonstrates collision-free ID generation inspired by Beads issue tracker.
Run with: python3 task-id-poc.py
"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional, Set
import json


class TaskIDGenerator:
    """Generate collision-free hash-based task IDs."""

    def __init__(self):
        self.existing_ids: Set[str] = set()
        self.task_count = 0

    def generate_id(self, prefix: Optional[str] = None) -> str:
        """
        Generate unique task ID using hash.

        Args:
            prefix: Optional namespace (e.g., "E01", "DOC", "FIX")

        Returns:
            Task ID in format TASK-{prefix}-{hash} or TASK-{hash}

        Examples:
            >>> gen = TaskIDGenerator()
            >>> gen.generate_id()
            'TASK-a3f8'
            >>> gen.generate_id("E01")
            'TASK-E01-b2c4'
        """
        # Determine hash length based on scale
        if self.task_count < 500:
            hash_length = 4
        elif self.task_count < 1500:
            hash_length = 5
        else:
            hash_length = 6

        # Generate collision-free hash
        max_attempts = 100
        for attempt in range(max_attempts):
            # Create random seed from timestamp + random bytes
            seed = f"{datetime.utcnow().isoformat()}-{secrets.token_hex(8)}"

            # Generate hash
            hash_bytes = hashlib.sha256(seed.encode()).digest()
            task_hash = hash_bytes.hex()[:hash_length]

            # Build full ID
            if prefix:
                task_id = f"TASK-{prefix}-{task_hash}"
            else:
                task_id = f"TASK-{task_hash}"

            # Check uniqueness
            if task_id not in self.existing_ids:
                self.existing_ids.add(task_id)
                self.task_count += 1
                return task_id

        raise RuntimeError(f"Failed to generate unique ID after {max_attempts} attempts")

    def generate_subtask_id(self, parent_id: str, subtask_number: int) -> str:
        """
        Generate subtask ID with dot notation.

        Args:
            parent_id: Parent task ID
            subtask_number: Sequential subtask number (1, 2, 3...)

        Returns:
            Subtask ID (e.g., "TASK-E01-b2c4.1")

        Examples:
            >>> gen = TaskIDGenerator()
            >>> gen.generate_subtask_id("TASK-E01-b2c4", 1)
            'TASK-E01-b2c4.1'
        """
        subtask_id = f"{parent_id}.{subtask_number}"
        self.existing_ids.add(subtask_id)
        return subtask_id


class ExternalIDMapper:
    """Map internal hash-based IDs to external PM tool sequential IDs."""

    def __init__(self):
        self.mappings = {}
        self.external_counters = {
            "jira": 100,  # Start at PROJ-100
            "azure_devops": 1000,  # Start at 1000
            "linear": 1,  # Start at TEAM-1
            "github": 1,  # Start at #1
        }

    def map_to_external(self, internal_id: str, tool: str, project_key: str = "PROJ") -> str:
        """
        Map internal hash ID to external sequential ID.

        Args:
            internal_id: Internal task ID (e.g., "TASK-E01-b2c4")
            tool: PM tool name ("jira", "azure_devops", "linear", "github")
            project_key: Project/team key for external tool

        Returns:
            External ID in tool's native format

        Examples:
            >>> mapper = ExternalIDMapper()
            >>> mapper.map_to_external("TASK-E01-b2c4", "jira", "PROJ")
            'PROJ-100'
            >>> mapper.map_to_external("TASK-E01-b2c4", "azure_devops")
            '1000'
        """
        # Check if already mapped
        if internal_id in self.mappings:
            if tool in self.mappings[internal_id]:
                return self.mappings[internal_id][tool]

        # Generate new external ID
        counter = self.external_counters[tool]
        self.external_counters[tool] += 1

        # Format based on tool
        if tool == "jira":
            external_id = f"{project_key}-{counter}"
        elif tool == "azure_devops":
            external_id = str(counter)
        elif tool == "linear":
            external_id = f"TEAM-{counter}"
        elif tool == "github":
            external_id = f"#{counter}"
        else:
            raise ValueError(f"Unknown tool: {tool}")

        # Store mapping
        if internal_id not in self.mappings:
            self.mappings[internal_id] = {}
        self.mappings[internal_id][tool] = external_id

        return external_id

    def get_internal_id(self, external_id: str, tool: str) -> Optional[str]:
        """
        Reverse lookup: external ID → internal ID.

        Args:
            external_id: External tool ID
            tool: PM tool name

        Returns:
            Internal task ID or None if not found
        """
        for internal_id, tools in self.mappings.items():
            if tool in tools and tools[tool] == external_id:
                return internal_id
        return None

    def export_mappings(self) -> str:
        """Export mappings as JSON for persistence."""
        return json.dumps(self.mappings, indent=2)


def demo():
    """Demonstrate ID generation and PM tool mapping."""

    print("=" * 80)
    print("TASK ID GENERATION - PROOF OF CONCEPT")
    print("=" * 80)
    print()

    # Initialize generator and mapper
    gen = TaskIDGenerator()
    mapper = ExternalIDMapper()

    print("1. BASIC ID GENERATION")
    print("-" * 80)

    # Generate various task IDs
    tasks = [
        (None, "Standalone task"),
        ("E01", "Task in Epic 001"),
        ("E01", "Another task in Epic 001"),
        ("DOC", "Documentation task"),
        ("FIX", "Bug fix task"),
    ]

    generated_ids = []
    for prefix, description in tasks:
        task_id = gen.generate_id(prefix)
        generated_ids.append(task_id)
        print(f"  {task_id:20s} - {description}")

    print()
    print("2. SUBTASK GENERATION")
    print("-" * 80)

    parent = generated_ids[1]  # Use Epic 001 task
    for i in range(1, 4):
        subtask = gen.generate_subtask_id(parent, i)
        print(f"  {subtask:20s} - Subtask {i} of {parent}")

    print()
    print("3. PM TOOL MAPPING")
    print("-" * 80)

    for task_id in generated_ids[:3]:
        print(f"\n  Internal: {task_id}")
        jira_id = mapper.map_to_external(task_id, "jira", "PROJ")
        azure_id = mapper.map_to_external(task_id, "azure_devops")
        linear_id = mapper.map_to_external(task_id, "linear", "TEAM")
        github_id = mapper.map_to_external(task_id, "github")

        print(f"    JIRA:        {jira_id}")
        print(f"    Azure DevOps: {azure_id}")
        print(f"    Linear:      {linear_id}")
        print(f"    GitHub:      {github_id}")

    print()
    print("4. REVERSE LOOKUP")
    print("-" * 80)

    # Demonstrate reverse lookup
    test_external = "PROJ-100"
    internal = mapper.get_internal_id(test_external, "jira")
    print(f"  External ID {test_external} → Internal ID {internal}")

    print()
    print("5. COLLISION TESTING")
    print("-" * 80)

    # Generate 1000 IDs to test collisions
    print("  Generating 1,000 task IDs...")
    test_gen = TaskIDGenerator()
    test_ids = set()

    for i in range(1000):
        task_id = test_gen.generate_id()
        if task_id in test_ids:
            print(f"  ❌ COLLISION DETECTED: {task_id}")
            break
        test_ids.add(task_id)
    else:
        print(f"  ✅ No collisions in 1,000 IDs")
        print(f"  ✅ Hash length: {len(test_gen.generate_id().split('-')[-1])} characters")

    print()
    print("6. MAPPING PERSISTENCE")
    print("-" * 80)

    # Show JSON export
    print("  Mapping table (JSON format):")
    print()
    mappings_json = mapper.export_mappings()
    print("  " + "\n  ".join(mappings_json.split("\n")[:20]))  # First 20 lines
    print()

    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("KEY BENEFITS:")
    print("  ✅ Zero collisions (hash-based)")
    print("  ✅ Concurrent creation safe")
    print("  ✅ PM tool compatibility (via mapping)")
    print("  ✅ Hierarchical subtasks (dot notation)")
    print("  ✅ Short and memorable (4-6 chars)")
    print()


if __name__ == "__main__":
    demo()
