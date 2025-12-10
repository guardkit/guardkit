# Archive Folder - Historical Tasks

**Archived**: 2025-11-25
**Source**: Former `tasks/archive/` folder

## Contents

This section contains **historical backlog tasks and planning documents** from the early development of Taskwright (October-November 2024). These tasks were never completed and have been superseded by the current implementation.

### What's Here

1. **EPIC-001 Planning** (`epic-001-algorithmic-approach/`)
   - 54 planning documents
   - Comprehensive reviews, risk assessments, implementation plans
   - Technology-agnostic design proposals
   - Parallel implementation strategies
   - Task breakdowns and quick-start guides

2. **Obsolete Backlog Tasks** (3 tasks)
   - `TASK-003-local-agent-scanner.md` - Agent discovery (superseded)
   - `TASK-004-configurable-agent-sources.md` - Agent configuration (superseded)
   - `TASK-009-agent-recommendation.md` - Agent recommendations (superseded)

### Why These Were Archived

**Status**: These tasks represent **early explorations** that were either:
- ✅ Implemented differently in the current system
- ❌ Deemed unnecessary for the current approach
- 🔄 Superseded by better solutions

### Current System

The **actual implementation** that replaced these plans:

1. **Templates**: `installer/core/templates/`
   - 6 production templates (react-typescript, fastapi-python, nextjs-fullstack, react-fastapi-monorepo, taskwright-python, default)
   - Each with 3 specialized agents

2. **Global Agents**: `installer/core/agents/`
   - 16 global agents (architectural-reviewer, task-manager, code-reviewer, etc.)
   - Enhanced with `/agent-enhance` command

3. **Commands**: `installer/core/commands/`
   - `/template-create` - Template generation
   - `/agent-enhance` - AI-powered agent enhancement
   - `/agent-format` - Pattern-based agent formatting
   - Complete task management workflow

### Historical Value

These documents show:
- ✅ Evolution of Taskwright's architecture
- ✅ Decision-making process for technology-agnostic design
- ✅ Early thinking about agent orchestration
- ✅ Risk assessments and trade-off analysis

### Recommendation

**DO NOT USE** tasks or plans from this archive. They are **historical artifacts** documenting the project's evolution, not current specifications.

For current tasks and planning, see:
- **Active backlog**: `tasks/backlog/`
- **In progress**: `tasks/in_progress/`
- **In review**: `tasks/in_review/`
- **Documentation**: `docs/`

---

**Archived By**: Claude Code (organizational cleanup)
**Date**: 2025-11-25
**Reason**: Historical planning superseded by current implementation
