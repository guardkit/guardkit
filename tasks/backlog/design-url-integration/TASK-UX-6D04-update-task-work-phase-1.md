---
id: TASK-UX-6D04
title: Update task-work Phase 1 to load design URL
status: backlog
created: 2025-11-11T11:20:00Z
updated: 2025-11-11T11:20:00Z
priority: high
tags: [ux-integration, task-work, phase-1]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update task-work Phase 1 to load design URL

## Description

Update the `/task-work` command's Phase 1 (Requirements Analysis) to detect and load design URLs from task frontmatter, validate MCP availability, and prepare design context for orchestrator routing in Phase 3.

This is part of Phase 4 of the Design URL Integration project (see [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] Phase 1 detects `design_url` in task frontmatter
- [ ] Design source auto-detected (figma, zeplin, sketch)
- [ ] Design URL parsed to extract metadata (file_key, node_id, project_id, screen_id)
- [ ] MCP availability validated before proceeding
- [ ] Design context stored in task state for Phase 3
- [ ] Clear error messages when MCP not available
- [ ] Help text provided for MCP installation
- [ ] Graceful fallback when no design URL present
- [ ] Command updated in global commands directory
- [ ] Tests updated to cover design URL scenarios

## Implementation Notes

### Source File
- **File**: `installer/core/commands/task-work.md`

### Key Changes Required

**1. Update Phase 1: Requirements Analysis**

Add design URL detection and loading logic:

```python
# Phase 1: Requirements Analysis
def phase_1_requirements_analysis(task: Task, config: Config) -> AnalysisResult:
    """
    Analyze task requirements and detect design URL if present.

    For GuardKit: This phase is skipped for requirements gathering,
    but we still need to check for design URLs.
    """

    # Check if task has design URL
    design_url = task.frontmatter.get('design_url')

    if design_url:
        # Design-driven workflow detected
        console.print("[blue]📐 Design URL detected - switching to design-driven workflow[/blue]")

        # Step 1: Detect design source
        design_source = detect_design_source(design_url)
        console.print(f"[dim]Design source: {design_source}[/dim]")

        # Step 2: Parse design URL to extract metadata
        design_metadata = parse_design_url(design_url, design_source)

        # Step 3: Validate MCP availability
        mcp_required = get_required_mcp(design_source)
        if not is_mcp_available(mcp_required):
            raise MCPNotAvailableError(
                f"Required MCP server '{mcp_required}' is not available.\n"
                f"Please install it using the appropriate guide:\n"
                f"  - Figma: See docs/mcp-setup/figma-mcp-setup.md\n"
                f"  - Zeplin: See docs/mcp-setup/zeplin-mcp-setup.md"
            )

        # Step 4: Store design context for Phase 3
        design_context = DesignContext(
            design_url=design_url,
            design_source=design_source,
            design_metadata=design_metadata,
            mcp_available=True
        )

        # Save to task state
        task.state['design_context'] = design_context.to_dict()
        task.save()

        console.print("[green]✓[/green] Design context loaded successfully")

        return AnalysisResult(
            has_design_url=True,
            design_context=design_context,
            skip_requirements_phase=True  # GuardKit skips Phase 1
        )
    else:
        # Standard workflow (no design URL)
        console.print("[dim]No design URL detected - using standard workflow[/dim]")

        return AnalysisResult(
            has_design_url=False,
            design_context=None,
            skip_requirements_phase=True  # GuardKit skips Phase 1
        )
```

**2. Add Design Source Detection**

```python
def detect_design_source(design_url: str) -> str:
    """
    Detect design source from URL pattern.

    Supported sources:
    - figma: figma.com/design/* or figma.com/file/*
    - zeplin: app.zeplin.io/project/*
    - sketch: sketch.cloud/* (future support)

    Returns:
        Design source identifier: "figma" | "zeplin" | "sketch" | "unknown"
    """
    url_lower = design_url.lower()

    if 'figma.com' in url_lower:
        return 'figma'
    elif 'zeplin.io' in url_lower:
        return 'zeplin'
    elif 'sketch.cloud' in url_lower:
        return 'sketch'
    else:
        return 'unknown'
```

**3. Add Design URL Parser**

```python
def parse_design_url(design_url: str, design_source: str) -> dict:
    """
    Parse design URL to extract metadata.

    Figma URL format:
        https://figma.com/design/{file_key}/...?node-id={node_id}
        https://figma.com/file/{file_key}/...?node-id={node_id}

    Zeplin URL format:
        https://app.zeplin.io/project/{project_id}/screen/{screen_id}
        https://app.zeplin.io/project/{project_id}/styleguide/components?coid={component_id}

    Returns:
        Dictionary with extracted metadata
    """
    from urllib.parse import urlparse, parse_qs
    import re

    parsed = urlparse(design_url)
    query_params = parse_qs(parsed.query)

    if design_source == 'figma':
        # Extract file_key from path: /design/{file_key}/ or /file/{file_key}/
        match = re.search(r'/(design|file)/([a-zA-Z0-9]+)', parsed.path)
        file_key = match.group(2) if match else None

        # Extract node_id from query parameter: ?node-id=123-456
        node_id_raw = query_params.get('node-id', [None])[0]

        # Convert node-id format: "123-456" -> "123:456"
        node_id = node_id_raw.replace('-', ':') if node_id_raw else None

        return {
            'file_key': file_key,
            'node_id': node_id,
            'url': design_url
        }

    elif design_source == 'zeplin':
        # Extract project_id and screen_id from path
        # /project/{project_id}/screen/{screen_id}
        match = re.search(r'/project/([^/]+)/screen/([^/]+)', parsed.path)
        if match:
            return {
                'project_id': match.group(1),
                'screen_id': match.group(2),
                'url': design_url
            }

        # Extract project_id and component_id from query
        # /project/{project_id}/styleguide/components?coid={component_id}
        match = re.search(r'/project/([^/]+)', parsed.path)
        component_id = query_params.get('coid', [None])[0]
        if match and component_id:
            return {
                'project_id': match.group(1),
                'component_id': component_id,
                'url': design_url
            }

        return {
            'project_id': None,
            'screen_id': None,
            'component_id': None,
            'url': design_url
        }

    else:
        return {
            'url': design_url
        }
```

**4. Add MCP Availability Check**

```python
def get_required_mcp(design_source: str) -> str:
    """
    Get required MCP server name for design source.

    Returns:
        MCP server name
    """
    mcp_mapping = {
        'figma': 'figma-dev-mode',
        'zeplin': 'zeplin',
        'sketch': 'sketch'  # Future support
    }
    return mcp_mapping.get(design_source, 'unknown')


def is_mcp_available(mcp_name: str) -> bool:
    """
    Check if MCP server is available and configured.

    This should check the MCP server status via the MCP client.

    Returns:
        True if MCP is available, False otherwise
    """
    # Implementation will depend on how MCP servers are queried
    # For now, assume we can check via mcp-client
    try:
        # Example: Check if MCP server is in claude_desktop_config.json
        config_path = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                mcpServers = config.get('mcpServers', {})
                return mcp_name in mcpServers
        return False
    except Exception:
        return False
```

**5. Add Design Context Data Class**

```python
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class DesignContext:
    """
    Design context loaded from task frontmatter.
    """
    design_url: str
    design_source: str  # "figma" | "zeplin" | "sketch"
    design_metadata: dict
    mcp_available: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'DesignContext':
        """Create from dictionary."""
        return cls(**data)

    def get_orchestrator_name(self) -> str:
        """Get appropriate orchestrator for this design source."""
        orchestrator_mapping = {
            'figma': 'figma-orchestrator',
            'zeplin': 'zeplin-orchestrator',
            'sketch': 'sketch-orchestrator'  # Future support
        }
        return orchestrator_mapping.get(self.design_source, None)
```

**6. Update Phase 1 Output**

Modify the phase output to include design context information:

```python
# Print Phase 1 summary
console.print("\n[bold]Phase 1 Complete: Requirements Analysis[/bold]")

if analysis_result.has_design_url:
    console.print(f"  [blue]Design Source:[/blue] {analysis_result.design_context.design_source}")
    console.print(f"  [blue]Design URL:[/blue] {analysis_result.design_context.design_url}")
    console.print(f"  [blue]Orchestrator:[/blue] {analysis_result.design_context.get_orchestrator_name()}")
else:
    console.print("  [dim]Standard workflow (no design URL)[/dim]")
```

**7. Error Handling**

Add comprehensive error handling:

```python
class MCPNotAvailableError(Exception):
    """Raised when required MCP server is not available."""
    pass


class InvalidDesignURLError(Exception):
    """Raised when design URL is invalid or cannot be parsed."""
    pass


try:
    analysis_result = phase_1_requirements_analysis(task, config)
except MCPNotAvailableError as e:
    console.print(f"[red]✗ MCP Server Not Available[/red]")
    console.print(str(e))
    console.print("\n[yellow]Action Required:[/yellow]")
    console.print("  1. Install the required MCP server")
    console.print("  2. Re-run /task-work once MCP is configured")
    sys.exit(1)
except InvalidDesignURLError as e:
    console.print(f"[red]✗ Invalid Design URL[/red]")
    console.print(str(e))
    console.print("\n[yellow]Supported URL formats:[/yellow]")
    console.print("  Figma: https://figma.com/design/{file_key}/...?node-id={node_id}")
    console.print("  Zeplin: https://app.zeplin.io/project/{project_id}/screen/{screen_id}")
    sys.exit(1)
```

**8. Update Phase Transition**

Ensure design context is passed to subsequent phases:

```python
# After Phase 1 completes, pass context to Phase 2
if analysis_result.has_design_url:
    # Phase 2 will know about design context
    phase_2_result = phase_2_planning(
        task=task,
        config=config,
        design_context=analysis_result.design_context  # Pass context
    )
```

### Testing Strategy

**Unit Tests**:
- Test `detect_design_source()` with various URLs
- Test `parse_design_url()` for Figma URLs
- Test `parse_design_url()` for Zeplin URLs
- Test `is_mcp_available()` with mock config
- Test `get_required_mcp()` for each source
- Test `DesignContext.to_dict()` and `from_dict()`

**Integration Tests**:
- Full Phase 1 execution with Figma design URL
- Full Phase 1 execution with Zeplin design URL
- Full Phase 1 execution without design URL (standard workflow)
- MCP not available error handling
- Invalid design URL error handling

**Manual Testing**:
- Test with real Figma URL and MCP installed
- Test with real Zeplin URL and MCP installed
- Test with Figma URL but MCP not installed (should error)
- Test with invalid URL format (should error)

## Test Requirements

- [ ] Unit test: detect_design_source() for Figma URLs
- [ ] Unit test: detect_design_source() for Zeplin URLs
- [ ] Unit test: detect_design_source() for unknown URLs
- [ ] Unit test: parse_design_url() for Figma (with node-id)
- [ ] Unit test: parse_design_url() for Figma (without node-id)
- [ ] Unit test: parse_design_url() for Zeplin screen
- [ ] Unit test: parse_design_url() for Zeplin component
- [ ] Unit test: is_mcp_available() returns true when MCP configured
- [ ] Unit test: is_mcp_available() returns false when MCP not configured
- [ ] Unit test: get_required_mcp() returns correct MCP name
- [ ] Unit test: DesignContext serialization (to_dict/from_dict)
- [ ] Integration test: Phase 1 with Figma design URL
- [ ] Integration test: Phase 1 with Zeplin design URL
- [ ] Integration test: Phase 1 without design URL
- [ ] Integration test: MCP not available error
- [ ] Integration test: Invalid design URL error
- [ ] Edge case test: Malformed Figma URL
- [ ] Edge case test: Malformed Zeplin URL
- [ ] Edge case test: Missing node-id in Figma URL

## Dependencies

**Blockers** (must be completed first):
- TASK-UX-7F1E: Add design URL parameter to task-create (design_url field must exist in frontmatter)
- TASK-UX-C3A3: Implement design URL validation (validation logic needed)

**Related** (will use output from this task):
- TASK-UX-6xxx: Update task-work Phase 3 (will consume design context)

## Next Steps

After completing this task:
1. TASK-UX-008: Update task-work Phase 3 to route to orchestrators
2. TASK-UX-009: Update task-refine for design context awareness

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md)
- [Implementation Guide - Phase 4](../../docs/proposals/design-url-integration-implementation-guide.md#phase-4-update-task-work)
- [Existing task-work Command](../../installer/core/commands/task-work.md)
- [Figma URL Format](https://help.figma.com/hc/en-us/articles/360045942953-Share-files-and-prototypes)
- [Zeplin URL Format](https://support.zeplin.io/en/articles/244698-sharing-screens)

## Implementation Estimate

**Duration**: 5-7 hours

**Complexity**: 7/10 (Medium-High)
- Modify critical command (task-work)
- Add design URL parsing logic for multiple sources
- Implement MCP availability checking
- Add comprehensive error handling
- Maintain backward compatibility (standard workflow)
- Pass design context to subsequent phases

## Test Execution Log

_Automatically populated by /task-work_
