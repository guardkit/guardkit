---
id: TASK-DM-002
title: Implement MCP facade for design extraction
status: in_progress
created: 2026-02-07 10:00:00+00:00
updated: 2026-02-07 10:00:00+00:00
priority: high
task_type: feature
parent_review: TASK-REV-D3E0
feature_id: FEAT-D4CE
wave: 1
implementation_mode: task-work
complexity: 6
dependencies: []
tags:
- design-mode
- mcp
- figma
- zeplin
- facade
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-D4CE
  base_branch: main
  started_at: '2026-02-07T21:29:48.103380'
  last_updated: '2026-02-07T22:28:13.526735'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- task-work execution exceeded 900s timeout'
    timestamp: '2026-02-07T21:29:48.103380'
    player_summary: '[RECOVERED via git_only] Original error: SDK timeout after 900s:
      task-work execution exceeded 900s timeout'
    player_success: true
    coach_success: true
---

# Implement MCP Facade for Design Extraction

## Description

Create a `DesignExtractor` facade class that hides MCP complexity from downstream agents. The orchestrator handles all MCP calls; Player and Coach never call MCP tools directly. Supports both Figma and Zeplin MCP servers with caching and token budget management.

## Requirements

1. Create `guardkit/orchestrator/mcp_design_extractor.py` with `DesignExtractor` class:
   ```python
   class DesignExtractor:
       async def extract_figma(self, file_key: str, node_id: str) -> DesignData
       async def extract_zeplin(self, project_id: str, screen_id: str) -> DesignData
       def verify_mcp_availability(self, source: str) -> bool
       def summarize_design_data(self, data: DesignData) -> str
   ```

2. Figma MCP integration:
   - `mcp__figma-dev-mode__get_code` — component structure (HIGH token risk)
   - `mcp__figma-dev-mode__get_image` — visual reference screenshot
   - `mcp__figma-dev-mode__get_variable_defs` — design tokens

3. Zeplin MCP integration:
   - `mcp__zeplin__get_screen` — screen design data
   - `mcp__zeplin__get_component` — component design data
   - `mcp__zeplin__get_styleguide` — design tokens
   - `mcp__zeplin__get_colors` — colour palette
   - `mcp__zeplin__get_text_styles` — typography

4. Token budget management:
   - Query specific nodes only (never entire files)
   - Summarise extracted data to ~3K tokens for agent context
   - Cache MCP responses (1-hour TTL) in `.guardkit/cache/design/`

5. Error handling:
   - Verify MCP tools available before extraction (fail fast)
   - Exponential backoff for transient failures (3 retries)
   - Clear error messages with remediation steps

6. Node ID format validation:
   - Validate colon format before every Figma MCP call
   - Convert if needed (defensive, even though TASK-DM-001 converts at storage)

## Acceptance Criteria

- [ ] `DesignExtractor` class created with Figma and Zeplin extraction methods
- [ ] MCP availability verification with fail-fast behaviour
- [ ] Node ID format validated before every Figma MCP call
- [ ] Token budget respected (specific node queries, summarisation)
- [ ] MCP responses cached (1-hour TTL, keyed by design URL hash)
- [ ] Retry logic for transient MCP failures (exponential backoff, 3 retries)
- [ ] `DesignData` dataclass captures: elements, tokens, visual reference, metadata
- [ ] Summarise method produces ~3K token context string
- [ ] Unit tests with mocked MCP responses

## Technical Notes

- See FEAT-DESIGN-MODE-spec.md §2 (MCP Integration Layer)
- Observed Figma responses up to 351K tokens — summarisation is critical
- Follow existing MCP patterns (context7, design-patterns) for graceful fallback
- Cache location: `.guardkit/cache/design/{url_hash}/`
