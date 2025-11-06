#!/usr/bin/env python3
"""
Example usage of the Multi-Source Agent Scanner

Demonstrates how to scan agent definitions from multiple sources
and query the resulting inventory.
"""

from pathlib import Path
import sys

# Add lib to path
lib_path = Path(__file__).parent.parent / "installer" / "global" / "lib"
sys.path.insert(0, str(lib_path))

from agent_scanner import MultiSourceAgentScanner


def main():
    """Demonstrate agent scanner usage"""

    print("=" * 70)
    print("Multi-Source Agent Scanner - Usage Example")
    print("=" * 70)
    print()

    # Example 1: Basic scanning
    print("Example 1: Scan all agent sources")
    print("-" * 70)

    scanner = MultiSourceAgentScanner()
    inventory = scanner.scan()

    print()
    print(f"Found {len(inventory.custom_agents)} custom agents")
    print(f"Found {len(inventory.template_agents)} template agents")
    print(f"Found {len(inventory.global_agents)} global agents")
    print(f"Total: {len(inventory.all_agents())} agents")

    print()
    print("=" * 70)
    print()

    # Example 2: Find specific agent
    print("Example 2: Find specific agent by name")
    print("-" * 70)

    agent_name = "task-manager"
    agent = inventory.find_by_name(agent_name)

    if agent:
        print(f"✓ Found agent: {agent.name}")
        print(f"  Description: {agent.description}")
        print(f"  Source: {agent.source}")
        print(f"  Priority: {agent.priority}")
        print(f"  Tools: {', '.join(agent.tools) if agent.tools else 'None'}")
        print(f"  Tags: {', '.join(agent.tags) if agent.tags else 'None'}")
        print(f"  Path: {agent.source_path}")
    else:
        print(f"✗ Agent '{agent_name}' not found")

    print()
    print("=" * 70)
    print()

    # Example 3: Check if agent exists
    print("Example 3: Check for agent existence")
    print("-" * 70)

    test_agents = ["task-manager", "react-specialist", "nonexistent-agent"]

    for name in test_agents:
        exists = inventory.has_agent(name)
        status = "✓ exists" if exists else "✗ not found"
        print(f"{name}: {status}")

    print()
    print("=" * 70)
    print()

    # Example 4: Get agents by source
    print("Example 4: List agents by source")
    print("-" * 70)

    for source in ["custom", "template", "global"]:
        agents = inventory.get_by_source(source)
        print(f"\n{source.upper()} agents ({len(agents)}):")
        for agent in agents[:3]:  # Show first 3
            print(f"  • {agent.name}: {agent.description[:50]}...")
        if len(agents) > 3:
            print(f"  ... and {len(agents) - 3} more")

    print()
    print("=" * 70)
    print()

    # Example 5: Demonstrate priority resolution
    print("Example 5: Priority resolution (duplicates)")
    print("-" * 70)

    all_agents = inventory.all_agents()
    agent_names = {}

    for agent in all_agents:
        if agent.name not in agent_names:
            agent_names[agent.name] = []
        agent_names[agent.name].append(agent.source)

    duplicates = {name: sources for name, sources in agent_names.items() if len(sources) > 1}

    if duplicates:
        print("Agents found in multiple sources:")
        for name, sources in duplicates.items():
            highest_priority_agent = inventory.find_by_name(name)
            print(f"\n  {name}:")
            print(f"    Found in: {', '.join(sources)}")
            print(f"    Using: {highest_priority_agent.source} (priority {highest_priority_agent.priority})")
    else:
        print("No duplicate agents found")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
