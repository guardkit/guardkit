---
id: TASK-017
title: Update agentic-init Template Discovery
status: backlog
created: 2025-11-01T23:45:00Z
priority: high
complexity: 3
estimated_hours: 4
tags: [agentic-init, template-discovery, integration]
epic: EPIC-001
feature: template-usage
dependencies: [TASK-010, TASK-011]
blocks: []
---

# TASK-017: Update agentic-init Template Discovery

## Objective

Update `agentic-init` command to discover templates from both personal and repository locations, with personal templates taking precedence. This enables seamless integration with templates created by `/template-create` and `/template-init` commands.

**Key Principle**: Personal templates (user-created) override repository templates (built-in)

**Note**: Updated for TASK-068 which changed template creation to default to `~/.agentecflow/templates/` for personal use.

## Context

**From Template Lifecycle Review & TASK-068**:
- EPIC-001 adds two template creation commands
- TASK-068: Templates default to `~/.agentecflow/templates/` (personal, immediate use)
- Use `--output-location=repo` flag to create in `installer/global/templates/` (repository, distribution)
- Existing `agentic-init` only checks `installer/global/templates/`
- Need to discover both locations with proper priority

**Current Behavior**:
```python
# Only checks repository templates
def discover_templates():
    return scan_directory("installer/global/templates/")
```

**New Behavior**:
```python
# Check personal first, then repository
def discover_templates():
    personal = scan_directory("~/.agentecflow/templates/")  # Priority 1
    repo = scan_directory("installer/global/templates/")  # Priority 2
    return merge_with_priority(personal, repo)
```

## Acceptance Criteria

- [ ] Discover templates from `~/.agentecflow/templates/` (personal, user-created)
- [ ] Discover templates from `installer/global/templates/` (repository, built-in)
- [ ] Personal templates take precedence over repository templates (same name)
- [ ] Display template source during selection (personal vs repository)
- [ ] Handle missing directories gracefully (personal directory may not exist yet)
- [ ] Backward compatible (existing repository templates still work)
- [ ] Agent conflict detection (user's custom vs template agents)
- [ ] Unit tests for discovery logic
- [ ] Integration tests with both template sources

## Implementation

```python
# src/commands/agentic_init/template_discovery.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json

@dataclass
class TemplateInfo:
    """Template information"""
    name: str
    version: str
    source: str  # "personal" or "repository"
    source_path: Path
    description: str
    language: str
    frameworks: List[str]
    architecture: str

class TemplateDiscovery:
    """Discover templates from personal and repository sources"""

    def __init__(
        self,
        personal_path: Path = None,
        repo_path: Path = None
    ):
        """
        Initialize template discovery

        Args:
            personal_path: Path to personal templates (default: ~/.agentecflow/templates)
            repo_path: Path to repository templates (default: installer/global/templates)
        """
        self.personal_path = personal_path or Path.home() / ".agentecflow/templates"
        self.repo_path = repo_path or Path("installer/global/templates")

    def discover(self) -> List[TemplateInfo]:
        """
        Discover all available templates

        Returns:
            List of templates (personal first, then repository)
        """
        print("📦 Discovering templates...")

        templates = []

        # 1. Discover personal templates (PRIORITY)
        personal_templates = self._scan_directory(self.personal_path, source="personal")
        if personal_templates:
            print(f"  ✓ Found {len(personal_templates)} personal template(s)")
            templates.extend(personal_templates)

        # 2. Discover repository templates
        repo_templates = self._scan_directory(self.repo_path, source="repository")
        if repo_templates:
            print(f"  ✓ Found {len(repo_templates)} repository template(s)")

        # 3. Merge with priority (personal overrides repository)
        templates.extend(self._filter_duplicates(repo_templates, templates))

        if not templates:
            print("  ⚠️  No templates found")
            return []

        print(f"\n📊 Total: {len(templates)} available template(s)")

        return templates

    def _scan_directory(
        self,
        directory: Path,
        source: str
    ) -> List[TemplateInfo]:
        """
        Scan directory for templates

        Args:
            directory: Directory to scan
            source: "personal" or "repository"

        Returns:
            List of discovered templates
        """
        if not directory.exists():
            return []

        templates = []

        # Each subdirectory is a template
        for template_dir in directory.iterdir():
            if not template_dir.is_dir():
                continue

            # Check for manifest.json
            manifest_file = template_dir / "manifest.json"
            if not manifest_file.exists():
                continue

            try:
                # Parse manifest
                template = self._parse_manifest(manifest_file, source)
                if template:
                    templates.append(template)
            except Exception as e:
                print(f"  ⚠️  Failed to parse {template_dir.name}: {e}")
                continue

        return templates

    def _parse_manifest(
        self,
        manifest_file: Path,
        source: str
    ) -> Optional[TemplateInfo]:
        """
        Parse template manifest.json

        Args:
            manifest_file: Path to manifest.json
            source: "personal" or "repository"

        Returns:
            TemplateInfo if valid, None otherwise
        """
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)

        # Required fields
        name = manifest.get("name")
        version = manifest.get("version", "1.0.0")

        if not name:
            return None

        # Optional fields
        description = manifest.get("description", "")
        language = manifest.get("language", "")
        frameworks = manifest.get("frameworks", [])
        architecture = manifest.get("architecture", "")

        return TemplateInfo(
            name=name,
            version=version,
            source=source,
            source_path=manifest_file.parent,
            description=description,
            language=language,
            frameworks=frameworks,
            architecture=architecture
        )

    def _filter_duplicates(
        self,
        repo_templates: List[TemplateInfo],
        personal_templates: List[TemplateInfo]
    ) -> List[TemplateInfo]:
        """
        Filter repository templates that are overridden by personal templates

        Args:
            repo_templates: Templates from repository directory
            personal_templates: Templates from personal directory (priority)

        Returns:
            Repository templates not overridden by personal
        """
        personal_names = {t.name for t in personal_templates}

        filtered = []
        for template in repo_templates:
            if template.name in personal_names:
                print(f"  ℹ️  Skipping repository '{template.name}' (personal version exists)")
            else:
                filtered.append(template)

        return filtered

    def find_by_name(self, templates: List[TemplateInfo], name: str) -> Optional[TemplateInfo]:
        """
        Find template by name

        Args:
            templates: List of templates
            name: Template name to find

        Returns:
            TemplateInfo if found, None otherwise
        """
        for template in templates:
            if template.name == name:
                return template
        return None

def discover_templates() -> List[TemplateInfo]:
    """
    Convenience function to discover templates

    Returns:
        List of available templates
    """
    discovery = TemplateDiscovery()
    return discovery.discover()
```

## Template Selection UI

```python
# src/commands/agentic_init/template_selection.py

def select_template(templates: List[TemplateInfo]) -> Optional[TemplateInfo]:
    """
    Interactive template selection

    Args:
        templates: Available templates

    Returns:
        Selected template or None if cancelled
    """
    if not templates:
        print("\n❌ No templates available")
        print("\n💡 Tip: Create templates with:")
        print("   • /template-create <name>  (from existing codebase)")
        print("   • /template-init           (from scratch)")
        return None

    print("\n📋 Available Templates:")
    print("="*60)

    # Group by source
    personal_templates = [t for t in templates if t.source == "personal"]
    repo_templates = [t for t in templates if t.source == "repository"]

    # Display personal templates first
    if personal_templates:
        print("\n👤 Personal Templates:")
        for i, template in enumerate(personal_templates, 1):
            print(f"\n  [{i}] {template.name} (v{template.version})")
            if template.description:
                print(f"      {template.description}")
            if template.language:
                tech = f"{template.language}"
                if template.frameworks:
                    tech += f" + {', '.join(template.frameworks)}"
                print(f"      {tech}")
            if template.architecture:
                print(f"      Architecture: {template.architecture}")

    # Display repository templates
    if repo_templates:
        print("\n📦 Repository Templates (Built-in):")
        start_idx = len(personal_templates) + 1
        for i, template in enumerate(repo_templates, start_idx):
            print(f"\n  [{i}] {template.name} (v{template.version})")
            if template.description:
                print(f"      {template.description}")
            if template.language:
                tech = f"{template.language}"
                if template.frameworks:
                    tech += f" + {', '.join(template.frameworks)}"
                print(f"      {tech}")

    print("\n" + "="*60)

    # Get user selection
    choice = input("\nSelect template (number or name) [or 'q' to quit]: ")

    if choice.lower() == 'q':
        return None

    # Try as number
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(templates):
            return templates[idx]
    except ValueError:
        pass

    # Try as name
    for template in templates:
        if template.name.lower() == choice.lower():
            return template

    print(f"\n❌ Invalid selection: {choice}")
    return select_template(templates)  # Retry
```

## Agent Conflict Detection

```python
# src/commands/agentic_init/agent_installer.py

def install_template_agents(
    template: TemplateInfo,
    project_path: Path
) -> None:
    """
    Install agents from template to project

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
            agent_name = agent_file.stem

            print(f"\n  ⚠️  Agent '{agent_name}' already exists")
            print(f"      Your version: {dst_file}")
            print(f"      Template version: {agent_file}")

            choice = input(
                f"      [a] Keep your version (recommended)\n"
                f"      [b] Use template version\n"
                f"      [c] Keep both (rename template version)\n"
                f"      Choice [a/b/c]: "
            )

            if choice.lower() == 'b':
                # Replace with template version
                shutil.copy(agent_file, dst_file)
                print(f"      ✓ Using template version")
            elif choice.lower() == 'c':
                # Keep both, rename template version
                dst_file_renamed = agents_dst / f"{agent_name}-template.md"
                shutil.copy(agent_file, dst_file_renamed)
                print(f"      ✓ Saved as {dst_file_renamed.name}")
            else:
                # Keep user's version (default)
                print(f"      ✓ Keeping your version")

        else:
            # No conflict, copy
            shutil.copy(agent_file, dst_file)
            print(f"  ✓ Installed: {agent_file.name}")

    # Count total agents
    agent_count = len(list(agents_dst.glob("*.md")))
    print(f"\n✅ Total agents: {agent_count}")
```

## Integration with Existing agentic-init

```python
# src/commands/agentic_init/command.py

def agentic_init(template_name: Optional[str] = None):
    """
    Initialize project with template

    Args:
        template_name: Template name (if not provided, show selection UI)
    """
    # Step 1: Discover templates (UPDATED)
    templates = discover_templates()

    if not templates:
        print("\n❌ No templates found")
        return

    # Step 2: Select template
    if template_name:
        # Use specified template
        template = find_by_name(templates, template_name)
        if not template:
            print(f"\n❌ Template '{template_name}' not found")
            print(f"\n💡 Available templates:")
            for t in templates:
                print(f"   • {t.name} ({t.source})")
            return
    else:
        # Interactive selection
        template = select_template(templates)
        if not template:
            return

    # Step 3: Display template info
    print(f"\n📋 Template: {template.name}")
    print(f"   Version: {template.version}")
    print(f"   Source: {template.source} ({'~/.agentecflow/templates/' if template.source == 'personal' else 'installer/global/templates/'})")
    if template.language:
        print(f"   Language: {template.language}")
    if template.architecture:
        print(f"   Architecture: {template.architecture}")

    # Step 4-6: Load, apply, initialize (EXISTING CODE)
    # ... existing implementation continues ...
```

## Usage Examples

### Example 1: Discover Both Sources

```bash
$ agentic-init

📦 Discovering templates...
  ✓ Found 2 personal template(s)
  ✓ Found 5 repository template(s)

📊 Total: 7 available template(s)

📋 Available Templates:
============================================================

👤 Personal Templates:

  [1] mycompany-maui (v1.0.0)
      Company standard MAUI + MVVM template
      C# + .NET MAUI 8.0
      Architecture: MVVM + AppShell

  [2] team-backend (v2.1.0)
      Team backend microservice template
      C# + ASP.NET Core 8.0
      Architecture: Clean Architecture

📦 Repository Templates (Built-in):

  [3] react (v1.0.0)
      React + TypeScript + Vite template

  [4] python (v1.0.0)
      Python + FastAPI template

  [5] maui-appshell (v1.0.0)
      .NET MAUI with AppShell navigation

  [6] maui-navigationpage (v1.0.0)
      .NET MAUI with NavigationPage

  [7] dotnet-microservice (v1.0.0)
      .NET microservice template

============================================================

Select template (number or name) [or 'q' to quit]: 1

📋 Template: mycompany-maui
   Version: 1.0.0
   Source: personal (~/.agentecflow/templates/)
   Language: C#
   Architecture: MVVM + AppShell

✅ Project initialized successfully!
```

### Example 2: Personal Overrides Repository

```bash
$ agentic-init

📦 Discovering templates...
  ✓ Found 1 personal template(s)
  ✓ Found 5 repository template(s)
  ℹ️  Skipping repository 'react' (personal version exists)

📊 Total: 5 available template(s)

# User's personal 'react' template takes precedence over repository
```

### Example 3: Specify Template Name

```bash
$ agentic-init mycompany-maui

📦 Discovering templates...
  ✓ Found 2 personal template(s)
  ✓ Found 5 repository template(s)

📋 Template: mycompany-maui
   Version: 1.0.0
   Source: personal (~/.agentecflow/templates/)

✅ Initialized with mycompany-maui template
```

### Example 4: Agent Conflict Handling

```bash
$ agentic-init mycompany-maui

# ... template selection ...

🤖 Installing agents...
  ✓ Installed: architectural-reviewer.md
  ✓ Installed: code-reviewer.md

  ⚠️  Agent 'react-specialist' already exists
      Your version: .claude/agents/react-specialist.md
      Template version: template/agents/react-specialist.md
      [a] Keep your version (recommended)
      [b] Use template version
      [c] Keep both (rename template version)
      Choice [a/b/c]: a
      ✓ Keeping your version

  ✓ Installed: maui-appshell-navigator.md

✅ Total agents: 18
```

## Testing Strategy

```python
# tests/test_agentic_init_discovery.py

def test_discover_personal_templates():
    """Test discovery of personal templates"""
    # Create test personal templates
    personal_dir = Path("tests/fixtures/personal-templates")
    personal_dir.mkdir(parents=True, exist_ok=True)

    # Create test template
    test_template = personal_dir / "test-template"
    test_template.mkdir(exist_ok=True)

    manifest = test_template / "manifest.json"
    manifest.write_text(json.dumps({
        "name": "test-template",
        "version": "1.0.0"
    }))

    # Discover
    discovery = TemplateDiscovery(personal_path=personal_dir, repo_path=Path("/nonexistent"))
    templates = discovery.discover()

    assert len(templates) == 1
    assert templates[0].name == "test-template"
    assert templates[0].source == "personal"

def test_personal_overrides_repository():
    """Test that personal templates override repository templates"""
    # Create personal and repository with same name
    # ... setup fixtures

    discovery = TemplateDiscovery(personal_path=personal_dir, repo_path=repo_dir)
    templates = discovery.discover()

    # Should only have one "react" (personal version)
    react_templates = [t for t in templates if t.name == "react"]
    assert len(react_templates) == 1
    assert react_templates[0].source == "personal"

def test_missing_directories():
    """Test graceful handling of missing directories"""
    discovery = TemplateDiscovery(
        personal_path=Path("/nonexistent"),
        repo_path=Path("/nonexistent")
    )

    # Should not crash
    templates = discovery.discover()
    assert len(templates) == 0

def test_agent_conflict_detection():
    """Test agent conflict detection during installation"""
    # Create project with existing agent
    project_path = Path("tests/fixtures/test-project")
    agents_dir = project_path / ".claude/agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    existing_agent = agents_dir / "react-specialist.md"
    existing_agent.write_text("# Existing agent")

    # Create template with same agent
    # ... setup template

    # Mock user input (keep existing)
    with patch('builtins.input', return_value='a'):
        install_template_agents(template, project_path)

        # Existing agent should be preserved
        assert existing_agent.exists()
        assert existing_agent.read_text() == "# Existing agent"
```

## Definition of Done

- [ ] Template discovery from personal and repository directories
- [ ] Personal templates take precedence over repository templates
- [ ] Source indication (personal vs repository) in UI
- [ ] Missing directory handling (graceful)
- [ ] Agent conflict detection and resolution
- [ ] Backward compatible (existing templates work)
- [ ] Template selection UI updated
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration tests with both sources
- [ ] Documentation updated

**Estimated Time**: 4 hours | **Complexity**: 3/10 | **Priority**: HIGH

## Benefits

- ✅ Enables use of `/template-create` and `/template-init` templates
- ✅ Personal templates override repository templates (user control)
- ✅ Agent conflict resolution (respects user's custom)
- ✅ Backward compatible (existing flow unchanged)
- ✅ Clear UX (shows source: personal vs repository)
- ✅ Aligns with TASK-068 two-location model (personal + repository)

---

**Created**: 2025-11-01
**Updated**: 2025-01-08 (aligned with TASK-068)
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Dependencies**: TASK-010 (template-create), TASK-011 (template-init), TASK-068 (template location refactor - COMPLETED)
**Integration**: Minimal changes to existing agentic-init
**Risk**: LOW (small, focused change)

## TASK-068 Alignment Notes

This task has been updated to reflect the TASK-068 implementation:
- **Personal templates**: `~/.agentecflow/templates/` (default, immediate use)
- **Repository templates**: `installer/global/templates/` (distribution, requires install.sh)
- All references to `installer/local/templates/` have been updated to `~/.agentecflow/templates/`
- Terminology updated from "local/global" to "personal/repository" for clarity
