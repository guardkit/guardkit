# FEAT-GR-003: Feature Spec Integration

> **Purpose**: Automatically seed feature specifications into Graphiti during `/feature-plan` execution, making feature context available for task generation and implementation.
>
> **Priority**: Medium
> **Estimated Complexity**: 4
> **Estimated Time**: 15 hours (revised from 13h based on TASK-REV-1505 review)
> **Dependencies**: FEAT-GR-002 (Context Addition Command)
> **Reviewed**: TASK-REV-1505 (2026-01-30)

---

## Problem Statement

When running `/feature-plan`, users often have detailed feature specifications in markdown files. Currently:

1. The feature spec content must be manually included in the prompt
2. Feature context is not available for subsequent `/feature-build` or `/task-work` commands
3. Related features and patterns are not automatically considered

This means valuable context is lost between planning and implementation phases.

---

## Proposed Solution

### Enhanced `/feature-plan` with Context Option

```bash
# Explicit context file
/feature-plan "implement FEAT-SKEL-001 walking skeleton" --context docs/features/FEAT-SKEL-001-walking-skeleton.md

# Auto-detect from feature ID
/feature-plan "implement FEAT-SKEL-001"  # Searches docs/features/ for matching spec

# Multiple context sources
/feature-plan "implement FEAT-SKEL-001" --context docs/features/FEAT-SKEL-001.md --context docs/CLAUDE.md
```

### Workflow Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        /feature-plan FEAT-XXX                           │
│                                                                         │
│  1. Detect/receive context file                                         │
│         ↓                                                               │
│  2. Parse and seed to Graphiti (via FEAT-GR-002 ingestor)              │
│         ↓                                                               │
│  3. Query Graphiti for enriched context:                               │
│     - Feature spec details                                              │
│     - Related features                                                  │
│     - Relevant patterns                                                 │
│     - Similar past implementations                                      │
│     - Role constraints (Player/Coach boundaries) [NEW]                 │
│     - Quality gate configs (task-type thresholds) [NEW]                │
│         ↓                                                               │
│  4. Inject context into planning prompt                                │
│         ↓                                                               │
│  5. Generate tasks with full context awareness                         │
│         ↓                                                               │
│  6. Capture planning decisions as episodes                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Requirements

### Feature ID Detection

```python
# guardkit/knowledge/feature_detector.py

import re
from pathlib import Path
from typing import Optional, List


class FeatureDetector:
    """Detects feature specs from IDs and descriptions."""
    
    FEATURE_ID_PATTERN = re.compile(r'FEAT-[A-Z0-9]+-\d+')
    DEFAULT_FEATURE_PATHS = [
        "docs/features",
        ".guardkit/features",
        "features"
    ]
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def detect_feature_id(self, description: str) -> Optional[str]:
        """Extract feature ID from description."""
        
        match = self.FEATURE_ID_PATTERN.search(description)
        return match.group(0) if match else None
    
    def find_feature_spec(self, feature_id: str) -> Optional[Path]:
        """Find feature spec file for given ID."""
        
        for search_path in self.DEFAULT_FEATURE_PATHS:
            feature_dir = self.project_root / search_path
            if not feature_dir.exists():
                continue
            
            # Look for files matching the feature ID
            for file_path in feature_dir.glob("*.md"):
                if feature_id in file_path.name:
                    return file_path
        
        return None
    
    def find_related_features(self, feature_id: str) -> List[Path]:
        """Find features that might be related (same prefix)."""
        
        # Extract prefix (e.g., FEAT-SKEL from FEAT-SKEL-001)
        parts = feature_id.split('-')
        if len(parts) >= 2:
            prefix = '-'.join(parts[:2])
        else:
            return []
        
        related = []
        for search_path in self.DEFAULT_FEATURE_PATHS:
            feature_dir = self.project_root / search_path
            if not feature_dir.exists():
                continue
            
            for file_path in feature_dir.glob(f"{prefix}*.md"):
                if feature_id not in file_path.name:  # Exclude self
                    related.append(file_path)
        
        return related
```

### Feature Plan Context Builder

```python
# guardkit/knowledge/feature_plan_context.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from .graphiti_client import get_graphiti
from .context_ingestor import ContextIngestor
from .feature_detector import FeatureDetector


@dataclass
class FeaturePlanContext:
    """Rich context for feature planning."""

    # Primary feature
    feature_spec: Dict[str, Any]

    # Enrichment from Graphiti
    related_features: List[Dict[str, Any]]
    relevant_patterns: List[Dict[str, Any]]
    similar_implementations: List[Dict[str, Any]]
    project_architecture: Dict[str, Any]
    warnings: List[Dict[str, Any]]

    # AutoBuild support context (NEW - from TASK-REV-1505)
    role_constraints: List[Dict[str, Any]] = field(default_factory=list)
    quality_gate_configs: List[Dict[str, Any]] = field(default_factory=list)
    implementation_modes: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_prompt_context(self, budget_tokens: int = 4000) -> str:
        """Format as context string for prompt injection."""
        
        sections = []
        budget_remaining = budget_tokens
        
        # 1. Feature spec (highest priority - 40%)
        spec_text = self._format_feature_spec()
        if spec_text and len(spec_text) < budget_remaining * 0.4:
            sections.append(f"## Feature Specification\n\n{spec_text}")
            budget_remaining -= len(spec_text.split())
        
        # 2. Project architecture context (20%)
        if self.project_architecture:
            arch_text = self._format_architecture()
            if len(arch_text.split()) < budget_remaining * 0.2:
                sections.append(f"## Project Architecture\n\n{arch_text}")
                budget_remaining -= len(arch_text.split())
        
        # 3. Related features (15%)
        if self.related_features:
            related_text = self._format_related()
            if len(related_text.split()) < budget_remaining * 0.15:
                sections.append(f"## Related Features\n\n{related_text}")
                budget_remaining -= len(related_text.split())
        
        # 4. Relevant patterns (15%)
        if self.relevant_patterns:
            patterns_text = self._format_patterns()
            if len(patterns_text.split()) < budget_remaining * 0.15:
                sections.append(f"## Recommended Patterns\n\n{patterns_text}")
                budget_remaining -= len(patterns_text.split())
        
        # 5. Warnings (10%)
        if self.warnings:
            warnings_text = self._format_warnings()
            sections.append(f"## Warnings from Past Implementations\n\n{warnings_text}")

        # 6. Role constraints (NEW - from TASK-REV-1505)
        if self.role_constraints:
            role_text = self._format_role_constraints()
            sections.append(f"## Role Constraints (Player/Coach)\n\n{role_text}")

        # 7. Quality gate configs (NEW - from TASK-REV-1505)
        if self.quality_gate_configs:
            gate_text = self._format_quality_gates()
            sections.append(f"## Quality Gate Thresholds\n\n{gate_text}")

        return "\n\n".join(sections)

    def _format_role_constraints(self) -> str:
        """Format role constraints for prompt (NEW - TASK-REV-1505)."""

        lines = []
        for constraint in self.role_constraints[:2]:  # Player and Coach
            role = constraint.get('role', 'unknown')
            must_do = constraint.get('must_do', [])
            must_not_do = constraint.get('must_not_do', [])
            lines.append(f"**{role.title()}**:")
            for item in must_do[:3]:
                lines.append(f"  ✓ {item}")
            for item in must_not_do[:3]:
                lines.append(f"  ✗ {item}")
        return '\n'.join(lines)

    def _format_quality_gates(self) -> str:
        """Format quality gate configs for prompt (NEW - TASK-REV-1505)."""

        lines = []
        for config in self.quality_gate_configs[:4]:  # Max 4 task types
            task_type = config.get('task_type', 'unknown')
            coverage = config.get('coverage_threshold', 0.8)
            arch_threshold = config.get('arch_review_threshold', 60)
            lines.append(f"**{task_type}**: coverage≥{coverage*100:.0f}%, arch≥{arch_threshold}")
        return '\n'.join(lines)
    
    def _format_feature_spec(self) -> str:
        """Format feature spec for prompt."""
        
        spec = self.feature_spec
        lines = [
            f"**ID**: {spec.get('id', 'N/A')}",
            f"**Title**: {spec.get('title', 'N/A')}",
            f"**Description**: {spec.get('description', 'N/A')}"
        ]
        
        if spec.get('success_criteria'):
            lines.append("\n**Success Criteria**:")
            for criterion in spec['success_criteria']:
                lines.append(f"- {criterion}")
        
        if spec.get('technical_requirements'):
            lines.append("\n**Technical Requirements**:")
            for req in spec['technical_requirements']:
                lines.append(f"- {req}")
        
        return '\n'.join(lines)
    
    def _format_architecture(self) -> str:
        """Format architecture context."""
        
        arch = self.project_architecture
        return f"""Architecture: {arch.get('architecture_style', 'N/A')}
Key Components: {', '.join(arch.get('key_components', []))}
Entry Points: {', '.join(arch.get('entry_points', []))}"""
    
    def _format_related(self) -> str:
        """Format related features."""
        
        lines = []
        for feature in self.related_features[:3]:  # Limit to 3
            lines.append(f"- **{feature.get('id')}**: {feature.get('title')}")
        return '\n'.join(lines)
    
    def _format_patterns(self) -> str:
        """Format recommended patterns."""
        
        lines = []
        for pattern in self.relevant_patterns[:3]:  # Limit to 3
            lines.append(f"- **{pattern.get('name')}**: {pattern.get('when_to_use', pattern.get('description', ''))[:100]}")
        return '\n'.join(lines)
    
    def _format_warnings(self) -> str:
        """Format warnings."""
        
        lines = []
        for warning in self.warnings[:3]:  # Limit to 3
            lines.append(f"⚠️ {warning.get('fact', str(warning))[:150]}")
        return '\n'.join(lines)


class FeaturePlanContextBuilder:
    """Builds rich context for feature planning."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.graphiti = get_graphiti()
        self.ingestor = ContextIngestor()
        self.detector = FeatureDetector(project_root)
    
    async def build_context(
        self,
        description: str,
        context_files: Optional[List[Path]] = None,
        tech_stack: str = "python"
    ) -> FeaturePlanContext:
        """Build comprehensive context for feature planning."""
        
        # 1. Detect feature ID and find spec if not provided
        feature_id = self.detector.detect_feature_id(description)
        
        if context_files:
            spec_file = context_files[0]
        elif feature_id:
            spec_file = self.detector.find_feature_spec(feature_id)
        else:
            spec_file = None
        
        # 2. Seed feature spec to Graphiti
        feature_spec = {}
        if spec_file and spec_file.exists():
            results = await self.ingestor.ingest_files(
                files=[spec_file],
                context_type="feature",
                force_update=True  # Always update during planning
            )
            if results and results[0].success:
                # Query back the structured spec
                query_results = await self.graphiti.search(
                    query=feature_id or description,
                    group_ids=["feature_specs"],
                    num_results=1
                )
                if query_results:
                    feature_spec = query_results[0]
        
        # 3. Seed additional context files
        for ctx_file in (context_files or [])[1:]:
            if ctx_file.suffix == ".md":
                # Auto-detect type
                if "claude" in ctx_file.name.lower():
                    await self.ingestor.ingest_files([ctx_file], "project-overview", True)
                elif "adr" in str(ctx_file).lower():
                    await self.ingestor.ingest_files([ctx_file], "adr", True)
        
        # 4. Query Graphiti for enrichment
        related_features = await self._get_related_features(feature_id, description)
        relevant_patterns = await self._get_relevant_patterns(description, tech_stack)
        similar_implementations = await self._get_similar_implementations(description)
        project_architecture = await self._get_project_architecture()
        warnings = await self._get_warnings(description)

        # 5. Query AutoBuild support context (NEW - from TASK-REV-1505)
        role_constraints = await self._get_role_constraints()
        quality_gate_configs = await self._get_quality_gate_configs()
        implementation_modes = await self._get_implementation_modes()

        return FeaturePlanContext(
            feature_spec=feature_spec,
            related_features=related_features,
            relevant_patterns=relevant_patterns,
            similar_implementations=similar_implementations,
            project_architecture=project_architecture,
            warnings=warnings,
            role_constraints=role_constraints,
            quality_gate_configs=quality_gate_configs,
            implementation_modes=implementation_modes
        )
    
    async def _get_related_features(
        self,
        feature_id: Optional[str],
        description: str
    ) -> List[Dict]:
        """Get related features from Graphiti."""
        
        query = feature_id or description
        results = await self.graphiti.search(
            query=query,
            group_ids=["feature_specs"],
            num_results=5
        )
        return [r for r in results if r.get('id') != feature_id]
    
    async def _get_relevant_patterns(
        self,
        description: str,
        tech_stack: str
    ) -> List[Dict]:
        """Get relevant patterns for this feature."""
        
        return await self.graphiti.search(
            query=description,
            group_ids=[f"patterns_{tech_stack}", "patterns"],
            num_results=5
        )
    
    async def _get_similar_implementations(self, description: str) -> List[Dict]:
        """Get similar past implementations."""
        
        return await self.graphiti.search(
            query=description,
            group_ids=["task_outcomes", "feature_completions"],
            num_results=5
        )
    
    async def _get_project_architecture(self) -> Dict:
        """Get project architecture context."""
        
        results = await self.graphiti.search(
            query="project architecture components",
            group_ids=["project_overview", "project_architecture"],
            num_results=1
        )
        return results[0] if results else {}
    
    async def _get_warnings(self, description: str) -> List[Dict]:
        """Get warnings from past failures."""

        return await self.graphiti.search(
            query=description,
            group_ids=["failure_patterns", "failed_approaches"],
            num_results=3
        )

    # NEW methods from TASK-REV-1505 review

    async def _get_role_constraints(self) -> List[Dict]:
        """Get Player/Coach role constraints (NEW - TASK-REV-1505).

        Prevents role reversal where Player makes decisions or Coach implements.
        """

        return await self.graphiti.search(
            query="role constraints player coach",
            group_ids=["role_constraints"],
            num_results=2  # Player and Coach
        )

    async def _get_quality_gate_configs(self) -> List[Dict]:
        """Get task-type specific quality gate configs (NEW - TASK-REV-1505).

        Prevents threshold drift where acceptable scores change mid-session.
        """

        return await self.graphiti.search(
            query="quality gate config threshold",
            group_ids=["quality_gate_configs"],
            num_results=4  # scaffolding, feature, testing, documentation
        )

    async def _get_implementation_modes(self) -> List[Dict]:
        """Get implementation mode guidance (NEW - TASK-REV-1505).

        Clarifies direct vs task-work patterns to prevent file location errors.
        """

        return await self.graphiti.search(
            query="implementation mode direct task-work",
            group_ids=["implementation_modes"],
            num_results=2  # direct and task-work
        )
```

### Integration with feature-plan Command

```python
# In feature_plan.py slash command or CLI

async def feature_plan(
    description: str,
    context_files: Optional[List[str]] = None
):
    """Execute feature planning with Graphiti context."""
    
    project_root = Path.cwd()
    
    # Build context
    context_builder = FeaturePlanContextBuilder(project_root)
    context = await context_builder.build_context(
        description=description,
        context_files=[Path(f) for f in (context_files or [])],
        tech_stack=detect_tech_stack(project_root)
    )
    
    # Format for prompt injection
    context_prompt = context.to_prompt_context(budget_tokens=4000)
    
    # Inject into planning prompt
    enhanced_prompt = f"""
{base_planning_prompt}

## Context from Project Knowledge

{context_prompt}

## Feature to Plan

{description}

Please create a detailed implementation plan with tasks.
"""
    
    # Continue with normal feature planning...
```

---

## Success Criteria

1. **Auto-detection works** - Feature ID extracted from description, spec file found
2. **Context seeded** - Feature spec is in Graphiti before planning starts
3. **Enrichment queries work** - Related features, patterns, warnings retrieved
4. **Context injected** - Planning prompt includes all relevant context
5. **Budget respected** - Context fits within token budget
6. **Subsequent commands benefit** - `/feature-build` and `/task-work` can query the seeded spec

---

## Implementation Tasks

| Task ID | Description | Estimate |
|---------|-------------|----------|
| TASK-GR-003A | Implement FeatureDetector class | 2h |
| TASK-GR-003B | Implement FeaturePlanContext dataclass and formatting | 2h |
| TASK-GR-003C | Implement FeaturePlanContextBuilder | 3h |
| TASK-GR-003D | Integrate with /feature-plan command | 2h |
| TASK-GR-003E | Add --context CLI option to feature-plan | 1h |
| TASK-GR-003F | **NEW**: Add AutoBuild context queries (role_constraints, quality_gate_configs, implementation_modes) | 2h |
| TASK-GR-003G | Add tests for context building (including AutoBuild context) | 2h |
| TASK-GR-003H | Update documentation | 1h |

**Total Estimate**: 15 hours (revised from 13h based on TASK-REV-1505 review)

### New Tasks Rationale (from TASK-REV-1505)

- **TASK-GR-003F**: Ensures feature planning has access to role constraints, quality gate configs, and implementation mode guidance to prevent AutoBuild workflow issues

---

## Usage Examples

### Basic Usage (Auto-Detect)

```bash
# Feature ID in description triggers auto-detection
$ /feature-plan "implement FEAT-SKEL-001 walking skeleton"

[Graphiti] Found feature spec: docs/features/FEAT-SKEL-001-walking-skeleton.md
[Graphiti] Seeded feature spec to Graphiti
[Graphiti] Found 2 related features: FEAT-SKEL-002, FEAT-SKEL-003
[Graphiti] Found 3 relevant patterns: mcp-tool-pattern, docker-setup, ping-healthcheck
[Graphiti] No warnings found for this type of feature

Planning with enriched context...
```

### Explicit Context Files

```bash
# Provide context files explicitly
$ /feature-plan "implement walking skeleton" \
    --context docs/features/FEAT-SKEL-001-walking-skeleton.md \
    --context CLAUDE.md

[Graphiti] Seeded feature spec: FEAT-SKEL-001
[Graphiti] Seeded project overview from CLAUDE.md
[Graphiti] Building enriched context...

Planning with enriched context...
```

### Context in Generated Tasks

After planning, the generated tasks reference the feature:

```markdown
# TASK-001: Set up basic MCP server structure

**Feature**: FEAT-SKEL-001 Walking Skeleton
**Feature Context**: Available in Graphiti - query "FEAT-SKEL-001 requirements"

## Requirements
Based on feature spec success criteria:
- [ ] MCP server responds to ping tool
- [ ] Returns {pong: true, timestamp: <iso>}
```

---

## Integration Points

### With `/feature-build`

When `/feature-build FEAT-SKEL-001` runs:

1. Queries Graphiti for feature spec (already seeded by /feature-plan)
2. Gets full context including success criteria
3. Uses context to validate task completion

### With `/task-work`

When `/task-work TASK-001` runs on a feature task:

1. Detects parent feature from task metadata
2. Queries Graphiti for feature context
3. Includes relevant success criteria in task context

---

## AutoBuild Integration (NEW - from TASK-REV-1505)

Feature planning now includes AutoBuild support context to prevent common workflow issues:

### Role Constraints in Planning

When generating tasks during `/feature-plan`, the system queries `role_constraints` to:
- Include Player/Coach responsibilities in task descriptions
- Prevent tasks that would cause role confusion
- Add "ask before" triggers to task metadata

### Quality Gate Context

Quality gate configs ensure generated tasks include:
- Appropriate thresholds based on task type (scaffolding vs feature)
- Complexity-appropriate review requirements
- Clear success criteria aligned with configured gates

### Implementation Mode Guidance

Tasks generated include implementation mode metadata:
- `mode: task-work` vs `mode: direct` based on task complexity
- Result location patterns (worktree vs inline)
- State recovery strategies

---

## Future Enhancements

1. **Feature dependency graphs** - Query Graphiti for feature dependencies
2. **Effort estimation** - Use similar past features to estimate effort
3. **Risk assessment** - Identify risks based on similar feature warnings
4. **Auto-suggest related tasks** - Based on similar feature implementations
5. **Turn state integration** - Load previous turn context when resuming feature work
