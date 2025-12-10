"""Agent installation with conflict detection for agentic-init command.

This module handles the installation of agents from templates to projects,
with intelligent conflict detection and resolution for existing custom agents.

Enhanced with agent discovery verification (TASK-ENF-P0-3):
- Verify agent metadata after copy
- Test discovery to ensure agents are findable
- Report registered agents to user
- Handle missing metadata gracefully
"""

from pathlib import Path
import shutil
import logging
from typing import Optional, List, Dict, Any
from .template_discovery import TemplateInfo

# Import agent discovery for verification
try:
    from ..agent_discovery import (
        _extract_metadata,
        validate_discovery_metadata,
        discover_agents
    )
    HAS_AGENT_DISCOVERY = True
except ImportError:
    HAS_AGENT_DISCOVERY = False

logger = logging.getLogger(__name__)


def install_template_agents(
    template: TemplateInfo,
    project_path: Path
) -> None:
    """
    Install agents from template to project.

    Enhanced with discovery verification (TASK-ENF-P0-3):
    - Verifies agent metadata after copy
    - Tests discovery to ensure agents are findable
    - Reports registered agents to user
    - Handles missing metadata gracefully

    Args:
        template: Selected template
        project_path: Project root path
    """
    agents_src = template.source_path / "agents"
    agents_dst = project_path / ".claude/agents"

    if not agents_src.exists():
        print("  ℹ️  Template has no agents")
        return

    # Ensure destination exists
    agents_dst.mkdir(parents=True, exist_ok=True)

    print("\n🤖 Installing agents...")

    # Copy agents with conflict detection
    copied_agents = []
    for agent_file in agents_src.glob("*.md"):
        dst_file = agents_dst / agent_file.name

        if dst_file.exists():
            # Conflict: User already has this agent
            _handle_agent_conflict(agent_file, dst_file)
            # Track as copied if user chose template version or both
            copied_agents.append(dst_file)
        else:
            # No conflict, copy
            shutil.copy(agent_file, dst_file)
            print(f"  ✓ Installed: {agent_file.name}")
            copied_agents.append(dst_file)

    # Count total agents
    agent_count = len(list(agents_dst.glob("*.md")))
    print(f"\n✅ Total agents: {agent_count}")

    # TASK-ENF-P0-3: Verify agent metadata
    if HAS_AGENT_DISCOVERY and copied_agents:
        _verify_agent_metadata(copied_agents)
        _test_agent_discovery(template, project_path)
        _report_registered_agents(copied_agents)


def _handle_agent_conflict(
    template_agent: Path,
    existing_agent: Path
) -> None:
    """
    Handle conflict when agent already exists.

    Args:
        template_agent: Agent from template
        existing_agent: Existing agent in project
    """
    agent_name = template_agent.stem

    print(f"\n  ⚠️  Agent '{agent_name}' already exists")
    print(f"      Your version: {existing_agent}")
    print(f"      Template version: {template_agent}")

    choice = input(
        f"      [a] Keep your version (recommended)\n"
        f"      [b] Use template version\n"
        f"      [c] Keep both (rename template version)\n"
        f"      Choice [a/b/c]: "
    )

    if choice.lower() == 'b':
        # Replace with template version
        shutil.copy(template_agent, existing_agent)
        print(f"      ✓ Using template version")
    elif choice.lower() == 'c':
        # Keep both, rename template version
        agents_dir = existing_agent.parent
        dst_file_renamed = agents_dir / f"{agent_name}-template.md"
        shutil.copy(template_agent, dst_file_renamed)
        print(f"      ✓ Saved as {dst_file_renamed.name}")
    else:
        # Keep user's version (default)
        print(f"      ✓ Keeping your version")


def list_template_agents(template: TemplateInfo) -> Optional[list]:
    """
    List all agents in a template.

    Args:
        template: Template to inspect

    Returns:
        List of agent file names, or None if no agents
    """
    agents_dir = template.source_path / "agents"

    if not agents_dir.exists():
        return None

    agent_files = list(agents_dir.glob("*.md"))
    return [f.name for f in agent_files]


def verify_agent_integrity(agent_file: Path) -> bool:
    """
    Verify that an agent file is valid.

    Args:
        agent_file: Path to agent markdown file

    Returns:
        True if valid, False otherwise
    """
    if not agent_file.exists():
        return False

    if not agent_file.suffix == ".md":
        return False

    # Check file is not empty
    try:
        content = agent_file.read_text()
        return len(content.strip()) > 0
    except Exception:
        return False


def _verify_agent_metadata(agent_files: List[Path]) -> None:
    """
    Verify agents have required discovery metadata (TASK-ENF-P0-3: FR1).

    Checks each agent's frontmatter for required fields:
    - stack: List of supported stacks
    - phase: Workflow phase (implementation/review/testing/orchestration)
    - capabilities: List of capabilities
    - keywords: List of keywords

    Warns if metadata missing but doesn't block initialization.

    Args:
        agent_files: List of agent file paths to verify
    """
    print("\n" + "=" * 60)
    print("  Agent Discovery Verification")
    print("=" * 60 + "\n")

    print("🔍 Verifying agent metadata...")

    missing_metadata = []

    for agent_file in agent_files:
        # Extract metadata
        metadata = _extract_metadata(agent_file, source="local", priority=1)

        if metadata is None:
            print(f"  ⚠️  Warning: Could not read {agent_file.name}")
            continue

        # Validate metadata
        is_valid, errors = validate_discovery_metadata(metadata)

        if not is_valid:
            agent_name = agent_file.stem
            print(f"  ⚠️  Warning: {agent_name} missing discovery metadata:")
            for error in errors:
                print(f"      - {error}")
            missing_metadata.append((agent_name, agent_file))
        else:
            print(f"  ✓ {agent_file.stem}: Valid metadata")

    if missing_metadata:
        print(f"\n⚠️  {len(missing_metadata)} agent(s) missing discovery metadata")
        print("\n💡 Tip: Enhance agents with:")
        for agent_name, agent_file in missing_metadata:
            print(f"   /agent-enhance {agent_file}")
    else:
        print(f"\n✅ All agents have valid discovery metadata")


def _test_agent_discovery(template: TemplateInfo, project_path: Path) -> None:
    """
    Test agent discovery after initialization (TASK-ENF-P0-3: FR2).

    Runs a discovery test to verify that template agents are findable
    by the discovery system. This ensures agents will be available for
    task execution.

    Logs success/warning/error but doesn't block initialization.

    Args:
        template: Template being installed
        project_path: Project root path
    """
    print("\n🧪 Testing agent discovery...")

    try:
        # Try to discover implementation agents
        # Note: We need to be in the project directory for discovery to work
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(project_path)

            # Try discovery for implementation phase
            discovered = discover_agents(phase="implementation")

            if discovered:
                # Find local agents (source='local')
                local_agents = [a for a in discovered if a.get('source') == 'local']

                if local_agents:
                    print(f"  ✅ Agent discovery successful:")
                    for agent in local_agents[:3]:  # Show first 3
                        agent_name = agent.get('name', 'unknown')
                        agent_stack = agent.get('stack', [])
                        print(f"      • {agent_name} (stack: {agent_stack})")
                    if len(local_agents) > 3:
                        print(f"      ... and {len(local_agents) - 3} more")
                else:
                    print(f"  ⚠️  No local agents discovered (will use global/user agents)")
            else:
                print(f"  ⚠️  No agents discovered (will use task-manager fallback)")

        finally:
            os.chdir(original_cwd)

    except Exception as e:
        print(f"  ⚠️  Agent discovery test failed: {e}")
        logger.debug(f"Discovery test exception: {e}", exc_info=True)


def _report_registered_agents(agent_files: List[Path]) -> None:
    """
    Report registered agents to user (TASK-ENF-P0-3: FR3).

    Displays a formatted table of registered agents with their
    stack and phase information.

    Args:
        agent_files: List of agent file paths
    """
    print("\n" + "=" * 60)
    print("  Registered Agents")
    print("=" * 60 + "\n")

    agents_with_metadata = []

    for agent_file in agent_files:
        metadata = _extract_metadata(agent_file, source="local", priority=1)
        if metadata:
            agent_name = metadata.get('name', agent_file.stem)
            stack = metadata.get('stack', ['unknown'])
            phase = metadata.get('phase', 'unknown')

            # Format stack list
            if isinstance(stack, list):
                stack_str = ', '.join(str(s) for s in stack)
            else:
                stack_str = str(stack)

            agents_with_metadata.append({
                'name': agent_name,
                'stack': stack_str,
                'phase': phase
            })

    if agents_with_metadata:
        for agent in agents_with_metadata:
            print(f"  • {agent['name']}")
            print(f"    Stack: {agent['stack']}, Phase: {agent['phase']}")
        print()
    else:
        print("  (No agents with metadata found)")
        print()
