---
paths: config/graphiti.yaml, guardkit/graphiti/**/*.py, docs/**/graphiti*
---

# Graphiti Knowledge Capture

GuardKit integrates with Graphiti for persistent knowledge capture across sessions. Build project understanding through guided Q&A and query stored knowledge via CLI.

## Interactive Capture

```bash
guardkit graphiti capture --interactive
guardkit graphiti capture --interactive --focus <category> --max-questions 5
```

### Focus Categories

**Project Knowledge:**

| Category | Captures |
|----------|----------|
| `project-overview` | Purpose, target users, goals, problem statement |
| `architecture` | Components, services, data flow |
| `domain` | Domain terminology, business rules |
| `constraints` | Technical/business constraints |
| `decisions` | Technology choices, rationale, trade-offs |
| `goals` | Key objectives and success criteria |

**AutoBuild Customization:**

| Category | Captures |
|----------|----------|
| `role-customization` | Player ask-before rules, Coach escalation rules |
| `quality-gates` | Coverage thresholds, arch review scores |
| `workflow-preferences` | Implementation mode preferences, turn limits |

## Knowledge Query Commands

```bash
# Show specific knowledge by ID
guardkit graphiti show <knowledge_id>

# Search knowledge
guardkit graphiti search "<query>" [--group <group>] [--limit N]

# List all knowledge in a category
guardkit graphiti list <category>    # features | adrs | patterns | constraints | all

# View knowledge graph status
guardkit graphiti status [--verbose]

# Seed/re-seed system context
guardkit graphiti seed [--force]
```

### Knowledge Groups

- **System**: product_knowledge, command_workflows, patterns, agents
- **Project**: project_overview, project_architecture, feature_specs
- **Decisions**: project_decisions, architecture_decisions
- **Learning**: task_outcomes, failure_patterns, successful_fixes
- **Turn States**: turn_states (AutoBuild turn tracking)

## Turn State Tracking

During `/feature-build`, GuardKit captures turn states for cross-turn learning:
- Player decisions/actions, Coach feedback, files modified
- Acceptance criteria status, blockers, progress summary

```bash
guardkit graphiti search "turn FEAT-XXX" --group turn_states
```

## Job-Specific Context Retrieval

Automatic context loading during task execution based on task type, complexity, and novelty. Categories: feature context, similar outcomes, patterns, architecture, warnings, domain knowledge.

Budget scales with complexity: 2000 tokens (simple) to 6000+ tokens (complex).

**See**: [Interactive Capture Guide](../../docs/guides/graphiti-knowledge-capture.md) | [Integration Guide](../../docs/guides/graphiti-integration-guide.md)
