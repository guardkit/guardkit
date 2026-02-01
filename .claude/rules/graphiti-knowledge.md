# Graphiti Knowledge Capture - Extended Documentation

This file contains detailed documentation for Graphiti integration with GuardKit. For quick reference, see the summary in the root CLAUDE.md.

## Interactive Knowledge Capture

GuardKit integrates with Graphiti to provide persistent knowledge capture across sessions. Use interactive knowledge capture to build comprehensive project understanding through guided Q&A.

### Starting a Capture Session

```bash
# Start interactive knowledge capture session
guardkit graphiti capture --interactive

# Focus on specific knowledge category
guardkit graphiti capture --interactive --focus project-overview
guardkit graphiti capture --interactive --focus architecture
guardkit graphiti capture --interactive --focus role-customization

# Limit number of questions
guardkit graphiti capture --interactive --max-questions 5
```

### Focus Categories

**Project Knowledge:**
- **project-overview**: Project purpose, target users, goals, problem statement
- **architecture**: High-level architecture, components, services, data flow
- **domain**: Domain-specific terminology, business rules
- **constraints**: Technical/business constraints, technologies to avoid
- **decisions**: Technology choices, rationale, trade-offs
- **goals**: Key objectives and success criteria

**AutoBuild Customization (FEAT-GR-004):**
- **role-customization**: Define what AI Player should ask about before implementing, what AI Coach should escalate to humans
- **quality-gates**: Customize coverage thresholds, architectural review scores
- **workflow-preferences**: Implementation mode preferences, autonomous turn limits

### Session Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Interactive Knowledge Capture                        │
│                                                                         │
│  1. Analyze existing knowledge (what we already know)                  │
│         ↓                                                               │
│  2. Identify gaps (what's missing or unclear)                          │
│         ↓                                                               │
│  3. Ask targeted questions                                              │
│         ↓                                                               │
│  4. Parse and structure answers                                         │
│         ↓                                                               │
│  5. Seed episodes to Graphiti                                          │
│         ↓                                                               │
│  6. Summarize what was learned                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### AutoBuild Customization Examples

**Role Customization:**
```bash
$ guardkit graphiti capture --interactive --focus role-customization

[1/3] ROLE_CUSTOMIZATION
Context: Prevents autonomous changes to sensitive areas

What tasks should the AI Player ALWAYS ask about before implementing?
Your answer: Database schema changes, auth/security changes, deployment configs

✓ Captured:
  - Player ask_before: Database schema changes...
  - Player ask_before: auth/security changes...
  - Player ask_before: deployment configs...
```

**Quality Gate Customization:**
```bash
$ guardkit graphiti capture --interactive --focus quality-gates

[1/2] QUALITY_GATES
Context: Customizes quality gate thresholds

What test coverage threshold is acceptable for this project?
Your answer: 85% for core business logic, 70% for utilities, 60% for scaffolding

✓ Captured:
  - Quality gate: coverage 85% for core business logic
  - Quality gate: coverage 70% for utilities
  - Quality gate: coverage 60% for scaffolding
```

**Workflow Preferences:**
```bash
$ guardkit graphiti capture --interactive --focus workflow-preferences

[1/2] WORKFLOW_PREFERENCES
Context: Clarifies implementation mode preferences

Should complex tasks use task-work mode or direct implementation?
Your answer: Use task-work for anything touching auth or payments, direct for UI changes

✓ Captured:
  - Workflow: task-work for auth and payment changes
  - Workflow: direct implementation for UI changes
```

### Benefits

1. **Persistent Memory**: Knowledge persists across Claude sessions
2. **AutoBuild Optimization**: Captured role constraints and quality gates guide autonomous workflows
3. **Reduced Ambiguity**: Fewer clarifying questions during task execution
4. **Team Knowledge**: Share project understanding across team members
5. **Context-Aware Planning**: `/feature-plan` queries Graphiti for related features and constraints

**See**: [FEAT-GR-004: Interactive Knowledge Capture](docs/research/graphiti-refinement/FEAT-GR-004-interactive-knowledge-capture.md) for complete technical details.

## Knowledge Query Commands

Query and inspect knowledge stored in Graphiti using CLI commands:

```bash
# Show specific knowledge by ID
guardkit graphiti show FEAT-SKEL-001
guardkit graphiti show ADR-001

# Search for knowledge
guardkit graphiti search "authentication patterns"
guardkit graphiti search "error handling" --group patterns --limit 20

# List all knowledge in a category
guardkit graphiti list features
guardkit graphiti list adrs
guardkit graphiti list patterns

# View knowledge graph status
guardkit graphiti status
guardkit graphiti status --verbose
```

### Command Details

**`show <knowledge_id>`** - Display detailed information about specific knowledge:
- Auto-detects knowledge type from ID (FEAT-*, ADR-*, etc.)
- Shows structured fields (title, description, status, etc.)
- Displays relevance score and metadata
- Example: `guardkit graphiti show FEAT-GR-005`

**`search <query>`** - Search across all knowledge:
- Full-text search with relevance scoring
- Optional `--group` filter (e.g., `--group feature_specs`)
- Optional `--limit` for result count (default: 10)
- Color-coded by relevance (green >0.8, yellow >0.5)
- Example: `guardkit graphiti search "authentication" --group patterns`

**`list <category>`** - List all items in a category:
- Categories: `features`, `adrs`, `patterns`, `constraints`, `all`
- Shows IDs and titles for all items
- Example: `guardkit graphiti list features`

**`status`** - Show knowledge graph health and statistics:
- Connection status (enabled/disabled)
- Episode counts by category
- Total knowledge count
- Use `--verbose` to show all groups (including empty)
- Example: `guardkit graphiti status --verbose`

### Knowledge Groups

- **System Knowledge**: product_knowledge, command_workflows, patterns, agents
- **Project Knowledge**: project_overview, project_architecture, feature_specs
- **Decisions**: project_decisions, architecture_decisions
- **Learning**: task_outcomes, failure_patterns, successful_fixes
- **Turn States**: turn_states (AutoBuild turn tracking)

**See**: [FEAT-GR-005: Knowledge Query Command](docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md) for complete technical details.

## Turn State Tracking (AutoBuild)

GuardKit captures turn states during `/feature-build` workflows for cross-turn learning.

### What Gets Captured

- Player decisions and actions
- Coach feedback and approval status
- Files modified during turn
- Acceptance criteria status
- Blockers encountered
- Progress summary

### Query Turn States

```bash
# View all recent turns
guardkit graphiti search "turn FEAT-XXX" --group turn_states

# View specific task turns
guardkit graphiti search "turn TASK-XXX" --group turn_states --limit 5
```

### Turn State Schema

| Field | Description |
|-------|-------------|
| `feature_id` | FEAT-XXX identifier |
| `task_id` | TASK-XXX being worked on |
| `turn_number` | Sequential turn number |
| `player_decision` | What Player implemented |
| `coach_decision` | APPROVED \| REJECTED \| FEEDBACK |
| `feedback_summary` | Key feedback points |
| `blockers_found` | List of blockers encountered |
| `files_modified` | List of changed files |
| `acceptance_criteria_status` | {criterion: verified\|pending\|rejected} |
| `mode` | FRESH_START \| RECOVERING_STATE \| CONTINUING_WORK |

### Benefits

- Turn N+1 knows what Turn N learned
- Prevents repeated mistakes
- Tracks progress across autonomous sessions
- Provides audit trail for feature development

## Job-Specific Context Retrieval

GuardKit automatically retrieves relevant context for each task based on its characteristics, ensuring you get exactly the knowledge you need without wasting tokens or missing critical information.

### How It Works

1. **Task Analysis**: Analyzes task type, complexity, novelty, and autobuild context
2. **Budget Calculation**: Dynamically allocates token budget (2000-6000+ tokens)
3. **Context Retrieval**: Queries Graphiti for relevant knowledge across categories
4. **Smart Filtering**: Applies relevance thresholds and deduplication
5. **Prompt Injection**: Formats context for optimal Claude understanding

### Context Categories

- **Feature Context**: Requirements and success criteria for parent feature
- **Similar Outcomes**: What worked for similar tasks (patterns, approaches)
- **Relevant Patterns**: Codebase patterns that apply to this task
- **Architecture Context**: How this fits into the overall system
- **Warnings**: Approaches to avoid based on past failures
- **Domain Knowledge**: Domain-specific terminology and concepts

### AutoBuild Additional Context

During `/feature-build`:
- **Role Constraints**: Player/Coach boundaries - what each can/cannot do
- **Quality Gate Configs**: Task-type specific thresholds (coverage, arch review)
- **Turn States**: Previous turn context for cross-turn learning
- **Implementation Modes**: Direct vs task-work guidance

### Budget Allocation

| Task Complexity | Base Budget | Context Focus |
|-----------------|-------------|---------------|
| Simple (1-3) | 2000 tokens | Patterns (30%), Outcomes (25%), Architecture (20%) |
| Medium (4-6) | 4000 tokens | Balanced allocation across all categories |
| Complex (7-10) | 6000 tokens | Architecture (25%), Patterns (25%), Outcomes (20%) |

### Budget Adjustments

- **First-of-type**: +30% (need more architecture understanding)
- **Refinement**: +20% (emphasize warnings and failures)
- **AutoBuild Turn >1**: +15% (load previous turn context)
- **AutoBuild with history**: +10% (cross-turn learning)

### Relevance Filtering

- Standard tasks: 0.6 threshold (high precision)
- First-of-type: 0.5 threshold (broader context)
- Refinement: 0.5 threshold (don't miss failure patterns)

### Performance

- Average retrieval: 600-800ms (concurrent queries)
- Cache hit rate: ~40% (repeated context cached)
- Budget utilization: 70-90% (efficient, rarely exceeds)
- Relevance scores: 0.65-0.85 average (high quality)

### Context in Action

```bash
# Automatic context loading during task execution
/task-work TASK-XXX
# → Loads similar outcomes, patterns, warnings, architecture

# AutoBuild with turn state context
/feature-build TASK-XXX
# → Turn 1: Loads role constraints, quality gates, implementation modes
# → Turn 2+: ALSO loads previous turn states (what was rejected, why)
```

### Transparency

Context retrieval is logged in task execution:
```
[INFO] Retrieved job-specific context (1850/2000 tokens)
  - Similar outcomes: 3 results (0.72 avg relevance)
  - Relevant patterns: 2 results (0.81 avg relevance)
  - Warnings: 1 result (0.68 relevance)
  - Architecture: 2 results (0.75 avg relevance)
```

### Troubleshooting Context Retrieval

| Issue | Solution |
|-------|----------|
| Context missing information | Check if knowledge seeded to Graphiti; verify task description specificity |
| Context irrelevant | Increase relevance threshold; review seeded knowledge quality |
| AutoBuild context missing | Verify `is_autobuild=True` in metadata; check role constraints seeded |
| Slow retrieval (>2s) | Check Neo4j performance; reduce context categories; verify network |

**See Also**:
- [FEAT-GR-006: Job-Specific Context Retrieval](docs/research/graphiti-refinement/FEAT-GR-006-job-specific-context.md) - Complete technical specification
- [Relevance Tuning Guide](docs/guides/graphiti-relevance-tuning.md) - Customizing relevance thresholds
- [Context Budget Optimization](docs/guides/graphiti-budget-optimization.md) - Fine-tuning budget allocation

## Troubleshooting Graphiti

### Command not found

```bash
# Verify Graphiti is enabled
guardkit graphiti status

# Check configuration
cat config/graphiti.yaml
```

### Connection errors

```bash
# Check Neo4j is running
docker ps | grep neo4j

# Verify connection settings in config/graphiti.yaml
# Default: neo4j://localhost:7687
```

### No results from queries

```bash
# Check if system context is seeded
guardkit graphiti status

# Seed system context if needed
guardkit graphiti seed

# Verify with test query
guardkit graphiti search "guardkit" --limit 5
```

### Empty turn states

```bash
# Turn states are only captured during /feature-build
# Run a feature-build task to generate turn states
guardkit autobuild task TASK-XXX

# Then query turn states
guardkit graphiti search "turn" --group turn_states
```

### Slow queries

- Reduce `--limit` value (default: 10)
- Use specific `--group` filters instead of searching all groups
- Check Neo4j resource allocation

### Stale knowledge

```bash
# Re-seed system context to update knowledge
guardkit graphiti seed --force

# Note: Force re-seeding clears previous system context
```
