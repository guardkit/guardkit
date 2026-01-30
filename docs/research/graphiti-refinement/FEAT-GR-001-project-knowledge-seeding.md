# FEAT-GR-001: Project Knowledge Seeding

> **Purpose**: Enable seeding of project-specific knowledge into Graphiti during project initialization and template application, including critical role constraints, quality gate configurations, and implementation modes from AutoBuild lessons learned.
>
> **Priority**: High
> **Estimated Complexity**: 6
> **Estimated Time**: 16 hours (revised from 13h based on TASK-REV-1505 review)
> **Dependencies**: FEAT-GR-PRE-000, FEAT-GR-PRE-001, FEAT-GR-PRE-002, FEAT-GR-PRE-003

---

## Problem Statement

Currently, when `guardkit init` runs with a template, only GuardKit system knowledge is available in Graphiti. There's no mechanism to seed:

1. **Project-specific context** - What this project is trying to achieve
2. **Project architecture** - How this specific project is structured
3. **Project constraints** - Technical/business limitations specific to this project
4. **Domain knowledge** - Terminology and concepts relevant to this project's domain

This means Claude Code sessions start without understanding the project they're working on, leading to generic responses that don't account for project-specific goals and constraints.

---

## Proposed Solution

Enhance `guardkit init` and add new seeding capabilities to populate project-specific knowledge:

### 1. Enhanced `guardkit init`

When running `guardkit init --template <template>`:

```bash
guardkit init --template fastmcp-python --project-name youtube-mcp
```

**New behavior:**
1. Existing: Installs template files
2. Existing: Seeds GuardKit system knowledge (if not already seeded)
3. **NEW**: Creates project namespace in Graphiti
4. **NEW**: Seeds project overview episode (placeholder for user to fill)
5. **NEW**: Seeds template-specific patterns for this project
6. **NEW**: Prompts user for basic project information (optional, can skip)

### 2. Project Overview Seeding

Create initial project knowledge episode:

```python
async def seed_project_overview(
    project_name: str,
    template_id: str,
    project_path: Path,
    user_provided: Optional[Dict] = None
):
    """Seed initial project overview into Graphiti."""
    
    # Extract what we can from existing files
    claude_md = parse_claude_md_if_exists(project_path / "CLAUDE.md")
    readme = parse_readme_if_exists(project_path / "README.md")
    
    episode_data = {
        "entity_type": "project_overview",
        "project_name": project_name,
        "template_used": template_id,
        "created_at": datetime.now().isoformat(),
        
        # From existing files (if available)
        "purpose": claude_md.get("purpose") or readme.get("description") or "",
        "architecture_summary": claude_md.get("architecture") or "",
        
        # From user input (if provided)
        "goals": user_provided.get("goals", []) if user_provided else [],
        "constraints": user_provided.get("constraints", []) if user_provided else [],
        "target_users": user_provided.get("target_users", []) if user_provided else [],
        
        # Metadata
        "knowledge_completeness": "minimal",  # minimal | partial | comprehensive
        "last_updated": datetime.now().isoformat()
    }
    
    await graphiti.add_episode(
        name=f"project_{project_name}_overview",
        episode_body=json.dumps(episode_data),
        group_id="project_overview"
    )
```

### 3. Optional Interactive Setup

If user doesn't skip, prompt for basic information:

```
$ guardkit init --template fastmcp-python --project-name youtube-mcp

✓ Template installed
✓ GuardKit system knowledge verified

Would you like to provide project context now? (recommended) [Y/n]: Y

What is the primary purpose of this project?
> MCP server for extracting insights from YouTube videos and podcasts

Who are the target users?
> Entrepreneurs and investors who want to consume content while walking/driving

What are the key constraints or requirements?
> Must work with Claude Desktop, focus on actionable insights, support focus areas

✓ Project knowledge seeded

Run 'guardkit graphiti add-context' to add more detailed documentation later.
```

---

## Technical Requirements

### New Group IDs

Add to Graphiti configuration:

```yaml
# config/graphiti.yaml
groups:
  # Existing system groups...

  # New project-specific groups (prefixed with project_id at runtime)
  project_overview: "project_overview"
  project_architecture: "project_architecture"
  project_decisions: "project_decisions"
  project_constraints: "project_constraints"
  feature_specs: "feature_specs"
  domain_knowledge: "domain_knowledge"

  # NEW: Critical entities from TASK-REV-1505 review (AutoBuild lessons)
  role_constraints: "role_constraints"          # Player/Coach role boundaries
  quality_gate_configs: "quality_gate_configs"  # Task-type specific thresholds
  implementation_modes: "implementation_modes"  # Direct vs task-work patterns
```

### Episode Schemas

#### Project Overview Episode

```python
@dataclass
class ProjectOverviewEpisode:
    """Project-level overview knowledge."""
    
    entity_type: str = "project_overview"
    project_name: str = ""
    template_used: str = ""
    
    # Core information
    purpose: str = ""
    description: str = ""
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    target_users: List[str] = field(default_factory=list)
    
    # Architecture summary
    architecture_summary: str = ""
    key_components: List[str] = field(default_factory=list)
    external_dependencies: List[str] = field(default_factory=list)
    
    # Domain context
    domain: str = ""  # e.g., "content-automation", "fintech", "healthcare"
    domain_terminology: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    knowledge_completeness: str = "minimal"  # minimal | partial | comprehensive
    created_at: str = ""
    last_updated: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

#### Project Architecture Episode

```python
@dataclass
class ProjectArchitectureEpisode:
    """Project-specific architecture knowledge."""

    entity_type: str = "project_architecture"
    project_name: str = ""

    # Structure
    architecture_style: str = ""  # e.g., "mcp-server", "api-backend", "fullstack"
    layers: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)

    # Components
    services: List[Dict[str, str]] = field(default_factory=list)  # [{name, purpose, location}]
    key_modules: List[Dict[str, str]] = field(default_factory=list)

    # Integration
    external_apis: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)

    # Patterns in use
    patterns_applied: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
```

#### Role Constraints Episode (NEW - from TASK-REV-1505)

```python
@dataclass
class RoleConstraintsEpisode:
    """Hard constraints for Player/Coach roles in feature-build.

    Addresses TASK-REV-7549 Finding: Player-Coach role reversal was a top-5
    recurring problem during AutoBuild development.
    """

    entity_type: str = "role_constraints"
    role: str = ""  # "player" | "coach"

    # What this role MUST do
    must_do: List[str] = field(default_factory=list)

    # What this role MUST NOT do
    must_not_do: List[str] = field(default_factory=list)

    # When to ask before proceeding
    ask_before: List[str] = field(default_factory=list)

    # When to escalate to human
    escalate_when: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Default role constraints to seed
DEFAULT_ROLE_CONSTRAINTS = [
    RoleConstraintsEpisode(
        role="player",
        must_do=[
            "Implement code to meet acceptance criteria",
            "Read and follow implementation plans",
            "Write tests for implemented functionality",
            "Report blockers with evidence",
        ],
        must_not_do=[
            "Validate quality gates (Coach's job)",
            "Make architectural decisions without ADR reference",
            "Modify quality profiles or thresholds",
            "Ask for human guidance mid-feature (autonomous mode)",
        ],
        ask_before=[
            "Changing architecture from implementation plan",
            "Modifying external dependencies",
            "Skipping acceptance criteria",
        ],
    ),
    RoleConstraintsEpisode(
        role="coach",
        must_do=[
            "Validate implementation against acceptance criteria",
            "Run quality gates (tests, coverage, architecture)",
            "Provide specific, actionable feedback",
            "Track acceptance criteria status",
        ],
        must_not_do=[
            "Write implementation code",
            "Modify the implementation directly",
            "Make implementation decisions",
            "Change acceptance criteria mid-task",
        ],
        escalate_when=[
            "Test failures persist after 3 attempts",
            "Architecture violations detected",
            "Acceptance criteria cannot be met as written",
        ],
    ),
]
```

#### Quality Gate Configuration Episode (NEW - from TASK-REV-1505)

```python
@dataclass
class QualityGateConfigEpisode:
    """Versioned quality gate thresholds by task type.

    Addresses TASK-REV-7549 Finding: Quality gate threshold drift caused
    unpredictable approval/rejection decisions during AutoBuild.
    """

    entity_type: str = "quality_gate_config"
    task_type: str = ""  # "scaffolding" | "feature" | "testing" | "documentation"
    complexity_range: Tuple[int, int] = (1, 10)  # (min, max) complexity this applies to

    # Architectural review settings
    arch_review_required: bool = True
    arch_review_threshold: int = 60  # Score needed to pass

    # Test coverage settings
    coverage_required: bool = True
    coverage_threshold: float = 0.80  # 80% coverage

    # Test pass settings
    tests_required: bool = True
    tests_must_pass: bool = True

    # Effective date (for versioning)
    effective_from: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Default quality gate configs to seed
DEFAULT_QUALITY_GATE_CONFIGS = [
    QualityGateConfigEpisode(
        task_type="scaffolding",
        complexity_range=(1, 10),
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0.0,
        tests_required=False,
        tests_must_pass=False,
        effective_from="2026-01-30",
    ),
    QualityGateConfigEpisode(
        task_type="feature",
        complexity_range=(1, 3),
        arch_review_required=True,
        arch_review_threshold=50,
        coverage_required=True,
        coverage_threshold=0.70,
        tests_required=True,
        tests_must_pass=True,
        effective_from="2026-01-30",
    ),
    QualityGateConfigEpisode(
        task_type="feature",
        complexity_range=(4, 6),
        arch_review_required=True,
        arch_review_threshold=60,
        coverage_required=True,
        coverage_threshold=0.80,
        tests_required=True,
        tests_must_pass=True,
        effective_from="2026-01-30",
    ),
    QualityGateConfigEpisode(
        task_type="feature",
        complexity_range=(7, 10),
        arch_review_required=True,
        arch_review_threshold=70,
        coverage_required=True,
        coverage_threshold=0.85,
        tests_required=True,
        tests_must_pass=True,
        effective_from="2026-01-30",
    ),
    QualityGateConfigEpisode(
        task_type="testing",
        complexity_range=(1, 10),
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=True,
        coverage_threshold=0.90,
        tests_required=True,
        tests_must_pass=True,
        effective_from="2026-01-30",
    ),
    QualityGateConfigEpisode(
        task_type="documentation",
        complexity_range=(1, 10),
        arch_review_required=False,
        arch_review_threshold=0,
        coverage_required=False,
        coverage_threshold=0.0,
        tests_required=False,
        tests_must_pass=False,
        effective_from="2026-01-30",
    ),
]
```

#### Implementation Mode Episode (NEW - from TASK-REV-1505)

```python
@dataclass
class ImplementationModeEpisode:
    """Patterns for different implementation modes.

    Addresses TASK-REV-7549 Finding: Direct mode vs task-work mode confusion
    caused file location errors during AutoBuild.
    """

    entity_type: str = "implementation_mode"
    mode: str = ""  # "direct" | "task-work"

    # How to invoke this mode
    invocation_method: str = ""  # "sdk_query" | "subprocess" | "inline"

    # Where results are stored
    result_location_pattern: str = ""  # Path pattern

    # State recovery strategy
    state_recovery_strategy: str = ""  # "git_check_first" | "retry_fresh" | "resume_from_checkpoint"

    # When to use this mode
    when_to_use: List[str] = field(default_factory=list)

    # Common pitfalls
    pitfalls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Default implementation modes to seed
DEFAULT_IMPLEMENTATION_MODES = [
    ImplementationModeEpisode(
        mode="direct",
        invocation_method="inline",
        result_location_pattern="{worktree_path}/",
        state_recovery_strategy="git_check_first",
        when_to_use=[
            "Simple file operations",
            "Configuration changes",
            "Documentation updates",
        ],
        pitfalls=[
            "Don't use for complex implementations",
            "Check git status before starting",
        ],
    ),
    ImplementationModeEpisode(
        mode="task-work",
        invocation_method="sdk_query",  # NOT subprocess!
        result_location_pattern=".guardkit/worktrees/{feature_id}/",
        state_recovery_strategy="resume_from_checkpoint",
        when_to_use=[
            "Feature implementations",
            "Tasks requiring quality gates",
            "Multi-file changes",
        ],
        pitfalls=[
            "MUST use SDK query(), NOT subprocess (ADR-FB-001)",
            "Paths use FEAT-XXX worktree ID, not TASK-XXX (ADR-FB-002)",
            "Implementation plan MUST exist before execution (ADR-FB-003)",
        ],
    ),
]
```

### File Parsing Utilities

```python
def parse_claude_md_if_exists(path: Path) -> Dict[str, str]:
    """Extract structured information from CLAUDE.md if it exists."""
    
    if not path.exists():
        return {}
    
    content = path.read_text()
    sections = {}
    
    # Parse markdown sections
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections[current_section.lower()] = '\n'.join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        elif current_section:
            current_content.append(line)
    
    if current_section:
        sections[current_section.lower()] = '\n'.join(current_content).strip()
    
    return sections


def parse_readme_if_exists(path: Path) -> Dict[str, str]:
    """Extract basic information from README.md if it exists."""
    
    if not path.exists():
        return {}
    
    content = path.read_text()
    
    # Extract description (first paragraph after title)
    lines = content.split('\n')
    description = ""
    in_description = False
    
    for line in lines:
        if line.startswith('# '):
            in_description = True
            continue
        if in_description:
            if line.strip() and not line.startswith('#'):
                description = line.strip()
                break
    
    return {"description": description}
```

---

## Success Criteria

1. **`guardkit init` creates project namespace** - New project gets isolated Graphiti space
2. **Project overview episode created** - Basic project information is seeded
3. **Existing files parsed** - CLAUDE.md and README.md content extracted where available
4. **Optional interactive setup** - User can provide context during init
5. **Skip option works** - Can skip interactive and seed later
6. **Knowledge queryable** - Can query project knowledge after init

---

## Implementation Tasks

| Task ID | Description | Estimate |
|---------|-------------|----------|
| TASK-GR-001A | Add project-specific and new group IDs to Graphiti config | 1h |
| TASK-GR-001B | Create ProjectOverviewEpisode and ProjectArchitectureEpisode schemas | 2h |
| TASK-GR-001C | Implement CLAUDE.md and README.md parsing utilities | 2h |
| TASK-GR-001D | Add project seeding to `guardkit init` command | 3h |
| TASK-GR-001E | Implement optional interactive setup flow | 2h |
| TASK-GR-001F | **NEW**: Create RoleConstraintsEpisode and seed defaults | 1h |
| TASK-GR-001G | **NEW**: Create QualityGateConfigEpisode and seed defaults | 2h |
| TASK-GR-001H | **NEW**: Create ImplementationModeEpisode and seed defaults | 1h |
| TASK-GR-001I | Add tests for project seeding (including new entities) | 2h |
| TASK-GR-001J | Update documentation | 1h |

**Total Estimate**: 16 hours (revised based on TASK-REV-1505 review)

### New Tasks Rationale (from TASK-REV-1505)

The following tasks were added based on the architectural review findings:

- **TASK-GR-001F (Role Constraints)**: Addresses TASK-REV-7549 top-5 problem of Player-Coach role reversal
- **TASK-GR-001G (Quality Gate Configs)**: Prevents quality gate threshold drift identified in AutoBuild lessons
- **TASK-GR-001H (Implementation Modes)**: Clarifies direct vs task-work mode patterns to prevent file location errors

---

## Testing Strategy

### Unit Tests

```python
def test_parse_claude_md():
    """Test CLAUDE.md parsing extracts sections correctly."""
    content = """# Project Name
    
## Purpose
This is the purpose.

## Architecture
Three-tier architecture.
"""
    result = parse_claude_md_content(content)
    assert result["purpose"] == "This is the purpose."
    assert result["architecture"] == "Three-tier architecture."


def test_project_overview_episode_creation():
    """Test project overview episode is created with correct structure."""
    episode = ProjectOverviewEpisode(
        project_name="test-project",
        template_used="fastmcp-python",
        purpose="Test purpose"
    )
    data = episode.to_dict()
    assert data["entity_type"] == "project_overview"
    assert data["project_name"] == "test-project"
```

### Integration Tests

```python
async def test_guardkit_init_seeds_project():
    """Test that guardkit init seeds project knowledge."""
    # Run init
    await run_guardkit_init(
        template="fastmcp-python",
        project_name="test-project",
        project_path=tmp_path
    )
    
    # Verify project knowledge exists
    results = await graphiti.search(
        query="project test-project overview",
        group_ids=["project_overview"]
    )
    assert len(results) > 0
    assert "test-project" in results[0]["fact"]
```

---

## Open Questions

1. **Namespace isolation**: Should project knowledge be in a separate Neo4j database, or use group_id prefixing within same database?
   - **Recommendation**: Start with group_id prefixing (simpler), migrate to separate databases later if needed

2. **CLAUDE.md sync**: Should changes to CLAUDE.md automatically update Graphiti?
   - **Recommendation**: No auto-sync initially. Use explicit `guardkit graphiti add-context` command.

3. **Template inheritance**: Should project inherit all template patterns, or just reference them?
   - **Recommendation**: Reference via group_id queries, don't duplicate episodes

---

## Future Enhancements

1. **Auto-detect project changes** - Watch for CLAUDE.md changes and prompt to update
2. **Project health score** - Track knowledge completeness and prompt to fill gaps
3. **Multi-project dashboards** - Compare knowledge across projects (for enterprise)
