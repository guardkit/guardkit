# Archived Specifications

This directory contains historical specification documents for completed features.

## Files Archived (2025-11-26)

### 1. agent-enhance-strategy-simplification-spec.md (38,519 bytes)
**Created**: 2025-11-22
**Status**: DRAFT / Not Implemented

Specification for simplifying `/agent-enhance` command's strategy selection:
- **Proposed**: Boolean flags (`--hybrid`, `--static`) instead of enum-based `--strategy=VALUE`
- **Goal**: Address user confusion around default vs recommended strategies
- **Current State**: Proposal not implemented, keeping verbose enum approach

**Reason for Archive**: Specification was drafted but not pursued. Current enum-based approach (`--strategy=ai|hybrid|static`) is working adequately.

### 2. enhanced-prompt-format.md (9,129 bytes)
**Created**: 2025-11-07
**Status**: Completed

Specification for enhanced prompt format in agent content enhancer:
- JSON schema enforcement for boundary sections
- Improved AI output reliability
- Defense-in-depth validation

**Related Completed Work**:
- [TASK-BDRY-E84A](../../../tasks/completed/TASK-BDRY-E84A/) - Enforce JSON Schema for Agent Boundaries Generation
- Result: Reduced AI omission rate from ~30-40% to <5%

## Active Specifications

For current specification documents, see:
- Task specifications in individual task files (tasks/backlog/, tasks/in_progress/)
- Implementation guides in docs/guides/
- Architecture decisions in docs/decisions/
