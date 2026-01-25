# Graphiti + DeepAgents Integration Architecture for GuardKit

> **Purpose**: Define how FalkorDB with Graphiti temporal knowledge graph integrates with the DeepAgents-based GuardKit orchestration to provide job-specific context retrieval, learning from outcomes, and architecture knowledge management.
>
> **Date**: January 2025
> **Status**: Research & Design
> **Related**: `FalkorDB_and_Graphiti_for_Knowledge_Graph_MCP_Implementation.md`, `DeepAgents_Integration_Analysis.md`

---

## Executive Summary

This document explores integrating Graphiti's temporal knowledge graph with GuardKit's DeepAgents-based orchestration. The integration addresses three core needs identified by Kris Wong (ClosedLoop): **job-specific context retrieval** rather than loading everything into every prompt, **learning from implementation outcomes** to improve over time, and **architecture/system big picture knowledge** to inform task execution.

The key insight is that Graphiti's bi-temporal model (tracking when facts became true and when they were superseded) combined with `group_id` namespacing provides precisely the infrastructure needed for intelligent, context-aware agent orchestration.

### Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Episode granularity** | Task-level primary, selective turn-level | Turn-level only for complexity >= 7 or failures. Storage not a concern (~15MB/year). |
| **Template/Agent storage** | Hybrid (Markdown source, Graphiti query) | Markdown remains human-editable source of truth; Graphiti provides semantic queryability. |
| **Multi-project scope** | Per-project isolation | Keeps architecture simple. Cross-project sharing via `template-create` markdown export. |
| **Knowledge retention** | Rolling window (6 months default) | Simpler than importance-based pruning. Configurable per episode type. |
| **Conflict resolution** | Rebuild from Markdown | Markdown is authoritative. `guardkit knowledge rebuild` for manual resync. |
| **Embedding model** | OpenAI Phase 1, evaluate local Phase 2 | Start simple, optimize later. |
| **Context budget** | Dynamic based on task | More context for complex tasks, more warnings for refinements. |

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|  
| **Multi-project scope** | Per-project isolation | Keeps architecture simple. Cross-project sharing already solved by `template-create` exporting to markdown. |
| **Knowledge retention** | Rolling window (6 months default) | Simpler than importance-based pruning. Configurable per episode type (feature completions kept longer at 12 months, turn-level shorter at 3 months). |
| **Conflict resolution** | Rebuild from Markdown | Markdown is source of truth. Simple `guardkit knowledge rebuild` command for manual resync. |
| **Template/Agent storage** | Hybrid (Markdown source, Graphiti query) | Markdown remains human-editable and version-controlled; Graphiti provides semantic search for job-specific context. |
| **Episode granularity** | Task-level primary, selective turn-level | Turn-level only for complexity >= 7 or on failure. Storage is not a constraint (~15MB/year). |
| **Embedding model** | OpenAI Phase 1, evaluate local Phase 2 | Start simple with `text-embedding-3-small`, evaluate `nomic-embed` via Ollama for cost optimization. |

### The Elegant Simplicity

The decision to use `template-create` for cross-project sharing is particularly elegant because:

1. **No new mechanisms needed** - existing tooling handles the export
2. **Human-in-the-loop** - you decide what to share by copying template folders
3. **Version control friendly** - shared patterns are just markdown files in git
4. **Graphiti stays project-scoped** - simpler deployment, no multi-tenancy complexity

---

## Table of Contents

1. [Integration Architecture Overview](#integration-architecture-overview)
2. [Command-Specific Integration Points](#command-specific-integration-points)
3. [Episode Granularity Analysis](#episode-granularity-analysis)
4. [Template and Agent Knowledge Storage](#template-and-agent-knowledge-storage)
5. [Group ID Schema Design](#group-id-schema-design)
6. [Context Window Budget Strategy](#context-window-budget-strategy)
7. [Embedding Model Considerations](#embedding-model-considerations)
8. [Architecture Knowledge Population](#architecture-knowledge-population)
9. [Implementation Phases](#implementation-phases)
10. [Open Questions and Decisions](#open-questions-and-decisions)

---

## Integration Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AutoBuild Orchestrator                             │
│                      (create_deep_agent)                                │
├─────────────────────────────────────────────────────────────────────────┤
│  DeepAgents Middleware Stack:                                           │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ TodoListMiddleware          (planning/task tracking)            │   │
│  │ FilesystemMiddleware        (ephemeral coordination)            │   │
│  │   /coordination/player/     ← Current task state                │   │
│  │   /coordination/coach/      ← Review feedback                   │   │
│  │ SubAgentMiddleware          (Player/Coach delegation)           │   │
│  │ SummarizationMiddleware     (context at 170K tokens)            │   │
│  │ HumanInTheLoopMiddleware    (approval gates)                    │   │
│  │ AdversarialLoopMiddleware   (Player↔Coach loop - CUSTOM)        │   │
│  │ GraphitiMiddleware          (persistent learning - NEW)         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 FalkorDB + Graphiti                              │   │
│  │   docker run falkordb/graphiti-knowledge-graph-mcp              │   │
│  │                                                                  │   │
│  │   Storage:                                                       │   │
│  │   ├── Episodes (task outcomes, review findings, feature learnings)│  │
│  │   ├── Entities (services, patterns, agents, templates)          │   │
│  │   └── Relationships (dependencies, patterns→tasks, etc.)        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   /task-    │     │   /task-    │     │   /task-    │     │   /task-    │
│    work     │────▶│   review    │────▶│   refine    │────▶│  complete   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           Graphiti Episodes                              │
│                                                                          │
│  task_start_episode     review_decision     refine_attempt     task_     │
│  ├── context retrieved  ├── findings        ├── failure cause  outcome  │
│  ├── approach planned   ├── recommendations ├── fix attempted  ├── final│
│  └── patterns matched   └── decision made   └── result         └── state│
│                              (Accept/Impl)                               │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         Queryable Knowledge                              │
│                                                                          │
│  "What worked for similar authentication tasks?"                         │
│  "What review findings led to successful implementations?"               │
│  "What patterns does this codebase use for error handling?"              │
│  "How did we resolve circular dependencies last time?"                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Command-Specific Integration Points

### `/task-work TASK-XXX`

**Pre-execution Context Retrieval:**

```python
async def retrieve_task_context(task: Task) -> TaskContext:
    """Retrieve job-specific context before task execution."""
    
    results = await graphiti.search(
        query=task.description,
        group_ids=[
            f"task_{task.id}",                    # Previous work on this task
            f"feature_{task.parent_feature_id}", # Parent feature context
            "project_architecture",               # System architecture knowledge
            "successful_patterns",                # What worked for similar tasks
            f"stack_{task.tech_stack}"           # Stack-specific patterns
        ],
        num_results=10
    )
    
    return TaskContext(
        similar_task_outcomes=filter_by_type(results, "task_outcome"),
        relevant_patterns=filter_by_type(results, "pattern"),
        architecture_context=filter_by_type(results, "architecture"),
        warnings=filter_by_type(results, "failure_pattern")
    )
```

**Post-completion Episode Capture:**

```python
async def capture_task_outcome(task: Task, outcome: TaskOutcome):
    """Capture task completion as episode for future learning."""
    
    episode = {
        "task_id": task.id,
        "feature_id": task.parent_feature_id,
        "description": task.description,
        "tech_stack": task.tech_stack,
        "approach_used": outcome.selected_approach,
        "player_turns": outcome.turn_count,
        "coach_feedback_summary": outcome.feedback_themes,
        "patterns_applied": outcome.detected_patterns,
        "tests_generated": outcome.test_count,
        "coverage_achieved": outcome.coverage_percentage,
        "issues_encountered": outcome.issues,
        "resolution_strategies": outcome.resolutions,
        "complexity_estimate": task.estimated_complexity,
        "actual_complexity": outcome.actual_complexity,
        "duration_minutes": outcome.duration,
        "final_status": outcome.status  # success | failed | escalated
    }
    
    await graphiti.add_episode(
        name=f"task_outcome_{task.id}",
        episode_body=json.dumps(episode),
        source=EpisodeType.json,
        reference_time=datetime.now(timezone.utc),
        group_id="task_outcomes"
    )
```

### `/task-review TASK-XXX`

The review command presents findings and recommendations with a human decision checkpoint. **This is a critical learning moment** - the user's decision (Accept, Implement, Skip) combined with the findings creates valuable knowledge.

**Review Decision Episode Capture:**

```python
async def capture_review_decision(
    task: Task,
    findings: ReviewFindings,
    decision: str,  # "accept" | "implement" | "skip"
    created_tasks: list[str] = None  # Task IDs if decision was "implement"
):
    """Capture review findings and decision as episode."""
    
    episode = {
        "task_id": task.id,
        "feature_id": task.parent_feature_id,
        "review_type": findings.review_type,  # code_review | architectural | test_coverage
        
        # Findings detail
        "findings_summary": findings.summary,
        "recommendations": findings.recommendations,
        "severity_distribution": {
            "critical": len([f for f in findings.items if f.severity == "critical"]),
            "major": len([f for f in findings.items if f.severity == "major"]),
            "minor": len([f for f in findings.items if f.severity == "minor"]),
            "suggestion": len([f for f in findings.items if f.severity == "suggestion"])
        },
        "categories": findings.categories,  # e.g., ["error_handling", "testing", "performance"]
        
        # Decision context
        "decision": decision,
        "decision_rationale": findings.decision_context,
        
        # If "implement" was chosen
        "spawned_tasks": created_tasks or [],
        "implementation_scope": findings.implementation_scope if decision == "implement" else None,
        
        # Meta
        "review_duration_seconds": findings.duration,
        "reviewer_confidence": findings.confidence_score
    }
    
    await graphiti.add_episode(
        name=f"review_decision_{task.id}_{datetime.now().isoformat()}",
        episode_body=json.dumps(episode),
        source=EpisodeType.json,
        reference_time=datetime.now(timezone.utc),
        group_id="review_decisions"
    )
```

**Learning from Review Patterns:**

When a user chooses "Implement" to create tasks from recommendations, this creates a traceable chain:

```
Review Finding → Implement Decision → Created Tasks → Task Outcomes
```

Future reviews can query: "For findings like X, what implementation approach worked?"

```python
async def get_similar_review_patterns(finding_type: str, category: str):
    """Query for how similar findings were resolved."""
    
    results = await graphiti.search(
        query=f"{finding_type} {category} implement resolution",
        group_ids=["review_decisions", "task_outcomes"],
        num_results=10
    )
    
    # Graphiti's temporal model lets us trace:
    # 1. Reviews with similar findings
    # 2. Whether "implement" was chosen
    # 3. What tasks were created
    # 4. Whether those tasks succeeded
    
    return analyze_resolution_patterns(results)
```

### `/task-refine TASK-XXX`

Refinement occurs when initial attempts fail. **This is where failure patterns become invaluable.**

**Pre-refinement Context:**

```python
async def retrieve_refinement_context(task: Task, failure: FailureContext):
    """Retrieve context specifically for refinement attempts."""
    
    # Query for similar failures and their resolutions
    results = await graphiti.search(
        query=f"{failure.error_type} {failure.description}",
        group_ids=[
            "failed_approaches",        # What didn't work
            "successful_fixes",         # How similar failures were resolved
            f"task_{task.id}",          # This task's history
            f"stack_{task.tech_stack}"  # Stack-specific failure patterns
        ],
        num_results=10
    )
    
    return RefinementContext(
        similar_failures=filter_successful_resolutions(results),
        anti_patterns=filter_repeated_failures(results),
        suggested_approaches=derive_suggestions(results)
    )
```

**Refinement Attempt Episode:**

```python
async def capture_refinement_attempt(
    task: Task,
    attempt_number: int,
    failure_context: FailureContext,
    fix_attempted: str,
    result: str  # "resolved" | "failed" | "partial"
):
    """Capture refinement attempt for failure pattern learning."""
    
    episode = {
        "task_id": task.id,
        "attempt_number": attempt_number,
        "failure_type": failure_context.error_type,
        "failure_description": failure_context.description,
        "stack_trace_signature": failure_context.stack_signature,  # Anonymized
        "fix_attempted": fix_attempted,
        "fix_category": categorize_fix(fix_attempted),
        "result": result,
        "time_to_fix_seconds": failure_context.resolution_time
    }
    
    # Use different group based on outcome
    group = "successful_fixes" if result == "resolved" else "failed_approaches"
    
    await graphiti.add_episode(
        name=f"refinement_{task.id}_{attempt_number}",
        episode_body=json.dumps(episode),
        source=EpisodeType.json,
        reference_time=datetime.now(timezone.utc),
        group_id=group
    )
```

### `/task-complete TASK-XXX`

Final task completion captures the holistic outcome.

```python
async def capture_task_completion(task: Task, completion: CompletionContext):
    """Capture final task state as comprehensive episode."""
    
    episode = {
        "task_id": task.id,
        "feature_id": task.parent_feature_id,
        "description": task.description,
        
        # Journey summary
        "total_work_sessions": completion.work_session_count,
        "total_review_cycles": completion.review_count,
        "total_refinement_attempts": completion.refinement_count,
        
        # Quality metrics
        "final_test_count": completion.test_count,
        "final_coverage": completion.coverage,
        "architectural_score": completion.arch_score,
        
        # Patterns learned
        "patterns_that_worked": completion.successful_patterns,
        "patterns_that_failed": completion.failed_patterns,
        "unexpected_challenges": completion.surprises,
        
        # Time tracking
        "estimated_hours": task.estimated_hours,
        "actual_hours": completion.actual_hours,
        "estimation_accuracy": completion.actual_hours / task.estimated_hours if task.estimated_hours else None,
        
        # Files touched (for architecture learning)
        "files_created": completion.files_created,
        "files_modified": completion.files_modified,
        "dependencies_added": completion.new_dependencies
    }
    
    await graphiti.add_episode(
        name=f"task_completion_{task.id}",
        episode_body=json.dumps(episode),
        source=EpisodeType.json,
        reference_time=datetime.now(timezone.utc),
        group_id="task_completions"
    )
```

### `/feature-plan "description"`

Feature planning benefits from architecture context and decomposition patterns.

**Pre-planning Context:**

```python
async def retrieve_feature_planning_context(description: str, detected_stack: str):
    """Retrieve context for feature planning."""
    
    results = await graphiti.search(
        query=description,
        group_ids=[
            "project_architecture",      # Current system architecture
            "service_dependencies",      # Known dependencies
            "feature_decomposition",     # How similar features were broken down
            f"stack_{detected_stack}"    # Stack-specific patterns
        ],
        num_results=15
    )
    
    return PlanningContext(
        architecture=extract_architecture(results),
        relevant_services=extract_services(results),
        decomposition_patterns=extract_decomposition_patterns(results),
        complexity_indicators=extract_complexity_hints(results)
    )
```

### `/feature-complete` (Proposed)

When a feature is completed (all tasks done, acceptance criteria met), capture the full journey:

```python
async def capture_feature_completion(feature: Feature, completion: FeatureCompletion):
    """Capture feature completion as comprehensive learning episode."""
    
    episode = {
        "feature_id": feature.id,
        "title": feature.title,
        "description": feature.description,
        
        # Task decomposition effectiveness
        "planned_task_count": feature.original_task_count,
        "actual_task_count": completion.final_task_count,
        "task_additions": completion.tasks_added,
        "task_removals": completion.tasks_removed,
        "decomposition_accuracy": feature.original_task_count / completion.final_task_count,
        
        # Execution summary
        "total_work_hours": completion.total_hours,
        "estimated_hours": feature.estimated_hours,
        "calendar_days": completion.calendar_days,
        
        # Quality outcomes
        "acceptance_criteria_met": completion.criteria_status,
        "review_cycles_total": completion.total_reviews,
        "refinement_cycles_total": completion.total_refinements,
        
        # Architecture impact
        "architecture_changes": completion.arch_changes,
        "new_services_created": completion.new_services,
        "dependencies_introduced": completion.new_deps,
        
        # Lessons learned
        "what_worked": completion.successes,
        "what_struggled": completion.challenges,
        "recommendations_for_similar": completion.recommendations
    }
    
    await graphiti.add_episode(
        name=f"feature_completion_{feature.id}",
        episode_body=json.dumps(episode),
        source=EpisodeType.json,
        reference_time=datetime.now(timezone.utc),
        group_id="feature_completions"
    )
```

---

## Episode Granularity Analysis

### The Trade-off

| Granularity | Storage | Query Speed | Learning Value | Recommendation |
|-------------|---------|-------------|----------------|----------------|
| **Turn-level** | High | Slower | Detailed patterns | ⚠️ Consider for specific cases |
| **Task-level** | Medium | Good | Solid patterns | ✅ Primary approach |
| **Feature-level** | Low | Fast | High-level trends | ✅ Always capture |

### Recommended Hybrid Approach

**Always Capture (Task-level):**
- Task outcomes (`/task-complete`)
- Review decisions with findings (`/task-review`)
- Refinement attempts (`/task-refine`)
- Feature completions (`/feature-complete`)

**Selectively Capture (Turn-level):**
- Only when task complexity > threshold (e.g., complexity >= 7)
- Only for failed tasks (to learn from failure patterns)
- Only when explicitly enabled via config

```python
class EpisodeGranularityConfig:
    """Configuration for episode capture granularity."""
    
    # Always capture these
    task_outcomes: bool = True
    review_decisions: bool = True
    feature_completions: bool = True
    
    # Selective turn-level capture
    turn_level_threshold: int = 7  # Complexity threshold
    turn_level_on_failure: bool = True
    turn_level_explicit: bool = False  # User can enable per-task
```

**Turn-level Episode Structure (when captured):**

```python
async def capture_turn_episode(
    task: Task,
    turn: int,
    role: str,  # "player" | "coach"
    action_summary: str,
    outcome: str
):
    """Capture individual turn for detailed pattern learning."""
    
    episode = {
        "task_id": task.id,
        "turn_number": turn,
        "role": role,
        "action_type": categorize_action(action_summary),
        "action_summary": action_summary,
        "outcome": outcome,
        "files_touched": extract_files(action_summary),
        "patterns_used": detect_patterns(action_summary)
    }
    
    await graphiti.add_episode(
        name=f"turn_{task.id}_{turn}_{role}",
        episode_body=json.dumps(episode),
        source=EpisodeType.json,
        reference_time=datetime.now(timezone.utc),
        group_id=f"task_{task.id}_turns"  # Task-scoped turns
    )
```

### Storage Estimation

Assuming:
- 100 tasks/month
- Average 3 reviews per task
- 20% tasks need refinement (avg 2 attempts)
- 10 features/month

**Task-level only:**
```
Episodes/month = 100 tasks + 300 reviews + 40 refinements + 10 features = 450 episodes
Average episode size: ~2KB
Monthly storage: ~900KB
Annual storage: ~11MB
```

**With selective turn-level (20% of tasks, avg 4 turns):**
```
Additional: 20 tasks × 4 turns × 2 (player+coach) = 160 turn episodes
Additional storage: ~320KB/month
Annual additional: ~4MB
```

**Conclusion:** Storage is not a significant concern. The decision should be based on learning value, not storage constraints.

---

## Template and Agent Knowledge Storage

### The Question

Should `/template-create` and `/agent-enhance` outputs go into Graphiti or remain as markdown files?

### Analysis

| Aspect | Markdown Files | Database/SQLite | Graphiti |
|--------|---------------|-----------------|----------|
| **Human readability** | ✅ Excellent | ❌ Poor | ⚠️ Requires tooling |
| **Version control** | ✅ Native git | ❌ Requires export | ⚠️ Requires export |
| **Queryable relationships** | ❌ Manual | ⚠️ With joins | ✅ Native traversal |
| **Temporal tracking** | ❌ Git history only | ⚠️ Manual | ✅ Native bi-temporal |
| **Job-specific retrieval** | ❌ Load all or parse | ⚠️ SQL queries | ✅ Semantic search |
| **Pattern discovery** | ❌ Manual | ⚠️ SQL analytics | ✅ Graph traversal |

### Recommendation: Hybrid Approach

**Keep in Markdown (source of truth):**
- Agent files (`.claude/agents/*.md`)
- Template definitions (`.claude/templates/*/`)
- CLAUDE.md and configuration

**Mirror to Graphiti (queryable layer):**
- Agent capabilities and specializations
- Pattern definitions and relationships
- Template-to-pattern mappings
- Success rates and usage statistics

```
┌─────────────────────────────────────────────────────────────────┐
│                     Source of Truth                             │
│                     (Markdown Files)                            │
│                                                                 │
│  .claude/agents/                                                │
│  ├── python-specialist.md      ← Human-editable                │
│  ├── react-specialist.md       ← Version controlled            │
│  └── requirements-analyst.md   ← Full documentation            │
│                                                                 │
│  .claude/templates/                                             │
│  └── my-template/                                               │
│      ├── patterns.md           ← Pattern definitions            │
│      └── stack-config.yaml     ← Stack configuration            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Sync on template-create / agent-enhance
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Queryable Layer                             │
│                     (Graphiti)                                  │
│                                                                 │
│  Entities:                                                      │
│  ├── Agent(name, capabilities, tech_stack, success_rate)       │
│  ├── Pattern(name, category, when_to_use, examples)            │
│  ├── Template(name, stack, agents, patterns)                   │
│  └── Service(name, dependencies, patterns_used)                │
│                                                                 │
│  Relationships:                                                 │
│  ├── Agent -[SPECIALIZES_IN]-> Pattern                         │
│  ├── Template -[USES]-> Agent                                  │
│  ├── Pattern -[APPLIES_TO]-> TechStack                         │
│  └── Task -[USED_PATTERN]-> Pattern (from outcomes)            │
└─────────────────────────────────────────────────────────────────┘
```

### Entity Definitions

```python
from graphiti_core.nodes import EntityModel
from pydantic import Field

class AgentEntity(EntityModel):
    """A GuardKit agent definition."""
    name: str = Field(description="Agent identifier")
    display_name: str = Field(description="Human-readable name")
    tech_stack: str = Field(description="Primary technology stack")
    capabilities: str = Field(description="What this agent can do")
    specializations: str = Field(description="Specific areas of expertise")
    invocation_count: int = Field(default=0, description="Times invoked")
    success_rate: float = Field(default=0.0, description="Success percentage")

class PatternEntity(EntityModel):
    """A codebase pattern extracted from templates."""
    name: str = Field(description="Pattern identifier")
    category: str = Field(description="Category: error_handling, data_access, etc.")
    description: str = Field(description="What this pattern does")
    when_to_use: str = Field(description="Conditions for applying this pattern")
    code_example: str = Field(description="Representative code snippet")
    tech_stack: str = Field(description="Applicable technology stack")
    usage_count: int = Field(default=0, description="Times successfully used")

class TemplateEntity(EntityModel):
    """A GuardKit template definition."""
    name: str = Field(description="Template identifier")
    tech_stack: str = Field(description="Primary stack (python, react, etc.)")
    description: str = Field(description="What this template provides")
    patterns_count: int = Field(description="Number of patterns defined")
    agents_count: int = Field(description="Number of agents generated")
    created_from: str = Field(description="Source codebase description")
```

### Sync Process

```python
async def sync_template_to_graphiti(template_path: Path, graphiti: Graphiti):
    """Sync template definition to Graphiti for querying."""
    
    # Parse template markdown and config
    template_data = parse_template(template_path)
    
    # Create/update template entity
    await graphiti.add_episode(
        name=f"template_definition_{template_data.name}",
        episode_body=json.dumps({
            "entity_type": "template",
            "name": template_data.name,
            "tech_stack": template_data.stack,
            "description": template_data.description,
            "patterns": [p.name for p in template_data.patterns],
            "agents": [a.name for a in template_data.agents]
        }),
        source=EpisodeType.json,
        group_id="template_definitions"
    )
    
    # Sync each pattern
    for pattern in template_data.patterns:
        await graphiti.add_episode(
            name=f"pattern_{template_data.name}_{pattern.name}",
            episode_body=json.dumps({
                "entity_type": "pattern",
                "name": pattern.name,
                "category": pattern.category,
                "description": pattern.description,
                "when_to_use": pattern.when_to_use,
                "code_example": pattern.example,
                "tech_stack": template_data.stack,
                "template": template_data.name
            }),
            source=EpisodeType.json,
            group_id=f"patterns_{template_data.stack}"
        )
    
    # Sync each agent
    for agent in template_data.agents:
        await graphiti.add_episode(
            name=f"agent_{agent.name}",
            episode_body=json.dumps({
                "entity_type": "agent",
                "name": agent.name,
                "display_name": agent.display_name,
                "tech_stack": template_data.stack,
                "capabilities": agent.capabilities,
                "specializations": agent.specializations,
                "template": template_data.name
            }),
            source=EpisodeType.json,
            group_id="agent_definitions"
        )
```

### Querying Template/Agent Knowledge

```python
async def select_agent_for_task(task: Task) -> AgentRecommendation:
    """Use Graphiti to recommend best agent for task."""
    
    results = await graphiti.search(
        query=f"{task.description} {task.tech_stack}",
        group_ids=[
            "agent_definitions",
            f"patterns_{task.tech_stack}",
            "task_outcomes"  # Include historical success data
        ],
        num_results=10
    )
    
    # Graphiti's semantic search finds relevant agents
    # Combined with historical task outcomes, we can rank by success rate
    
    return rank_agents_by_fit(results, task)

async def get_relevant_patterns(task: Task) -> list[Pattern]:
    """Retrieve patterns relevant to the current task."""
    
    results = await graphiti.search(
        query=f"{task.type} {task.description}",
        group_ids=[
            f"patterns_{task.tech_stack}",
            "successful_patterns"  # Patterns that worked in similar tasks
        ],
        num_results=5
    )
    
    return extract_patterns(results)
```

---

## Group ID Schema Design

### Proposed Taxonomy

```
group_ids/
├── task_outcomes              # All task completion episodes
├── review_decisions           # All review finding/decision episodes
├── successful_fixes           # Refinements that resolved issues
├── failed_approaches          # Approaches that didn't work
├── task_{TASK-XXX}_turns      # Turn-level episodes for specific task
│
├── feature_completions        # Feature-level outcomes
├── feature_decomposition      # How features were broken into tasks
│
├── project_architecture       # System architecture knowledge
├── service_dependencies       # Service relationship knowledge
│
├── template_definitions       # Template entity definitions
├── agent_definitions          # Agent entity definitions
├── patterns_{stack}           # Patterns by technology stack
│   ├── patterns_python
│   ├── patterns_react
│   ├── patterns_dotnet
│   └── patterns_maui
│
├── stack_{stack}              # Stack-specific knowledge
│   ├── stack_python
│   ├── stack_react
│   └── ...
│
└── project_{project_id}       # Project-scoped knowledge (multi-project)
```

### Query Patterns

```python
# Job-specific context for a Python task in feature FEAT-001
group_ids = [
    "task_outcomes",           # General task learning
    "patterns_python",         # Python-specific patterns
    "stack_python",            # Python stack knowledge
    f"feature_FEAT-001",       # Feature-specific context
    "project_architecture"     # System architecture
]

# Refinement context for a test failure
group_ids = [
    "failed_approaches",       # What didn't work
    "successful_fixes",        # What resolved similar issues
    f"task_{task_id}_turns",   # This task's turn history (if captured)
    f"stack_{stack}"           # Stack-specific failure patterns
]

# Feature planning context
group_ids = [
    "project_architecture",
    "service_dependencies",
    "feature_completions",     # How similar features went
    "feature_decomposition"    # Decomposition patterns
]
```

---

## Context Window Budget Strategy

Following Kris Wong's principle: **optimize context for specific jobs at specific moments**.

### Budget Allocation

```python
class ContextBudget:
    """Token budget allocation for context injection."""
    
    # Total budget for injected context (conservative)
    total_tokens: int = 4000
    
    # Allocation by category
    allocation = {
        "similar_outcomes": 0.30,      # 1200 tokens - What worked before
        "relevant_patterns": 0.25,     # 1000 tokens - Applicable patterns
        "architecture": 0.20,          # 800 tokens - System context
        "warnings": 0.15,              # 600 tokens - What to avoid
        "meta": 0.10                   # 400 tokens - Task-specific history
    }
```

### Context Injection Strategy

```python
async def build_task_context(task: Task, budget: ContextBudget) -> str:
    """Build context string within budget constraints."""
    
    context_sections = []
    
    # 1. Similar successful outcomes (highest priority)
    similar = await graphiti.search(
        query=task.description,
        group_ids=["task_outcomes", "successful_patterns"],
        num_results=3
    )
    similar_text = summarize_within_budget(
        similar,
        budget.total_tokens * budget.allocation["similar_outcomes"]
    )
    if similar_text:
        context_sections.append(f"## Similar Task Patterns\n{similar_text}")
    
    # 2. Relevant patterns from template
    patterns = await graphiti.search(
        query=f"{task.type} {task.tech_stack}",
        group_ids=[f"patterns_{task.tech_stack}"],
        num_results=3
    )
    patterns_text = summarize_within_budget(
        patterns,
        budget.total_tokens * budget.allocation["relevant_patterns"]
    )
    if patterns_text:
        context_sections.append(f"## Codebase Patterns\n{patterns_text}")
    
    # 3. Architecture context
    arch = await graphiti.search(
        query=task.description,
        group_ids=["project_architecture", "service_dependencies"],
        num_results=2
    )
    arch_text = summarize_within_budget(
        arch,
        budget.total_tokens * budget.allocation["architecture"]
    )
    if arch_text:
        context_sections.append(f"## Architecture Context\n{arch_text}")
    
    # 4. Warning patterns (things that failed)
    warnings = await graphiti.search(
        query=task.description,
        group_ids=["failed_approaches"],
        num_results=2
    )
    warnings_text = summarize_within_budget(
        warnings,
        budget.total_tokens * budget.allocation["warnings"]
    )
    if warnings_text:
        context_sections.append(f"## Patterns to Avoid\n{warnings_text}")
    
    return "\n\n".join(context_sections)
```

### Dynamic Budget Adjustment

```python
class DynamicBudget:
    """Adjust budget based on task characteristics."""
    
    @staticmethod
    def for_task(task: Task) -> ContextBudget:
        budget = ContextBudget()
        
        # New task type - more architecture context
        if task.is_first_of_type:
            budget.allocation["architecture"] = 0.35
            budget.allocation["similar_outcomes"] = 0.20
        
        # Refinement attempt - emphasize warnings
        if task.refinement_attempt > 0:
            budget.allocation["warnings"] = 0.35
            budget.allocation["similar_outcomes"] = 0.40
            budget.allocation["patterns"] = 0.10
        
        # High complexity - more context overall
        if task.complexity >= 7:
            budget.total_tokens = 6000
        
        return budget
```

---

## Embedding Model Considerations

### Options

| Model | Latency | Cost | Quality | Privacy |
|-------|---------|------|---------|---------|
| **OpenAI text-embedding-3-small** | ~100ms | $0.02/1M | Good | Cloud |
| **OpenAI text-embedding-3-large** | ~150ms | $0.13/1M | Better | Cloud |
| **Cohere embed-v3** | ~80ms | $0.10/1M | Good | Cloud |
| **sentence-transformers (local)** | ~50ms | Free | Good | ✅ Local |
| **nomic-embed (local via Ollama)** | ~30ms | Free | Good | ✅ Local |

### Recommendation

**Phase 1 (MVP):** Use OpenAI `text-embedding-3-small`
- Simplest integration (Graphiti default)
- Good quality for code/technical content
- Low cost at GuardKit's scale

**Phase 2 (Cost optimization):** Evaluate local embeddings
- `nomic-embed` via Ollama for zero marginal cost
- Requires embedding model download (~500MB)
- May need evaluation on code-specific benchmarks

### Configuration

```python
# graphiti_config.py

class GraphitiConfig:
    # Phase 1: OpenAI (default)
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    
    # Phase 2: Local option
    # embedding_provider: str = "ollama"
    # embedding_model: str = "nomic-embed-text"
    # ollama_base_url: str = "http://localhost:11434"
```

---

## Architecture Knowledge Population

### Initial Population Strategy

When GuardKit is initialized in a project, populate the knowledge graph with:

1. **Template patterns** (from `/template-create` output)
2. **Agent definitions** (from `/agent-enhance` output)
3. **Codebase structure** (from static analysis)

```python
async def populate_initial_knowledge(project_path: Path, graphiti: Graphiti):
    """Populate knowledge graph on guardkit init."""
    
    # 1. Parse existing templates
    templates_path = project_path / ".claude" / "templates"
    for template_dir in templates_path.iterdir():
        if template_dir.is_dir():
            await sync_template_to_graphiti(template_dir, graphiti)
    
    # 2. Parse existing agents
    agents_path = project_path / ".claude" / "agents"
    for agent_file in agents_path.glob("*.md"):
        await sync_agent_to_graphiti(agent_file, graphiti)
    
    # 3. Analyze codebase structure (lightweight)
    structure = analyze_codebase_structure(project_path)
    await graphiti.add_episode(
        name="project_structure",
        episode_body=json.dumps({
            "entity_type": "architecture",
            "services": structure.services,
            "entry_points": structure.entry_points,
            "dependencies": structure.external_deps,
            "tech_stack": structure.detected_stack
        }),
        source=EpisodeType.json,
        group_id="project_architecture"
    )
```

### Incremental Updates

As templates and agents are modified:

```python
# In template-create command
async def post_template_create(template_path: Path):
    """Hook after template-create completes."""
    graphiti = get_graphiti_client()
    await sync_template_to_graphiti(template_path, graphiti)

# In agent-enhance command
async def post_agent_enhance(agent_path: Path):
    """Hook after agent-enhance completes."""
    graphiti = get_graphiti_client()
    await sync_agent_to_graphiti(agent_path, graphiti)
```

### Architecture Evolution Tracking

Graphiti's temporal model tracks how architecture evolves:

```python
async def record_architecture_change(change: ArchitectureChange):
    """Record architectural change with temporal context."""
    
    await graphiti.add_episode(
        name=f"arch_change_{change.timestamp.isoformat()}",
        episode_body=json.dumps({
            "change_type": change.type,  # "service_added", "dependency_changed", etc.
            "affected_services": change.services,
            "reason": change.reason,
            "task_id": change.triggering_task,
            "feature_id": change.triggering_feature
        }),
        source=EpisodeType.json,
        reference_time=change.timestamp,
        group_id="project_architecture"
    )
```

Query architecture at a point in time:
```python
# "What did the architecture look like before feature X?"
results = await graphiti.search(
    query="architecture services dependencies",
    group_ids=["project_architecture"],
    # Graphiti's temporal model filters by valid_at
)
```

---

## Implementation Phases

### Phase 1: Foundation (3-4 days)

**Goal:** Basic integration with task outcomes and review decisions.

**Deliverables:**
1. FalkorDB + Graphiti Docker setup
2. `GraphitiMiddleware` skeleton
3. Task outcome capture on `/task-complete`
4. Review decision capture on `/task-review`
5. Basic context retrieval for `/task-work`

**Configuration:**
```yaml
# guardkit.yaml
knowledge_graph:
  enabled: true
  provider: "graphiti"
  connection:
    host: "localhost"
    port: 6379
  embedding:
    provider: "openai"
    model: "text-embedding-3-small"
```

### Phase 2: Template/Agent Integration (2-3 days)

**Goal:** Sync template and agent knowledge for job-specific context.

**Deliverables:**
1. Template sync on `/template-create`
2. Agent sync on `/agent-enhance`
3. Pattern retrieval in task context
4. Agent selection recommendations

### Phase 3: Advanced Learning (3-4 days)

**Goal:** Full learning loop with refinement patterns and failure tracking.

**Deliverables:**
1. Refinement attempt tracking
2. Failure pattern queries
3. Success rate tracking for patterns/agents
4. Feature completion episodes
5. Turn-level capture (selective)

### Phase 4: Optimization (2-3 days)

**Goal:** Performance tuning and context budget optimization.

**Deliverables:**
1. Context budget tuning
2. Query optimization
3. Local embedding evaluation
4. Caching layer for frequent queries

---

## Open Questions and Decisions

### Decisions Needed

| Question | Options | Recommendation | Status |
|----------|---------|----------------|--------|
| Turn-level granularity | Always / Never / Selective | Selective (complexity >= 7, on failure) | ✅ Decided |
| Template storage | Markdown only / Graphiti only / Hybrid | Hybrid (Markdown source, Graphiti query) | ✅ Decided |
| Embedding model | OpenAI / Local | OpenAI Phase 1, evaluate local Phase 2 | ✅ Decided |
| Context budget | Fixed / Dynamic | Dynamic based on task characteristics | ✅ Decided |
| Multi-project scope | Shared / Isolated | Per-project isolation (use template-create for sharing) | ✅ Decided |
| Knowledge retention | Forever / Rolling / Importance-based | Rolling window (6 months default, configurable) | ✅ Decided |
| Conflict resolution | Graphiti wins / Markdown wins | Rebuild from Markdown | ✅ Decided |

### Resolved Questions

1. **Multi-project scope**: ✅ **Per-project isolation**
   - Each project maintains its own Graphiti instance/namespace
   - Cross-project sharing via existing mechanisms: `/template-create` exports patterns to markdown, which can be copied to other projects
   - This keeps the architecture simple and leverages existing tooling
   - Future consideration: explicit export/import commands if demand emerges

2. **Knowledge retention**: ✅ **Rolling window (6 months default)**
   - Simpler than importance-based pruning (hard to define "importance")
   - Graphiti's temporal model already handles invalidation via `invalid_at`
   - Configuration option for retention period:
     ```yaml
     knowledge_graph:
       retention:
         task_outcomes: 6_months
         review_decisions: 6_months
         feature_completions: 12_months  # Keep longer for high-level patterns
         turn_level: 3_months            # Shorter for detailed data
     ```
   - Retention job runs periodically to prune old episodes
   - Note: "Old" means episodes where `created_at` exceeds retention period AND no recent references

3. **Conflict resolution**: ✅ **Rebuild from Markdown**
   - Markdown files are authoritative source of truth
   - On detected divergence, Graphiti layer is rebuilt from markdown
   - Sync validation on `guardkit init` and optionally on each command
   - Simple `guardkit knowledge rebuild` command for manual resync

### Open Questions

1. **Privacy/PII**: Should we sanitize episodes?
   - Remove specific file paths? Variable names?
   - Anonymize error messages?
   - Consider for enterprise deployment

---

## References

- [FalkorDB and Graphiti Research Document](../../../project-knowledge/FalkorDB_and_Graphiti_for_Knowledge_Graph_MCP_Implementation.md)
- [DeepAgents Integration Analysis](../../../project-knowledge/DeepAgents_Integration_Analysis.md)
- [AutoBuild Product Specification](../../../project-knowledge/AutoBuild_Product_Specification.md)
- [Kris Wong (ClosedLoop) context optimization insight](https://www.linkedin.com/posts/kriswong_closedloop-uses-claude-code-ai-agents)
- [Graphiti Documentation](https://github.com/getzep/graphiti)
- [FalkorDB Documentation](https://www.falkordb.com/)

---

## Appendix A: GraphitiMiddleware Full Implementation

```python
"""
guardkit/orchestrator/middleware/graphiti_middleware.py

Custom middleware for Graphiti temporal knowledge graph integration.
"""

from typing import Optional
from datetime import datetime, timezone
import json

from langchain.agents.middleware import AgentMiddleware
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType


class GraphitiMiddleware(AgentMiddleware):
    """
    Middleware that integrates Graphiti temporal knowledge graph
    for job-specific context retrieval and outcome learning.
    
    Provides:
    - Pre-task context injection based on similar past tasks
    - Post-task outcome capture for future learning
    - Pattern and architecture knowledge retrieval
    """
    
    def __init__(
        self,
        graphiti: Graphiti,
        project_id: str,
        context_budget: int = 4000,
        enable_turn_capture: bool = False,
        turn_capture_threshold: int = 7
    ):
        super().__init__()
        self.graphiti = graphiti
        self.project_id = project_id
        self.context_budget = context_budget
        self.enable_turn_capture = enable_turn_capture
        self.turn_capture_threshold = turn_capture_threshold
        
        self._current_task: Optional[dict] = None
        self._turn_count: int = 0
    
    async def before_request(self, request) -> any:
        """Inject relevant context before task execution."""
        
        task_context = self._extract_task_context(request)
        if not task_context:
            return request
        
        self._current_task = task_context
        self._turn_count = 0
        
        # Build context from knowledge graph
        context_text = await self._build_context(task_context)
        
        if context_text:
            request.system_prompt = f"""
{request.system_prompt}

## Historical Context from Similar Tasks

{context_text}

Use this context to inform your approach. It reflects patterns and outcomes from similar past work.
"""
        
        return request
    
    async def after_response(self, response) -> any:
        """Capture outcomes and optionally turn-level data."""
        
        self._turn_count += 1
        
        # Capture turn-level if enabled and appropriate
        if self._should_capture_turn():
            await self._capture_turn(response)
        
        # Capture task outcome if this appears to be completion
        if self._is_task_completion(response):
            await self._capture_task_outcome(response)
        
        return response
    
    async def _build_context(self, task: dict) -> str:
        """Build context string from knowledge graph queries."""
        
        sections = []
        budget_remaining = self.context_budget
        
        # 1. Similar task outcomes (30% budget)
        similar = await self.graphiti.search(
            query=task.get("description", ""),
            group_ids=[
                "task_outcomes",
                f"stack_{task.get('tech_stack', 'python')}"
            ],
            num_results=3
        )
        if similar:
            text = self._summarize_outcomes(similar, int(budget_remaining * 0.3))
            if text:
                sections.append(f"### What Worked Before\n{text}")
                budget_remaining -= len(text.split())
        
        # 2. Relevant patterns (25% budget)
        patterns = await self.graphiti.search(
            query=f"{task.get('type', '')} {task.get('description', '')}",
            group_ids=[f"patterns_{task.get('tech_stack', 'python')}"],
            num_results=3
        )
        if patterns:
            text = self._summarize_patterns(patterns, int(budget_remaining * 0.25))
            if text:
                sections.append(f"### Applicable Patterns\n{text}")
                budget_remaining -= len(text.split())
        
        # 3. Warnings from failed approaches (20% budget)
        warnings = await self.graphiti.search(
            query=task.get("description", ""),
            group_ids=["failed_approaches"],
            num_results=2
        )
        if warnings:
            text = self._summarize_warnings(warnings, int(budget_remaining * 0.2))
            if text:
                sections.append(f"### Patterns to Avoid\n{text}")
        
        return "\n\n".join(sections) if sections else ""
    
    async def _capture_task_outcome(self, response) -> None:
        """Capture task completion as learning episode."""
        
        if not self._current_task:
            return
        
        episode = {
            "task_id": self._current_task.get("id"),
            "feature_id": self._current_task.get("feature_id"),
            "description": self._current_task.get("description"),
            "tech_stack": self._current_task.get("tech_stack"),
            "turns_taken": self._turn_count,
            "outcome": self._extract_outcome(response),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.graphiti.add_episode(
            name=f"task_outcome_{episode['task_id']}",
            episode_body=json.dumps(episode),
            source=EpisodeType.json,
            reference_time=datetime.now(timezone.utc),
            group_id="task_outcomes"
        )
    
    async def _capture_turn(self, response) -> None:
        """Capture individual turn for detailed pattern learning."""
        
        if not self._current_task:
            return
        
        episode = {
            "task_id": self._current_task.get("id"),
            "turn_number": self._turn_count,
            "action_summary": self._extract_action_summary(response),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.graphiti.add_episode(
            name=f"turn_{episode['task_id']}_{self._turn_count}",
            episode_body=json.dumps(episode),
            source=EpisodeType.json,
            reference_time=datetime.now(timezone.utc),
            group_id=f"task_{episode['task_id']}_turns"
        )
    
    def _should_capture_turn(self) -> bool:
        """Determine if turn-level capture is appropriate."""
        
        if not self.enable_turn_capture:
            return False
        
        task = self._current_task or {}
        complexity = task.get("complexity", 0)
        
        return complexity >= self.turn_capture_threshold
    
    def _extract_task_context(self, request) -> Optional[dict]:
        """Extract task context from request."""
        # Implementation depends on request structure
        pass
    
    def _is_task_completion(self, response) -> bool:
        """Determine if response represents task completion."""
        # Implementation depends on response structure
        pass
    
    def _extract_outcome(self, response) -> str:
        """Extract outcome status from response."""
        # Implementation depends on response structure
        return "completed"
    
    def _extract_action_summary(self, response) -> str:
        """Extract action summary from response."""
        # Implementation depends on response structure
        pass
    
    def _summarize_outcomes(self, results: list, max_tokens: int) -> str:
        """Summarize task outcomes within token budget."""
        # Implementation: format and truncate results
        pass
    
    def _summarize_patterns(self, results: list, max_tokens: int) -> str:
        """Summarize patterns within token budget."""
        # Implementation: format and truncate results
        pass
    
    def _summarize_warnings(self, results: list, max_tokens: int) -> str:
        """Summarize failure patterns within token budget."""
        # Implementation: format and truncate results
        pass
```

---

## Appendix B: Episode Schema Reference

### Task Outcome Episode

```json
{
  "task_id": "TASK-a3f8",
  "feature_id": "FEAT-001",
  "description": "Add JWT authentication to API endpoints",
  "tech_stack": "python",
  "approach_used": "decorator_pattern",
  "player_turns": 4,
  "coach_feedback_summary": ["test_coverage", "error_handling"],
  "patterns_applied": ["repository_pattern", "dependency_injection"],
  "tests_generated": 12,
  "coverage_achieved": 87.5,
  "issues_encountered": ["circular_dependency"],
  "resolution_strategies": ["interface_extraction"],
  "complexity_estimate": 5,
  "actual_complexity": 7,
  "duration_minutes": 45,
  "final_status": "success"
}
```

### Review Decision Episode

```json
{
  "task_id": "TASK-a3f8",
  "feature_id": "FEAT-001",
  "review_type": "code_review",
  "findings_summary": "Good implementation, needs error handling improvements",
  "recommendations": [
    "Add specific exception types for auth failures",
    "Improve logging for debugging"
  ],
  "severity_distribution": {
    "critical": 0,
    "major": 1,
    "minor": 2,
    "suggestion": 3
  },
  "categories": ["error_handling", "logging"],
  "decision": "implement",
  "spawned_tasks": ["TASK-a3f9", "TASK-a3fa"],
  "review_duration_seconds": 120
}
```

### Pattern Entity Episode

```json
{
  "entity_type": "pattern",
  "name": "repository_pattern",
  "category": "data_access",
  "description": "Abstracts data persistence behind repository interface",
  "when_to_use": "When accessing database or external data sources",
  "code_example": "class UserRepository:\n    def get_by_id(self, id: str) -> User: ...",
  "tech_stack": "python",
  "template": "python-fastapi-template",
  "usage_count": 15,
  "success_rate": 0.93
}
```

### Feature Completion Episode

```json
{
  "feature_id": "FEAT-001",
  "title": "User Authentication System",
  "description": "Complete JWT-based authentication with role-based access",
  "planned_task_count": 5,
  "actual_task_count": 7,
  "task_additions": ["TASK-a3f9", "TASK-a3fa"],
  "decomposition_accuracy": 0.71,
  "total_work_hours": 8.5,
  "estimated_hours": 6.0,
  "acceptance_criteria_met": {
    "ac_1": true,
    "ac_2": true,
    "ac_3": true
  },
  "architecture_changes": ["Added auth service layer"],
  "what_worked": ["Decorator pattern for endpoint protection"],
  "what_struggled": ["Token refresh logic complexity"],
  "recommendations_for_similar": "Consider dedicated token service from start"
}
```
