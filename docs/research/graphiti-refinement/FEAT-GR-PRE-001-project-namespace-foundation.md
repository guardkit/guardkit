# FEAT-GR-PRE-001: Project Namespace Foundation

> **Purpose**: Establish project-specific namespacing in Graphiti to isolate project knowledge from system knowledge.
>
> **Priority**: High (Prerequisite)
> **Estimated Complexity**: 4
> **Dependencies**: None (foundational)
> **Blocks**: FEAT-GR-001, FEAT-GR-002

---

## Problem Statement

Currently, all Graphiti episodes go into a shared namespace. This causes issues:

1. **No project isolation** - Knowledge from project A mixes with project B
2. **System vs project confusion** - GuardKit system knowledge (how commands work) mixes with project knowledge (what this project does)
3. **Query pollution** - Searching for "authentication" returns results from all projects

The new features (FEAT-GR-001 through FEAT-GR-006) require clear separation between:
- **System knowledge** - GuardKit-wide (shared across all projects)
- **Project knowledge** - Project-specific (isolated per project)

---

## Proposed Solution

### 1. Project ID Detection

```python
# guardkit/knowledge/project_namespace.py

from pathlib import Path
from typing import Optional
import hashlib


def get_project_id(project_root: Optional[Path] = None) -> str:
    """Get unique project ID for namespace isolation.
    
    Resolution order:
    1. .guardkit/graphiti.yaml project_id setting
    2. Directory name
    
    Args:
        project_root: Project root directory. Defaults to cwd.
        
    Returns:
        Project ID string (e.g., "youtube-mcp", "guardkit")
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # 1. Check config file
    config_path = project_root / ".guardkit" / "graphiti.yaml"
    if config_path.exists():
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        if config.get("project_id"):
            return config["project_id"]
    
    # 2. Use directory name (sanitized)
    dir_name = project_root.name
    # Sanitize: lowercase, replace spaces/special chars with hyphens
    project_id = dir_name.lower().replace(" ", "-").replace("_", "-")
    
    return project_id


def get_project_group_id(base_group: str, project_id: Optional[str] = None) -> str:
    """Get project-namespaced group ID.
    
    Args:
        base_group: Base group name (e.g., "feature_specs")
        project_id: Optional project ID. Auto-detected if not provided.
        
    Returns:
        Namespaced group ID (e.g., "youtube-mcp__feature_specs")
    """
    if project_id is None:
        project_id = get_project_id()
    
    return f"{project_id}__{base_group}"


def is_system_group(group_id: str) -> bool:
    """Check if a group ID is a system (non-project) group.
    
    System groups don't have the project namespace prefix.
    
    Args:
        group_id: Group ID to check
        
    Returns:
        True if system group, False if project-specific
    """
    # System groups from seeding.py
    SYSTEM_GROUPS = {
        "product_knowledge",
        "command_workflows", 
        "quality_gate_phases",
        "technology_stack",
        "feature_build_architecture",
        "architecture_decisions",
        "failure_patterns",
        "component_status",
        "integration_points",
        "templates",
        "agents",
        "patterns",
        "rules",
        "failed_approaches",
        "quality_gate_configs",
        "feature_overviews",
        "role_constraints",
    }
    
    return group_id in SYSTEM_GROUPS
```

### 2. Project-Specific Group IDs

Define the project knowledge group taxonomy:

```python
# guardkit/knowledge/project_groups.py

from enum import Enum
from typing import List


class ProjectGroupID(str, Enum):
    """Project-specific group IDs for knowledge organization."""
    
    # Core project knowledge
    PROJECT_OVERVIEW = "project_overview"        # What the project is, goals, constraints
    PROJECT_ARCHITECTURE = "project_architecture"  # System architecture
    PROJECT_DECISIONS = "project_decisions"       # Project-specific ADRs
    PROJECT_CONSTRAINTS = "project_constraints"   # Technical/business constraints
    
    # Feature and domain knowledge
    FEATURE_SPECS = "feature_specs"              # Feature specifications
    DOMAIN_KNOWLEDGE = "domain_knowledge"        # Domain terminology, concepts
    
    # Implementation artifacts
    IMPLEMENTATION_GUIDES = "implementation_guides"  # How-to docs
    CODE_PATTERNS = "code_patterns"              # Project-specific patterns
    
    @classmethod
    def all_groups(cls) -> List[str]:
        """Get all project group IDs as strings."""
        return [g.value for g in cls]
```

### 3. Configuration Extension

Extend `.guardkit/graphiti.yaml` to support project configuration:

```yaml
# .guardkit/graphiti.yaml

# Connection settings (existing)
enabled: true
neo4j_uri: bolt://localhost:7687
neo4j_user: neo4j
neo4j_password: password123
timeout: 30.0

# NEW: Project namespace settings
project:
  # Optional: Override auto-detected project ID
  id: youtube-mcp
  
  # Optional: Project display name
  name: "YouTube MCP Server"
  
  # Optional: Enable/disable project knowledge features
  knowledge_enabled: true
```

### 4. GraphitiClient Extension

Add project awareness to the client:

```python
# Additions to guardkit/knowledge/graphiti_client.py

class GraphitiClient:
    """Extended with project namespace support."""
    
    def __init__(
        self,
        config: Optional[GraphitiConfig] = None,
        project_id: Optional[str] = None
    ):
        self.config = config or GraphitiConfig()
        self._project_id = project_id
        # ... existing initialization
    
    @property
    def project_id(self) -> Optional[str]:
        """Get the project ID for namespacing."""
        if self._project_id:
            return self._project_id
        return get_project_id()
    
    def get_project_group_id(self, base_group: str) -> str:
        """Get namespaced group ID for project knowledge.
        
        Args:
            base_group: Base group name (e.g., "feature_specs")
            
        Returns:
            Namespaced group ID (e.g., "youtube-mcp__feature_specs")
        """
        return f"{self.project_id}__{base_group}"
    
    async def add_project_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str
    ) -> Optional[str]:
        """Add episode to project-namespaced group.
        
        Automatically prefixes group_id with project namespace.
        
        Args:
            name: Episode name
            episode_body: Episode content (JSON string or dict)
            group_id: Base group ID (will be namespaced)
            
        Returns:
            Episode UUID if successful, None otherwise
        """
        namespaced_group = self.get_project_group_id(group_id)
        return await self.add_episode(name, episode_body, namespaced_group)
    
    async def search_project(
        self,
        query: str,
        group_ids: Optional[List[str]] = None,
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search within project-namespaced groups.
        
        Automatically prefixes group_ids with project namespace.
        
        Args:
            query: Search query
            group_ids: Base group IDs (will be namespaced)
            num_results: Maximum results
            
        Returns:
            Search results
        """
        if group_ids:
            namespaced_groups = [
                self.get_project_group_id(g) for g in group_ids
            ]
        else:
            # Default: all project groups
            namespaced_groups = [
                self.get_project_group_id(g) 
                for g in ProjectGroupID.all_groups()
            ]
        
        return await self.search(query, namespaced_groups, num_results)
    
    async def search_all(
        self,
        query: str,
        include_system: bool = True,
        include_project: bool = True,
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search across system and/or project knowledge.
        
        Args:
            query: Search query
            include_system: Include system knowledge groups
            include_project: Include project knowledge groups
            num_results: Maximum results
            
        Returns:
            Combined search results
        """
        groups = []
        
        if include_system:
            groups.extend(SYSTEM_GROUPS)
        
        if include_project:
            groups.extend([
                self.get_project_group_id(g) 
                for g in ProjectGroupID.all_groups()
            ])
        
        return await self.search(query, groups, num_results)
```

### 5. Project Initialization

Add project initialization during `guardkit init`:

```python
# guardkit/knowledge/project_init.py

async def initialize_project_knowledge(
    client: GraphitiClient,
    project_name: str,
    template_id: Optional[str] = None
) -> bool:
    """Initialize project knowledge namespace in Graphiti.
    
    Creates a minimal project overview episode to establish the namespace.
    
    Args:
        client: GraphitiClient instance
        project_name: Project name
        template_id: Optional template used for initialization
        
    Returns:
        True if successful
    """
    from datetime import datetime, timezone
    import json
    
    if not client.enabled:
        return False
    
    # Create minimal project overview
    overview = {
        "entity_type": "project_overview",
        "project_name": project_name,
        "template_used": template_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "knowledge_completeness": "minimal",
        "purpose": "",  # To be filled by user
        "goals": [],
        "constraints": []
    }
    
    result = await client.add_project_episode(
        name=f"project_overview_{project_name}",
        episode_body=json.dumps(overview),
        group_id="project_overview"
    )
    
    return result is not None
```

---

## Success Criteria

1. **Project ID detected** - Can detect project ID from directory or config
2. **Group namespacing works** - `feature_specs` → `youtube-mcp__feature_specs`
3. **Search isolation** - Project search only returns project knowledge
4. **System knowledge unchanged** - Existing system seeding still works
5. **Configuration extended** - New project settings in graphiti.yaml

---

## Implementation Tasks

| Task ID | Description | Estimate |
|---------|-------------|----------|
| TASK-GR-PRE-001A | Create `project_namespace.py` with ID detection | 1.5h |
| TASK-GR-PRE-001B | Create `project_groups.py` with group taxonomy | 0.5h |
| TASK-GR-PRE-001C | Extend GraphitiSettings for project config | 1h |
| TASK-GR-PRE-001D | Add project methods to GraphitiClient | 2h |
| TASK-GR-PRE-001E | Add project initialization function | 1h |
| TASK-GR-PRE-001F | Add tests | 1.5h |
| TASK-GR-PRE-001G | Update documentation | 0.5h |

**Total Estimate**: 8 hours

---

## Usage Examples

### Detecting Project ID

```python
from guardkit.knowledge.project_namespace import get_project_id

# In /Users/rich/Projects/youtube-mcp/
project_id = get_project_id()
# Returns: "youtube-mcp"

# With custom config
# .guardkit/graphiti.yaml: project_id: my-custom-id
project_id = get_project_id()
# Returns: "my-custom-id"
```

### Adding Project Knowledge

```python
client = get_graphiti()

# Add to project-namespaced group
await client.add_project_episode(
    name="feat_skel_001",
    episode_body=json.dumps(feature_spec),
    group_id="feature_specs"  # Becomes: youtube-mcp__feature_specs
)
```

### Searching Project Knowledge

```python
# Search only project knowledge
results = await client.search_project(
    query="walking skeleton requirements",
    group_ids=["feature_specs"]
)

# Search both system and project knowledge
results = await client.search_all(
    query="MCP server patterns",
    include_system=True,
    include_project=True
)
```

---

## Migration Considerations

- **Backward compatible** - Existing system seeding continues to work
- **No data migration** - Project groups are new, no existing data to migrate
- **Opt-in** - Projects without `.guardkit/graphiti.yaml` project settings still work (uses directory name)
