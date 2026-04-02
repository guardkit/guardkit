# Implementation Guide: Register Orchestrator Template

**Feature**: FEAT-ROT — Register `langchain-deepagents-orchestrator` as builtin template
**Parent Review**: TASK-REV-TI25
**Total Subtasks**: 5
**Estimated Effort**: ~45 minutes
**Testing**: Minimal (metadata/config changes)

---

## Wave Breakdown

### Wave 1: Fix Source Template (parallel)

Fix issues in the template at `~/.agentecflow/templates/langchain-deepagents-orchestrator/` before copying.

| Task | Description | Mode | Effort |
|------|-------------|------|--------|
| TASK-ROT-001 | Fix manifest.json metadata (display_name, description, frameworks, paths) | task-work | 15 min |
| TASK-ROT-002 | Fix CompiledStateGraph import in agents.py.template | task-work | 10 min |

**Dependencies**: None — these can run in parallel.

**Verification**: After both complete, check:
```bash
# No absolute paths
grep -r "/Users/" ~/.agentecflow/templates/langchain-deepagents-orchestrator/manifest.json
# Should return nothing

# Display name correct
python3 -c "import json; m=json.load(open('$HOME/.agentecflow/templates/langchain-deepagents-orchestrator/manifest.json')); print(m['display_name'])"
# Should print: LangChain DeepAgents Orchestrator
```

### Wave 2: Copy to Installer (sequential)

| Task | Description | Mode | Effort |
|------|-------------|------|--------|
| TASK-ROT-003 | Copy template to `installer/core/templates/` | direct | 5 min |

**Dependencies**: TASK-ROT-001, TASK-ROT-002

**Verification**:
```bash
# Template directory exists
ls installer/core/templates/langchain-deepagents-orchestrator/manifest.json

# No absolute paths in any file
grep -r "/Users/" installer/core/templates/langchain-deepagents-orchestrator/
# Should return nothing
```

### Wave 3: Update Registration Points (parallel)

| Task | Description | Mode | Effort |
|------|-------------|------|--------|
| TASK-ROT-004 | Update `init.py` help text | direct | 5 min |
| TASK-ROT-005 | Update CLAUDE.md and docs/templates.md | direct | 10 min |

**Dependencies**: TASK-ROT-003

**Verification**:
```bash
# Help text includes new template
grep "langchain-deepagents-orchestrator" guardkit/cli/init.py

# CLAUDE.md lists template
grep "langchain-deepagents-orchestrator" CLAUDE.md

# docs/templates.md lists template
grep "langchain-deepagents-orchestrator" docs/templates.md
```

---

## End-to-End Verification

After all waves complete:

```bash
# 1. Template is discoverable
python3 -c "
from guardkit.cli.init import _resolve_template_source_dir
result = _resolve_template_source_dir('langchain-deepagents-orchestrator')
print(f'Found: {result}')
"

# 2. No extends chain (standalone)
python3 -c "
import json
m = json.load(open('installer/core/templates/langchain-deepagents-orchestrator/manifest.json'))
print(f'extends: {m.get(\"extends\", \"(standalone)\")}')
print(f'display_name: {m[\"display_name\"]}')
"

# 3. Integration test (if available)
guardkit init langchain-deepagents-orchestrator --dry-run
```

---

## Wave 4: Template Polish (parallel, all depend on TASK-ROT-003)

These improve the template quality but are not required for registration to work.

| Task | Description | Mode | Effort |
|------|-------------|------|--------|
| TASK-ROT-006 | Add config templates (langgraph.json, config YAML, domain) | task-work | 30 min |
| TASK-ROT-007 | Enhance agents with `/agent-enhance --hybrid` | task-work | 60 min |
| TASK-ROT-008 | Add DeepAgents-specific pattern rules | task-work | 30 min |
| TASK-ROT-009 | Update template `.claude/CLAUDE.md` content | direct | 10 min |

**Dependencies**: All depend on TASK-ROT-003 (template must be in installer first).

**Verification**:
```bash
# Config templates exist
ls installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/langgraph.json.template
ls installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/orchestrator-config.yaml.template

# CLAUDE.md no longer says "None"
grep -v "None" installer/core/templates/langchain-deepagents-orchestrator/.claude/CLAUDE.md

# DeepAgents patterns exist
ls installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/patterns/two-model-orchestration.md
```
