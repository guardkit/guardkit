# Design Mode for Player-Coach Loops

## Problem

GuardKit's `/task-work` workflow treats all tasks as code-only. When implementing a UI from a design, developers manually inspect Figma/Zeplin, mentally translate design tokens, eyeball results, and iterate manually. This is error-prone, slow, and produces inconsistent results.

## Solution

Add design mode to the Player-Coach adversarial loop. When a task includes a design URL, the system:

1. **Extracts** design data via MCP (Figma/Zeplin) before the loop starts
2. **Documents** design boundaries via a 12-category prohibition checklist
3. **Generates** components via the Player with extracted design context
4. **Verifies** visual fidelity via the Coach using SSIM-based browser comparison

## Tasks

| ID | Title | Wave | Complexity | Status |
|----|-------|------|-----------|--------|
| TASK-DM-001 | Extend task frontmatter for design URLs | 1 | 3 | backlog |
| TASK-DM-002 | Implement MCP facade for design extraction | 1 | 6 | backlog |
| TASK-DM-003 | Implement Phase 0 design extraction in autobuild | 2 | 7 | backlog |
| TASK-DM-004 | Generate prohibition checklist from design data | 2 | 5 | backlog |
| TASK-DM-005 | Implement BrowserVerifier abstraction | 3 | 6 | backlog |
| TASK-DM-006 | Implement SSIM comparison pipeline | 3 | 5 | backlog |
| TASK-DM-007 | Integrate design context into Player-Coach prompts | 4 | 6 | backlog |
| TASK-DM-008 | Add design change detection and state-aware handling | 4 | 5 | backlog |

## Getting Started

See [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) for wave execution plan and architecture details.

Start with Wave 1: `TASK-DM-001` and `TASK-DM-002` (can run in parallel).
