# Dark Factory — GuardKit Template Specs

Template specification documents for new GuardKit templates. These are the design
briefs used with `/template-create` to generate new built-in templates.

## Active Specs

| Spec | Template Name | Status | Source Repo |
|------|--------------|--------|-------------|
| `template-spec-python-library.md` | `python-library` | Ready to create | `youtube-transcript-mcp` (exemplar) |
| `template-spec-nats-asyncio-service.md` | `nats-asyncio-service` | Ready to create | Greenfield — bootstrap via FastStream cookiecutter |

## Existing Templates (Already Built)

| Template | Location | Created From |
|----------|----------|-------------|
| `langchain-deepagents` | `installer/core/templates/langchain-deepagents/` | `deepagents-player-coach-exemplar` |
| `langchain-deepagents-weighted-evaluation` | `installer/core/templates/langchain-deepagents-weighted-evaluation/` | Extended from base |
| `langchain-deepagents-orchestrator` | `installer/core/templates/langchain-deepagents-orchestrator/` | `deepagents-orchestrator-exemplar` — registered as built-in |

## Workflow

```bash
# 1. Create template from spec
/template-create --name <template-name> --path <source-repo>

# 2. Enhance agents
/agent-enhance <template-name>/<agent-name> --hybrid

# 3. Review task to add as built-in to installer
# (pending for python-library + nats-asyncio-service)
```

## Archive

Superseded documents moved to `archive/`:
- `pipeline-orchestrator-*.md` → authoritative versions now in `guardkitfactory/docs/research/`
- `langchain-deepagents-adversarial-conversation-starter.md` → superseded by `langchain-deepagents-orchestrator` template
