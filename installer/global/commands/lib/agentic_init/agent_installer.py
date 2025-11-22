"""Agent installation with conflict detection for agentic-init command.

This module handles the installation of agents from templates to projects,
with intelligent conflict detection and resolution for existing custom agents.
"""

from pathlib import Path
import shutil
from typing import Optional
from .template_discovery import TemplateInfo


def install_template_agents(
    template: TemplateInfo,
    project_path: Path
) -> None:
    """
    Install agents from template to project.

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
    for agent_file in agents_src.glob("*.md"):
        dst_file = agents_dst / agent_file.name

        if dst_file.exists():
            # Conflict: User already has this agent
            _handle_agent_conflict(agent_file, dst_file)
        else:
            # No conflict, copy
            shutil.copy(agent_file, dst_file)
            print(f"  ✓ Installed: {agent_file.name}")

    # Count total agents
    agent_count = len(list(agents_dst.glob("*.md")))
    print(f"\n✅ Total agents: {agent_count}")


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
