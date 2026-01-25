# Graphiti Prototype Integration Plan for Claude Code GuardKit

> **Purpose**: Define a lightweight integration of Graphiti temporal knowledge graph with the current markdown-based Claude Code version of GuardKit to validate learning value before the DeepAgents migration.
>
> **Date**: January 2025
> **Status**: Implementation Ready
> **Approach**: Minimal hooks into existing commands, validate before investing in full middleware architecture

---

## Executive Summary

This plan outlines a prototype integration of Graphiti with the current Claude Code markdown-based GuardKit. The goal is to validate that:

1. Captured episodes actually improve task execution quality
2. The episode schemas capture useful data
3. Query patterns provide meaningful job-specific context
4. The approach is worth the full DeepAgents middleware investment

**Estimated effort**: 2-3 days for basic integration, 1-2 days for tuning

---

## Architecture Overview

### Current GuardKit Flow (Markdown-based)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code Session                         │
│                                                                 │
│  User: /task-work TASK-XXX                                     │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │ Read task from  │───▶│ Load agent docs │                    │
│  │ .tasks/TASK-XXX │    │ from .claude/   │                    │
│  └─────────────────┘    └─────────────────┘                    │
│           │                      │                              │
│           ▼                      ▼                              │
│  ┌─────────────────────────────────────────┐                   │
│  │        Execute task with Claude         │                   │
│  │        (Player/Coach iterations)        │                   │
│  └─────────────────────────────────────────┘                   │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ Update task.md  │                                           │
│  │ status          │                                           │
│  └─────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Proposed Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code Session                         │
│                                                                 │
│  User: /task-work TASK-XXX                                     │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 🆕 GRAPHITI     │  ← Query similar tasks, patterns,         │
│  │ Context Query   │    architecture, warnings                  │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │ Read task from  │───▶│ Load agent docs │                    │
│  │ .tasks/TASK-XXX │    │ + 🆕 CONTEXT    │                    │
│  └─────────────────┘    └─────────────────┘                    │
│           │                      │                              │
│           ▼                      ▼                              │
│  ┌─────────────────────────────────────────┐                   │
│  │        Execute task with Claude         │                   │
│  │        (Player/Coach iterations)        │                   │
│  └─────────────────────────────────────────┘                   │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │ Update task.md  │───▶│ 🆕 GRAPHITI     │ ← Capture outcome  │
│  │ status          │    │ Episode Capture │   as episode       │
│  └─────────────────┘    └─────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 FalkorDB + Graphiti (Docker)                    │
│   docker run -p 6379:6379 -p 3000:3000 -p 8000:8000 \          │
│     falkordb/graphiti-knowledge-graph-mcp                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Critical Pre-Session Context (PRIORITY)

Based on analysis of the feature-build crisis, **session context loading** is the highest priority integration point. Without this, each Claude Code session starts fresh and repeats the same mistakes.

### The Core Problem

The feature-build reviews reveal a pattern:
1. Session 1 makes a decision (e.g., "use subprocess to CLI")
2. Session 2 doesn't know this decision exists
3. Session 2 discovers the approach doesn't work
4. Session 3 tries to fix it without knowing the original rationale
5. Cycle repeats

### The Solution: Session Context Loading

Before ANY command execution, load critical context:

```python
# In CLI entry point or command start
async def load_critical_context() -> CriticalContext:
    """Load must-know context at session start."""
    
    graphiti = get_graphiti()
    if not graphiti.enabled:
        return CriticalContext.empty()
    
    # 1. Architecture decisions - "How things SHOULD work"
    decisions = await graphiti.search(
        query="architecture decision integration protocol",
        group_ids=["architecture_decisions"],
        num_results=10
    )
    
    # 2. Failure patterns - "What NOT to do"
    failures = await graphiti.search(
        query="failure error bug pattern",
        group_ids=["failure_patterns", "failed_approaches"],
        num_results=10
    )
    
    # 3. Component status - "What's incomplete"
    incomplete = await graphiti.search(
        query="stub partial not_implemented incomplete",
        group_ids=["component_status"],
        num_results=10
    )
    
    # 4. Integration points - "How components connect"
    integrations = await graphiti.search(
        query="integration connects protocol",
        group_ids=["integration_points"],
        num_results=10
    )
    
    return CriticalContext(
        decisions=decisions,
        failures=failures,
        incomplete=incomplete,
        integrations=integrations
    )
```

### Context Injection

```python
def format_session_warnings(context: CriticalContext) -> str:
    """Format context as warnings for prompt injection."""
    
    sections = []
    
    if context.failures:
        sections.append("""## ⚠️ Known Issues - DO NOT REPEAT

" + "\n".join([
            f"- {f['symptom']}: {f['fix']}" for f in context.failures
        ]))
    
    if context.incomplete:
        sections.append("""## 🚧 Incomplete Components

" + "\n".join([
            f"- {c['component']}.{c['method']}: {c['status']} - {c['notes']}"
            for c in context.incomplete
        ]))
    
    if context.decisions:
        sections.append("""## 📐 Architecture Decisions (FOLLOW THESE)

" + "\n".join([
            f"- {d['decision']} (NOT: {d.get('not', 'n/a')})"
            for d in context.decisions
        ]))
    
    return "\n\n".join(sections)
```

### Manual Seeding (Immediate Action)

To break the current feature-build cycle, manually seed these episodes:

```python
# Run once to seed critical knowledge
async def seed_feature_build_knowledge():
    graphiti = get_graphiti()
    
    # Architecture decisions
    await graphiti.add_episode(
        name="arch_sdk_not_subprocess",
        episode_body=json.dumps({
            "decision": "Use SDK query() for task-work invocation",
            "not": "subprocess to guardkit CLI",
            "rationale": "CLI command doesn't exist, SDK query() invokes slash commands directly"
        }),
        group_id="architecture_decisions"
    )
    
    await graphiti.add_episode(
        name="arch_feature_paths",
        episode_body=json.dumps({
            "decision": "In feature mode, paths use FEAT-XXX worktree ID",
            "not": "individual TASK-XXX IDs",
            "rationale": "Feature worktree is shared, task IDs are for task management not filesystem"
        }),
        group_id="architecture_decisions"
    )
    
    # Failure patterns
    await graphiti.add_episode(
        name="failure_missing_cli",
        episode_body=json.dumps({
            "symptom": "subprocess.CalledProcessError: guardkit task-work",
            "root_cause": "CLI command not implemented",
            "fix": "Use SDK query() instead of subprocess"
        }),
        group_id="failure_patterns"
    )
    
    await graphiti.add_episode(
        name="failure_wrong_path",
        episode_body=json.dumps({
            "symptom": "Task-work results not found at .../TASK-XXX/...",
            "root_cause": "Path uses task ID instead of feature worktree ID",
            "fix": "Use feature_worktree_id for path construction in feature mode"
        }),
        group_id="failure_patterns"
    )
    
    await graphiti.add_episode(
        name="failure_mock_preloop",
        episode_body=json.dumps({
            "symptom": "Pre-loop returns complexity=5, arch_score=80 (hardcoded)",
            "root_cause": "TaskWorkInterface.execute_design_phase() is stub",
            "fix": "Implement with SDK query() to /task-work --design-only"
        }),
        group_id="failure_patterns"
    )
    
    # Component status
    await graphiti.add_episode(
        name="component_taskwork_interface",
        episode_body=json.dumps({
            "component": "TaskWorkInterface",
            "method": "execute_design_phase",
            "status": "stub",
            "notes": "Returns mock data, needs SDK query() integration"
        }),
        group_id="component_status"
    )
    
    # Integration points
    await graphiti.add_episode(
        name="integration_autobuild_taskwork",
        episode_body=json.dumps({
            "name": "autobuild_to_taskwork",
            "connects": ["AutoBuildOrchestrator", "task-work command"],
            "protocol": "sdk_query",
            "correct": "query('/task-work TASK-XXX --implement-only', cwd=worktree_path)",
            "wrong": "subprocess.run(['guardkit', 'task-work', ...])"
        }),
        group_id="integration_points"
    )
```

---

## Implementation Components

### 1. Project Structure

```
guardkit/
├── src/
│   └── guardkit/
│       ├── knowledge/                    # 🆕 New module
│       │   ├── __init__.py
│       │   ├── graphiti_client.py       # Graphiti SDK wrapper
│       │   ├── context_builder.py       # Build context for prompts
│       │   ├── episode_capture.py       # Capture outcomes as episodes
│       │   └── schemas.py               # Episode schema definitions
│       └── commands/
│           ├── task_work.py             # Add hooks
│           ├── task_review.py           # Add hooks
│           ├── task_complete.py         # Add hooks
│           ├── template_create.py       # Add hooks
│           └── feature_plan.py          # Add hooks
├── config/
│   └── graphiti.yaml                    # Configuration
└── scripts/
    └── start_graphiti.sh                # Docker startup script
```

### 2. Configuration

```yaml
# config/graphiti.yaml

graphiti:
  enabled: true  # Feature flag for easy disable
  
  connection:
    host: "localhost"
    port: 6379
    # For FalkorDB connection
    
  embedding:
    provider: "openai"
    model: "text-embedding-3-small"
    # Uses OPENAI_API_KEY from environment
    
  context:
    enabled: true
    budget_tokens: 4000
    allocation:
      similar_outcomes: 0.30
      relevant_patterns: 0.25
      architecture: 0.20
      warnings: 0.15
      meta: 0.10
      
  capture:
    task_outcomes: true
    review_decisions: true
    feature_completions: true
    turn_level:
      enabled: false  # Start disabled, enable selectively
      complexity_threshold: 7
      on_failure: true
      
  retention:
    task_outcomes: "6_months"
    review_decisions: "6_months"
    feature_completions: "12_months"
    turn_level: "3_months"
```

### 3. Docker Startup Script

```bash
#!/bin/bash
# scripts/start_graphiti.sh

# Start FalkorDB with Graphiti MCP
docker run -d \
  --name guardkit-graphiti \
  -p 6379:6379 \
  -p 3000:3000 \
  -p 8000:8000 \
  -v guardkit-graphiti-data:/data \
  falkordb/graphiti-knowledge-graph-mcp

echo "Graphiti started. Waiting for initialization..."
sleep 5

# Verify connection
python -c "
from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIClient
import asyncio

async def check():
    client = Graphiti(
        'bolt://localhost:6379',
        OpenAIClient()
    )
    print('✓ Graphiti connection successful')
    
asyncio.run(check())
"
```

---

## Core Implementation

### 4. Graphiti Client Wrapper

```python
"""
guardkit/knowledge/graphiti_client.py

Wrapper around Graphiti SDK for GuardKit integration.
"""

import os
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client import OpenAIClient

import yaml


class GuardKitGraphiti:
    """
    Singleton wrapper for Graphiti client with GuardKit-specific operations.
    """
    
    _instance: Optional['GuardKitGraphiti'] = None
    _client: Optional[Graphiti] = None
    _config: Optional[Dict] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'GuardKitGraphiti':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    async def initialize(cls, config_path: Optional[Path] = None) -> 'GuardKitGraphiti':
        """Initialize the Graphiti client."""
        instance = cls.get_instance()
        
        # Load configuration
        if config_path is None:
            config_path = Path.cwd() / "config" / "graphiti.yaml"
        
        if config_path.exists():
            with open(config_path) as f:
                instance._config = yaml.safe_load(f).get('graphiti', {})
        else:
            instance._config = {'enabled': False}
        
        if not instance._config.get('enabled', False):
            return instance
        
        # Initialize Graphiti client
        conn = instance._config.get('connection', {})
        host = conn.get('host', 'localhost')
        port = conn.get('port', 6379)
        
        instance._client = Graphiti(
            f"bolt://{host}:{port}",
            OpenAIClient()  # Uses OPENAI_API_KEY from env
        )
        
        return instance
    
    @property
    def enabled(self) -> bool:
        """Check if Graphiti integration is enabled."""
        return self._config and self._config.get('enabled', False) and self._client is not None
    
    @property
    def client(self) -> Optional[Graphiti]:
        """Get the underlying Graphiti client."""
        return self._client
    
    @property
    def config(self) -> Dict:
        """Get configuration."""
        return self._config or {}
    
    async def search(
        self,
        query: str,
        group_ids: List[str],
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant episodes/entities.
        
        Args:
            query: Search query text
            group_ids: List of group IDs to search within
            num_results: Maximum number of results
            
        Returns:
            List of search results with facts and metadata
        """
        if not self.enabled:
            return []
        
        try:
            results = await self._client.search(
                query=query,
                group_ids=group_ids,
                num_results=num_results
            )
            return [self._format_result(r) for r in results]
        except Exception as e:
            print(f"[Graphiti] Search error: {e}")
            return []
    
    async def add_episode(
        self,
        name: str,
        episode_body: Dict[str, Any],
        group_id: str,
        reference_time: Optional[datetime] = None
    ) -> bool:
        """
        Add an episode to the knowledge graph.
        
        Args:
            name: Episode identifier
            episode_body: Episode data as dictionary
            group_id: Group ID for namespacing
            reference_time: When this episode occurred
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            await self._client.add_episode(
                name=name,
                episode_body=json.dumps(episode_body),
                source=EpisodeType.json,
                reference_time=reference_time or datetime.now(timezone.utc),
                group_id=group_id
            )
            return True
        except Exception as e:
            print(f"[Graphiti] Add episode error: {e}")
            return False
    
    def _format_result(self, result) -> Dict[str, Any]:
        """Format a search result for consumption."""
        return {
            'fact': getattr(result, 'fact', str(result)),
            'score': getattr(result, 'score', 0.0),
            'episode_id': getattr(result, 'episode_id', None),
            'valid_at': getattr(result, 'valid_at', None),
            'invalid_at': getattr(result, 'invalid_at', None),
        }


# Convenience function for synchronous code
def get_graphiti() -> GuardKitGraphiti:
    """Get the Graphiti client instance."""
    return GuardKitGraphiti.get_instance()


async def init_graphiti(config_path: Optional[Path] = None) -> GuardKitGraphiti:
    """Initialize Graphiti client."""
    return await GuardKitGraphiti.initialize(config_path)
```

### 5. Episode Schemas

```python
"""
guardkit/knowledge/schemas.py

Episode schema definitions for Graphiti integration.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ESCALATED = "escalated"
    PARTIAL = "partial"


class ReviewDecision(str, Enum):
    ACCEPT = "accept"
    IMPLEMENT = "implement"
    SKIP = "skip"


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


@dataclass
class TaskOutcomeEpisode:
    """Episode captured when a task is completed."""
    
    task_id: str
    feature_id: Optional[str]
    description: str
    tech_stack: str
    
    # Execution details
    approach_used: str
    player_turns: int
    coach_feedback_themes: List[str]
    
    # Patterns
    patterns_applied: List[str]
    issues_encountered: List[str]
    resolution_strategies: List[str]
    
    # Quality metrics
    tests_generated: int = 0
    coverage_achieved: float = 0.0
    
    # Complexity
    complexity_estimate: int = 0
    actual_complexity: int = 0
    
    # Timing
    duration_minutes: int = 0
    
    # Outcome
    final_status: TaskStatus = TaskStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['final_status'] = self.final_status.value
        return data


@dataclass
class ReviewDecisionEpisode:
    """Episode captured when a review decision is made."""
    
    task_id: str
    feature_id: Optional[str]
    review_type: str  # code_review | architectural | test_coverage
    
    # Findings
    findings_summary: str
    recommendations: List[str]
    severity_distribution: Dict[str, int]  # {critical: N, major: N, ...}
    categories: List[str]  # e.g., ["error_handling", "testing"]
    
    # Decision
    decision: ReviewDecision
    decision_rationale: Optional[str] = None
    
    # If "implement" was chosen
    spawned_tasks: List[str] = field(default_factory=list)
    implementation_scope: Optional[str] = None
    
    # Meta
    review_duration_seconds: int = 0
    reviewer_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['decision'] = self.decision.value
        return data


@dataclass
class RefinementAttemptEpisode:
    """Episode captured for each refinement attempt."""
    
    task_id: str
    attempt_number: int
    
    # Failure context
    failure_type: str
    failure_description: str
    stack_trace_signature: Optional[str] = None  # Anonymized
    
    # Fix details
    fix_attempted: str
    fix_category: str
    
    # Outcome
    result: str  # "resolved" | "failed" | "partial"
    time_to_fix_seconds: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class FeatureCompletionEpisode:
    """Episode captured when a feature is completed."""
    
    feature_id: str
    title: str
    description: str
    
    # Task decomposition
    planned_task_count: int
    actual_task_count: int
    tasks_added: List[str] = field(default_factory=list)
    tasks_removed: List[str] = field(default_factory=list)
    
    # Execution
    total_work_hours: float = 0.0
    estimated_hours: float = 0.0
    calendar_days: int = 0
    
    # Quality
    acceptance_criteria_met: Dict[str, bool] = field(default_factory=dict)
    review_cycles_total: int = 0
    refinement_cycles_total: int = 0
    
    # Architecture
    architecture_changes: List[str] = field(default_factory=list)
    new_services_created: List[str] = field(default_factory=list)
    dependencies_introduced: List[str] = field(default_factory=list)
    
    # Lessons
    what_worked: List[str] = field(default_factory=list)
    what_struggled: List[str] = field(default_factory=list)
    recommendations_for_similar: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class PatternEntityEpisode:
    """Episode for syncing pattern definitions to Graphiti."""
    
    entity_type: str = "pattern"
    name: str = ""
    category: str = ""  # error_handling, data_access, etc.
    description: str = ""
    when_to_use: str = ""
    code_example: str = ""
    tech_stack: str = ""
    template: str = ""
    usage_count: int = 0
    success_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class AgentEntityEpisode:
    """Episode for syncing agent definitions to Graphiti."""
    
    entity_type: str = "agent"
    name: str = ""
    display_name: str = ""
    tech_stack: str = ""
    capabilities: str = ""
    specializations: str = ""
    template: str = ""
    invocation_count: int = 0
    success_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
```

### 6. Context Builder

```python
"""
guardkit/knowledge/context_builder.py

Build context from Graphiti for injection into prompts.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .graphiti_client import get_graphiti


@dataclass
class ContextBudget:
    """Token budget allocation for context sections."""
    
    total_tokens: int = 4000
    
    # Allocation percentages
    similar_outcomes: float = 0.30
    relevant_patterns: float = 0.25
    architecture: float = 0.20
    warnings: float = 0.15
    meta: float = 0.10


@dataclass
class TaskContext:
    """Context for task execution."""
    
    task_id: str
    description: str
    tech_stack: str
    feature_id: Optional[str] = None
    complexity: int = 5
    is_refinement: bool = False
    refinement_attempt: int = 0


class ContextBuilder:
    """
    Builds context from Graphiti for injection into Claude prompts.
    """
    
    def __init__(self, budget: Optional[ContextBudget] = None):
        self.graphiti = get_graphiti()
        self.budget = budget or ContextBudget()
    
    async def build_task_context(self, task: TaskContext) -> str:
        """
        Build context string for task execution.
        
        Args:
            task: Task context information
            
        Returns:
            Formatted context string for prompt injection
        """
        if not self.graphiti.enabled:
            return ""
        
        # Adjust budget based on task characteristics
        budget = self._adjust_budget(task)
        
        sections = []
        
        # 1. Similar task outcomes (what worked before)
        similar_text = await self._get_similar_outcomes(task, budget)
        if similar_text:
            sections.append(f"### What Worked for Similar Tasks\n\n{similar_text}")
        
        # 2. Relevant patterns from template
        patterns_text = await self._get_relevant_patterns(task, budget)
        if patterns_text:
            sections.append(f"### Applicable Codebase Patterns\n\n{patterns_text}")
        
        # 3. Architecture context
        arch_text = await self._get_architecture_context(task, budget)
        if arch_text:
            sections.append(f"### Architecture Context\n\n{arch_text}")
        
        # 4. Warning patterns (what to avoid)
        warnings_text = await self._get_warnings(task, budget)
        if warnings_text:
            sections.append(f"### Patterns to Avoid\n\n{warnings_text}")
        
        if not sections:
            return ""
        
        return f"""
## Historical Context from Knowledge Graph

The following context is derived from similar past tasks and the project's knowledge base.
Use this to inform your approach.

{chr(10).join(sections)}
"""
    
    async def build_review_context(self, task_id: str) -> str:
        """Build context for review command."""
        if not self.graphiti.enabled:
            return ""
        
        results = await self.graphiti.search(
            query=f"review findings recommendations {task_id}",
            group_ids=["review_decisions", "task_outcomes"],
            num_results=5
        )
        
        if not results:
            return ""
        
        context_lines = []
        for r in results:
            context_lines.append(f"- {r['fact']}")
        
        return f"""
## Similar Review Patterns

{chr(10).join(context_lines)}
"""
    
    async def build_feature_planning_context(
        self,
        description: str,
        tech_stack: str
    ) -> str:
        """Build context for feature planning."""
        if not self.graphiti.enabled:
            return ""
        
        sections = []
        
        # Architecture context
        arch_results = await self.graphiti.search(
            query=f"{description} architecture services",
            group_ids=["project_architecture", "service_dependencies"],
            num_results=5
        )
        
        if arch_results:
            lines = [f"- {r['fact']}" for r in arch_results]
            sections.append(f"### Current Architecture\n\n{chr(10).join(lines)}")
        
        # Similar feature decompositions
        decomp_results = await self.graphiti.search(
            query=f"{description} feature tasks decomposition",
            group_ids=["feature_completions", "feature_decomposition"],
            num_results=5
        )
        
        if decomp_results:
            lines = [f"- {r['fact']}" for r in decomp_results]
            sections.append(f"### Similar Feature Patterns\n\n{chr(10).join(lines)}")
        
        if not sections:
            return ""
        
        return f"""
## Planning Context from Knowledge Graph

{chr(10).join(sections)}
"""
    
    def _adjust_budget(self, task: TaskContext) -> ContextBudget:
        """Adjust budget based on task characteristics."""
        budget = ContextBudget(
            total_tokens=self.budget.total_tokens,
            similar_outcomes=self.budget.similar_outcomes,
            relevant_patterns=self.budget.relevant_patterns,
            architecture=self.budget.architecture,
            warnings=self.budget.warnings,
            meta=self.budget.meta,
        )
        
        # Refinement attempt - emphasize warnings
        if task.is_refinement:
            budget.warnings = 0.35
            budget.similar_outcomes = 0.40
            budget.relevant_patterns = 0.10
            budget.architecture = 0.10
            budget.meta = 0.05
        
        # High complexity - more context overall
        if task.complexity >= 7:
            budget.total_tokens = 6000
        
        return budget
    
    async def _get_similar_outcomes(
        self,
        task: TaskContext,
        budget: ContextBudget
    ) -> str:
        """Get similar task outcomes."""
        results = await self.graphiti.search(
            query=task.description,
            group_ids=[
                "task_outcomes",
                f"stack_{task.tech_stack}",
                "successful_patterns"
            ],
            num_results=3
        )
        
        return self._format_results(
            results,
            int(budget.total_tokens * budget.similar_outcomes)
        )
    
    async def _get_relevant_patterns(
        self,
        task: TaskContext,
        budget: ContextBudget
    ) -> str:
        """Get relevant patterns."""
        results = await self.graphiti.search(
            query=f"{task.description} pattern",
            group_ids=[f"patterns_{task.tech_stack}"],
            num_results=3
        )
        
        return self._format_results(
            results,
            int(budget.total_tokens * budget.relevant_patterns)
        )
    
    async def _get_architecture_context(
        self,
        task: TaskContext,
        budget: ContextBudget
    ) -> str:
        """Get architecture context."""
        results = await self.graphiti.search(
            query=task.description,
            group_ids=["project_architecture", "service_dependencies"],
            num_results=2
        )
        
        return self._format_results(
            results,
            int(budget.total_tokens * budget.architecture)
        )
    
    async def _get_warnings(
        self,
        task: TaskContext,
        budget: ContextBudget
    ) -> str:
        """Get warning patterns."""
        results = await self.graphiti.search(
            query=task.description,
            group_ids=["failed_approaches"],
            num_results=2
        )
        
        return self._format_results(
            results,
            int(budget.total_tokens * budget.warnings)
        )
    
    def _format_results(
        self,
        results: List[Dict[str, Any]],
        max_tokens: int
    ) -> str:
        """Format results within token budget."""
        if not results:
            return ""
        
        lines = []
        current_tokens = 0
        
        for r in results:
            fact = r.get('fact', '')
            # Rough token estimate: 1 token ≈ 4 chars
            fact_tokens = len(fact) // 4
            
            if current_tokens + fact_tokens > max_tokens:
                break
            
            lines.append(f"- {fact}")
            current_tokens += fact_tokens
        
        return "\n".join(lines)
```

### 7. Episode Capture

```python
"""
guardkit/knowledge/episode_capture.py

Capture outcomes as episodes in Graphiti.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from .graphiti_client import get_graphiti
from .schemas import (
    TaskOutcomeEpisode,
    ReviewDecisionEpisode,
    RefinementAttemptEpisode,
    FeatureCompletionEpisode,
    PatternEntityEpisode,
    AgentEntityEpisode,
    TaskStatus,
    ReviewDecision,
)


class EpisodeCapture:
    """
    Captures GuardKit events as Graphiti episodes.
    """
    
    def __init__(self):
        self.graphiti = get_graphiti()
    
    async def capture_task_outcome(
        self,
        task_id: str,
        description: str,
        tech_stack: str,
        status: TaskStatus,
        feature_id: Optional[str] = None,
        approach_used: str = "",
        player_turns: int = 0,
        coach_feedback_themes: Optional[List[str]] = None,
        patterns_applied: Optional[List[str]] = None,
        issues_encountered: Optional[List[str]] = None,
        resolution_strategies: Optional[List[str]] = None,
        tests_generated: int = 0,
        coverage_achieved: float = 0.0,
        complexity_estimate: int = 0,
        actual_complexity: int = 0,
        duration_minutes: int = 0,
    ) -> bool:
        """
        Capture a task completion outcome.
        
        Args:
            task_id: Task identifier
            description: Task description
            tech_stack: Technology stack
            status: Final task status
            ... other task details
            
        Returns:
            True if capture succeeded
        """
        if not self.graphiti.enabled:
            return False
        
        episode = TaskOutcomeEpisode(
            task_id=task_id,
            feature_id=feature_id,
            description=description,
            tech_stack=tech_stack,
            approach_used=approach_used,
            player_turns=player_turns,
            coach_feedback_themes=coach_feedback_themes or [],
            patterns_applied=patterns_applied or [],
            issues_encountered=issues_encountered or [],
            resolution_strategies=resolution_strategies or [],
            tests_generated=tests_generated,
            coverage_achieved=coverage_achieved,
            complexity_estimate=complexity_estimate,
            actual_complexity=actual_complexity,
            duration_minutes=duration_minutes,
            final_status=status,
        )
        
        return await self.graphiti.add_episode(
            name=f"task_outcome_{task_id}",
            episode_body=episode.to_dict(),
            group_id="task_outcomes",
        )
    
    async def capture_review_decision(
        self,
        task_id: str,
        review_type: str,
        findings_summary: str,
        recommendations: List[str],
        decision: ReviewDecision,
        feature_id: Optional[str] = None,
        severity_distribution: Optional[Dict[str, int]] = None,
        categories: Optional[List[str]] = None,
        decision_rationale: Optional[str] = None,
        spawned_tasks: Optional[List[str]] = None,
        implementation_scope: Optional[str] = None,
        review_duration_seconds: int = 0,
        reviewer_confidence: float = 0.0,
    ) -> bool:
        """
        Capture a review decision.
        
        Args:
            task_id: Task being reviewed
            review_type: Type of review
            findings_summary: Summary of findings
            recommendations: List of recommendations
            decision: User's decision (accept/implement/skip)
            ... other review details
            
        Returns:
            True if capture succeeded
        """
        if not self.graphiti.enabled:
            return False
        
        episode = ReviewDecisionEpisode(
            task_id=task_id,
            feature_id=feature_id,
            review_type=review_type,
            findings_summary=findings_summary,
            recommendations=recommendations,
            severity_distribution=severity_distribution or {},
            categories=categories or [],
            decision=decision,
            decision_rationale=decision_rationale,
            spawned_tasks=spawned_tasks or [],
            implementation_scope=implementation_scope,
            review_duration_seconds=review_duration_seconds,
            reviewer_confidence=reviewer_confidence,
        )
        
        return await self.graphiti.add_episode(
            name=f"review_decision_{task_id}_{datetime.now().isoformat()}",
            episode_body=episode.to_dict(),
            group_id="review_decisions",
        )
    
    async def capture_refinement_attempt(
        self,
        task_id: str,
        attempt_number: int,
        failure_type: str,
        failure_description: str,
        fix_attempted: str,
        fix_category: str,
        result: str,
        stack_trace_signature: Optional[str] = None,
        time_to_fix_seconds: int = 0,
    ) -> bool:
        """
        Capture a refinement attempt.
        
        Args:
            task_id: Task being refined
            attempt_number: Which attempt this is
            failure_type: Type of failure
            failure_description: Description of failure
            fix_attempted: What fix was tried
            fix_category: Category of fix
            result: "resolved" | "failed" | "partial"
            
        Returns:
            True if capture succeeded
        """
        if not self.graphiti.enabled:
            return False
        
        episode = RefinementAttemptEpisode(
            task_id=task_id,
            attempt_number=attempt_number,
            failure_type=failure_type,
            failure_description=failure_description,
            stack_trace_signature=stack_trace_signature,
            fix_attempted=fix_attempted,
            fix_category=fix_category,
            result=result,
            time_to_fix_seconds=time_to_fix_seconds,
        )
        
        # Use different group based on outcome
        group_id = "successful_fixes" if result == "resolved" else "failed_approaches"
        
        return await self.graphiti.add_episode(
            name=f"refinement_{task_id}_{attempt_number}",
            episode_body=episode.to_dict(),
            group_id=group_id,
        )
    
    async def capture_feature_completion(
        self,
        feature_id: str,
        title: str,
        description: str,
        planned_task_count: int,
        actual_task_count: int,
        tasks_added: Optional[List[str]] = None,
        tasks_removed: Optional[List[str]] = None,
        total_work_hours: float = 0.0,
        estimated_hours: float = 0.0,
        calendar_days: int = 0,
        acceptance_criteria_met: Optional[Dict[str, bool]] = None,
        review_cycles_total: int = 0,
        refinement_cycles_total: int = 0,
        architecture_changes: Optional[List[str]] = None,
        new_services_created: Optional[List[str]] = None,
        dependencies_introduced: Optional[List[str]] = None,
        what_worked: Optional[List[str]] = None,
        what_struggled: Optional[List[str]] = None,
        recommendations_for_similar: Optional[str] = None,
    ) -> bool:
        """
        Capture a feature completion.
        
        Returns:
            True if capture succeeded
        """
        if not self.graphiti.enabled:
            return False
        
        episode = FeatureCompletionEpisode(
            feature_id=feature_id,
            title=title,
            description=description,
            planned_task_count=planned_task_count,
            actual_task_count=actual_task_count,
            tasks_added=tasks_added or [],
            tasks_removed=tasks_removed or [],
            total_work_hours=total_work_hours,
            estimated_hours=estimated_hours,
            calendar_days=calendar_days,
            acceptance_criteria_met=acceptance_criteria_met or {},
            review_cycles_total=review_cycles_total,
            refinement_cycles_total=refinement_cycles_total,
            architecture_changes=architecture_changes or [],
            new_services_created=new_services_created or [],
            dependencies_introduced=dependencies_introduced or [],
            what_worked=what_worked or [],
            what_struggled=what_struggled or [],
            recommendations_for_similar=recommendations_for_similar,
        )
        
        return await self.graphiti.add_episode(
            name=f"feature_completion_{feature_id}",
            episode_body=episode.to_dict(),
            group_id="feature_completions",
        )
    
    async def sync_pattern(
        self,
        name: str,
        category: str,
        description: str,
        when_to_use: str,
        code_example: str,
        tech_stack: str,
        template: str,
    ) -> bool:
        """
        Sync a pattern definition to Graphiti.
        
        Returns:
            True if sync succeeded
        """
        if not self.graphiti.enabled:
            return False
        
        episode = PatternEntityEpisode(
            name=name,
            category=category,
            description=description,
            when_to_use=when_to_use,
            code_example=code_example,
            tech_stack=tech_stack,
            template=template,
        )
        
        return await self.graphiti.add_episode(
            name=f"pattern_{template}_{name}",
            episode_body=episode.to_dict(),
            group_id=f"patterns_{tech_stack}",
        )
    
    async def sync_agent(
        self,
        name: str,
        display_name: str,
        tech_stack: str,
        capabilities: str,
        specializations: str,
        template: str,
    ) -> bool:
        """
        Sync an agent definition to Graphiti.
        
        Returns:
            True if sync succeeded
        """
        if not self.graphiti.enabled:
            return False
        
        episode = AgentEntityEpisode(
            name=name,
            display_name=display_name,
            tech_stack=tech_stack,
            capabilities=capabilities,
            specializations=specializations,
            template=template,
        )
        
        return await self.graphiti.add_episode(
            name=f"agent_{name}",
            episode_body=episode.to_dict(),
            group_id="agent_definitions",
        )


# Singleton instance
_capture: Optional[EpisodeCapture] = None


def get_episode_capture() -> EpisodeCapture:
    """Get the episode capture singleton."""
    global _capture
    if _capture is None:
        _capture = EpisodeCapture()
    return _capture
```

---

## Command Integration Hooks

### 8. Task Work Hook

```python
"""
guardkit/knowledge/hooks/task_work_hook.py

Hook for /task-work command integration.
"""

import asyncio
from typing import Optional, Dict, Any

from ..graphiti_client import get_graphiti
from ..context_builder import ContextBuilder, TaskContext


async def pre_task_work(
    task_id: str,
    description: str,
    tech_stack: str,
    feature_id: Optional[str] = None,
    complexity: int = 5,
) -> str:
    """
    Pre-hook for task-work command.
    Returns context to inject into the prompt.
    
    Usage in task_work.py:
        context = await pre_task_work(task_id, description, tech_stack)
        # Inject context into system prompt or task description
    """
    graphiti = get_graphiti()
    if not graphiti.enabled:
        return ""
    
    builder = ContextBuilder()
    task_context = TaskContext(
        task_id=task_id,
        description=description,
        tech_stack=tech_stack,
        feature_id=feature_id,
        complexity=complexity,
    )
    
    return await builder.build_task_context(task_context)


def pre_task_work_sync(
    task_id: str,
    description: str,
    tech_stack: str,
    feature_id: Optional[str] = None,
    complexity: int = 5,
) -> str:
    """Synchronous wrapper for pre_task_work."""
    return asyncio.run(pre_task_work(
        task_id, description, tech_stack, feature_id, complexity
    ))
```

### 9. Task Complete Hook

```python
"""
guardkit/knowledge/hooks/task_complete_hook.py

Hook for /task-complete command integration.
"""

import asyncio
from typing import Optional, List

from ..episode_capture import get_episode_capture
from ..schemas import TaskStatus


async def post_task_complete(
    task_id: str,
    description: str,
    tech_stack: str,
    status: str,  # "success" | "failed" | "escalated"
    feature_id: Optional[str] = None,
    approach_used: str = "",
    player_turns: int = 0,
    coach_feedback_themes: Optional[List[str]] = None,
    patterns_applied: Optional[List[str]] = None,
    issues_encountered: Optional[List[str]] = None,
    resolution_strategies: Optional[List[str]] = None,
    tests_generated: int = 0,
    coverage_achieved: float = 0.0,
    complexity_estimate: int = 0,
    actual_complexity: int = 0,
    duration_minutes: int = 0,
) -> bool:
    """
    Post-hook for task-complete command.
    Captures the task outcome as an episode.
    
    Usage in task_complete.py:
        await post_task_complete(
            task_id=task.id,
            description=task.description,
            tech_stack=task.tech_stack,
            status="success",
            ...
        )
    """
    capture = get_episode_capture()
    
    status_enum = TaskStatus(status)
    
    return await capture.capture_task_outcome(
        task_id=task_id,
        description=description,
        tech_stack=tech_stack,
        status=status_enum,
        feature_id=feature_id,
        approach_used=approach_used,
        player_turns=player_turns,
        coach_feedback_themes=coach_feedback_themes,
        patterns_applied=patterns_applied,
        issues_encountered=issues_encountered,
        resolution_strategies=resolution_strategies,
        tests_generated=tests_generated,
        coverage_achieved=coverage_achieved,
        complexity_estimate=complexity_estimate,
        actual_complexity=actual_complexity,
        duration_minutes=duration_minutes,
    )


def post_task_complete_sync(
    task_id: str,
    description: str,
    tech_stack: str,
    status: str,
    **kwargs
) -> bool:
    """Synchronous wrapper for post_task_complete."""
    return asyncio.run(post_task_complete(
        task_id, description, tech_stack, status, **kwargs
    ))
```

### 10. Task Review Hook

```python
"""
guardkit/knowledge/hooks/task_review_hook.py

Hook for /task-review command integration.
"""

import asyncio
from typing import Optional, List, Dict

from ..episode_capture import get_episode_capture
from ..context_builder import ContextBuilder
from ..schemas import ReviewDecision


async def pre_task_review(task_id: str) -> str:
    """
    Pre-hook for task-review command.
    Returns context about similar reviews.
    """
    builder = ContextBuilder()
    return await builder.build_review_context(task_id)


async def post_task_review(
    task_id: str,
    review_type: str,
    findings_summary: str,
    recommendations: List[str],
    decision: str,  # "accept" | "implement" | "skip"
    feature_id: Optional[str] = None,
    severity_distribution: Optional[Dict[str, int]] = None,
    categories: Optional[List[str]] = None,
    decision_rationale: Optional[str] = None,
    spawned_tasks: Optional[List[str]] = None,
    implementation_scope: Optional[str] = None,
    review_duration_seconds: int = 0,
    reviewer_confidence: float = 0.0,
) -> bool:
    """
    Post-hook for task-review command.
    Captures the review decision as an episode.
    
    Usage in task_review.py:
        # After user makes decision (Accept/Implement/Skip)
        await post_task_review(
            task_id=task.id,
            review_type="code_review",
            findings_summary=findings.summary,
            recommendations=findings.recommendations,
            decision="implement",
            spawned_tasks=["TASK-a1b2", "TASK-c3d4"],
            ...
        )
    """
    capture = get_episode_capture()
    
    decision_enum = ReviewDecision(decision)
    
    return await capture.capture_review_decision(
        task_id=task_id,
        review_type=review_type,
        findings_summary=findings_summary,
        recommendations=recommendations,
        decision=decision_enum,
        feature_id=feature_id,
        severity_distribution=severity_distribution,
        categories=categories,
        decision_rationale=decision_rationale,
        spawned_tasks=spawned_tasks,
        implementation_scope=implementation_scope,
        review_duration_seconds=review_duration_seconds,
        reviewer_confidence=reviewer_confidence,
    )


def post_task_review_sync(
    task_id: str,
    review_type: str,
    findings_summary: str,
    recommendations: List[str],
    decision: str,
    **kwargs
) -> bool:
    """Synchronous wrapper for post_task_review."""
    return asyncio.run(post_task_review(
        task_id, review_type, findings_summary, recommendations, decision, **kwargs
    ))
```

### 11. Template Create Hook

```python
"""
guardkit/knowledge/hooks/template_create_hook.py

Hook for /template-create command integration.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any
import yaml
import re

from ..episode_capture import get_episode_capture


async def post_template_create(template_path: Path) -> bool:
    """
    Post-hook for template-create command.
    Syncs template patterns and agents to Graphiti.
    
    Usage in template_create.py:
        # After template is created
        await post_template_create(Path(".claude/templates/my-template"))
    """
    capture = get_episode_capture()
    
    # Parse template
    template_name = template_path.name
    tech_stack = _detect_tech_stack(template_path)
    
    success = True
    
    # Sync patterns
    patterns_file = template_path / "patterns.md"
    if patterns_file.exists():
        patterns = _parse_patterns(patterns_file, tech_stack, template_name)
        for pattern in patterns:
            result = await capture.sync_pattern(**pattern)
            success = success and result
    
    # Sync agents
    agents_path = template_path.parent.parent / "agents"
    if agents_path.exists():
        for agent_file in agents_path.glob("*.md"):
            agent = _parse_agent(agent_file, tech_stack, template_name)
            if agent:
                result = await capture.sync_agent(**agent)
                success = success and result
    
    return success


def _detect_tech_stack(template_path: Path) -> str:
    """Detect tech stack from template."""
    config_file = template_path / "stack-config.yaml"
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)
            return config.get('tech_stack', 'unknown')
    
    # Fallback: infer from template name
    name = template_path.name.lower()
    if 'python' in name or 'fastapi' in name:
        return 'python'
    elif 'react' in name or 'next' in name:
        return 'react'
    elif 'dotnet' in name or 'maui' in name:
        return 'dotnet'
    
    return 'unknown'


def _parse_patterns(
    patterns_file: Path,
    tech_stack: str,
    template_name: str
) -> List[Dict[str, Any]]:
    """Parse patterns from patterns.md file."""
    patterns = []
    
    content = patterns_file.read_text()
    
    # Simple pattern extraction (assumes ## Pattern Name format)
    pattern_sections = re.split(r'^## ', content, flags=re.MULTILINE)[1:]
    
    for section in pattern_sections:
        lines = section.strip().split('\n')
        if not lines:
            continue
        
        name = lines[0].strip()
        body = '\n'.join(lines[1:]).strip()
        
        # Extract category from name or body
        category = "general"
        if "error" in name.lower():
            category = "error_handling"
        elif "data" in name.lower() or "repository" in name.lower():
            category = "data_access"
        elif "auth" in name.lower():
            category = "authentication"
        
        patterns.append({
            'name': name.lower().replace(' ', '_'),
            'category': category,
            'description': body[:500],  # Truncate
            'when_to_use': "",  # Would need more sophisticated parsing
            'code_example': "",
            'tech_stack': tech_stack,
            'template': template_name,
        })
    
    return patterns


def _parse_agent(
    agent_file: Path,
    tech_stack: str,
    template_name: str
) -> Dict[str, Any]:
    """Parse agent from markdown file."""
    content = agent_file.read_text()
    
    # Extract frontmatter if present
    name = agent_file.stem
    display_name = name.replace('-', ' ').title()
    
    # Simple extraction of capabilities from content
    capabilities = ""
    specializations = ""
    
    if "## Capabilities" in content:
        caps_section = content.split("## Capabilities")[1].split("##")[0]
        capabilities = caps_section.strip()[:500]
    
    if "## Specializations" in content or "## Expertise" in content:
        spec_section = content.split("## Specializations")[1].split("##")[0] if "## Specializations" in content else content.split("## Expertise")[1].split("##")[0]
        specializations = spec_section.strip()[:500]
    
    return {
        'name': name,
        'display_name': display_name,
        'tech_stack': tech_stack,
        'capabilities': capabilities,
        'specializations': specializations,
        'template': template_name,
    }


def post_template_create_sync(template_path: Path) -> bool:
    """Synchronous wrapper for post_template_create."""
    return asyncio.run(post_template_create(template_path))
```

---

## Usage Examples

### Example 1: Integrating with task-work

```python
# In your task_work.py command handler

from guardkit.knowledge.hooks.task_work_hook import pre_task_work_sync

def execute_task_work(task_id: str):
    # Load task from .tasks/
    task = load_task(task_id)
    
    # Get Graphiti context
    graphiti_context = pre_task_work_sync(
        task_id=task.id,
        description=task.description,
        tech_stack=task.tech_stack,
        feature_id=task.feature_id,
        complexity=task.complexity,
    )
    
    # Inject into system prompt
    if graphiti_context:
        system_prompt = f"""
{base_system_prompt}

{graphiti_context}
"""
    else:
        system_prompt = base_system_prompt
    
    # Continue with normal task execution...
```

### Example 2: Capturing review decisions

```python
# In your task_review.py command handler

from guardkit.knowledge.hooks.task_review_hook import post_task_review_sync

def handle_review_decision(task, findings, user_choice):
    # Process user's choice (Accept/Implement/Skip)
    
    if user_choice == "implement":
        # Create follow-up tasks
        spawned_tasks = create_tasks_from_recommendations(findings.recommendations)
        spawned_task_ids = [t.id for t in spawned_tasks]
    else:
        spawned_task_ids = []
    
    # Capture the decision
    post_task_review_sync(
        task_id=task.id,
        review_type="code_review",
        findings_summary=findings.summary,
        recommendations=findings.recommendations,
        decision=user_choice.lower(),  # "accept" | "implement" | "skip"
        spawned_tasks=spawned_task_ids,
        categories=findings.categories,
        severity_distribution={
            "critical": len([f for f in findings.items if f.severity == "critical"]),
            "major": len([f for f in findings.items if f.severity == "major"]),
            "minor": len([f for f in findings.items if f.severity == "minor"]),
        },
    )
```

### Example 3: CLI initialization

```python
# In your CLI entry point

import asyncio
from guardkit.knowledge.graphiti_client import init_graphiti

async def startup():
    # Initialize Graphiti on CLI startup
    await init_graphiti()

def main():
    asyncio.run(startup())
    # Continue with CLI...
```

---

## Testing Strategy

### Manual Testing Checklist

1. **Start Graphiti**
   ```bash
   ./scripts/start_graphiti.sh
   ```

2. **Verify Connection**
   ```bash
   guardkit graphiti status
   ```

3. **Run a task and check capture**
   ```bash
   guardkit task-work TASK-001
   # ... complete task ...
   guardkit task-complete TASK-001
   
   # Verify episode was captured
   guardkit graphiti query "task_outcomes"
   ```

4. **Test context retrieval**
   ```bash
   # Run a similar task
   guardkit task-work TASK-002
   # Should see context from TASK-001 in prompt
   ```

### Validation Metrics

Track these to validate the integration is valuable:

1. **Context Relevance**: Are the retrieved facts actually useful?
2. **Task Success Rate**: Does context improve task completion?
3. **Pattern Discovery**: Are useful patterns being captured?
4. **Query Latency**: Is context retrieval fast enough (<500ms)?

---

## Rollout Plan

### Phase 0: System Context Seeding (CRITICAL - Day 1)

- [ ] Start Graphiti Docker container
- [ ] Run `seed_system_context.py` to populate baseline knowledge
- [ ] Verify seeding with test queries
- [ ] **This MUST happen before any development work**

See: `graphiti-system-context-seeding.md` for the full seeding script.

### Phase 0.5: Session Context Loading (Day 1-2)

- [ ] Implement `load_critical_context()` function
- [ ] Add context injection to command entry points
- [ ] Test that sessions receive system context

### Phase 1: Basic Integration (Days 2-3)

- [ ] Create `guardkit/knowledge/` module structure
- [ ] Implement `graphiti_client.py`
- [ ] Implement `schemas.py`
- [ ] Implement `episode_capture.py`
- [ ] Add `post_task_complete` hook
- [ ] Test episode capture manually

### Phase 2: Context Retrieval (Days 2-3)

- [ ] Implement `context_builder.py`
- [ ] Add `pre_task_work` hook
- [ ] Test context injection
- [ ] Tune context budget allocation

### Phase 3: Full Command Coverage (Days 3-4)

- [ ] Add `post_task_review` hook
- [ ] Add `post_template_create` hook
- [ ] Add `pre_feature_plan` hook
- [ ] Add refinement tracking

### Phase 4: Evaluation (Days 4-5)

- [ ] Run through 5-10 tasks with integration
- [ ] Evaluate context relevance
- [ ] Document findings
- [ ] Decide on DeepAgents middleware investment

---

## Configuration Reference

### Full Configuration File

```yaml
# config/graphiti.yaml

graphiti:
  # Feature flag - set to false to disable without code changes
  enabled: true
  
  # FalkorDB connection
  connection:
    host: "localhost"
    port: 6379
    
  # Embedding configuration
  embedding:
    provider: "openai"
    model: "text-embedding-3-small"
    # Uses OPENAI_API_KEY from environment
    
  # Context retrieval settings
  context:
    enabled: true
    budget_tokens: 4000
    
    # How to allocate budget across categories
    allocation:
      similar_outcomes: 0.30    # What worked before
      relevant_patterns: 0.25   # Applicable patterns
      architecture: 0.20        # System context
      warnings: 0.15            # What to avoid
      meta: 0.10                # Task-specific history
      
  # Episode capture settings
  capture:
    task_outcomes: true
    review_decisions: true
    feature_completions: true
    
    # Turn-level capture (more granular, more storage)
    turn_level:
      enabled: false
      complexity_threshold: 7
      on_failure: true
      
  # Data retention (rolling window)
  retention:
    task_outcomes: "6_months"
    review_decisions: "6_months"
    feature_completions: "12_months"
    turn_level: "3_months"
    
  # Group ID configuration
  groups:
    # These match the group_ids used in queries
    task_outcomes: "task_outcomes"
    review_decisions: "review_decisions"
    successful_fixes: "successful_fixes"
    failed_approaches: "failed_approaches"
    feature_completions: "feature_completions"
    project_architecture: "project_architecture"
    agent_definitions: "agent_definitions"
    # Pattern groups are dynamic: patterns_{tech_stack}
```

---

## Dependencies

Add to `pyproject.toml` or `requirements.txt`:

```toml
[project.optional-dependencies]
knowledge = [
    "graphiti-core[falkordb]>=0.5.0",
    "pyyaml>=6.0",
]
```

Or:

```
# requirements-knowledge.txt
graphiti-core[falkordb]>=0.5.0
pyyaml>=6.0
```

---

## Appendix: Group ID Reference

| Group ID | Purpose | Captured By |
|----------|---------|-------------|
| `task_outcomes` | Completed task outcomes | `/task-complete` |
| `review_decisions` | Review findings + decisions | `/task-review` |
| `successful_fixes` | Refinements that worked | `/task-refine` (success) |
| `failed_approaches` | Refinements that failed | `/task-refine` (failure) |
| `feature_completions` | Feature-level outcomes | `/feature-complete` |
| `project_architecture` | System architecture | Manual / init |
| `service_dependencies` | Service relationships | Manual / init |
| `agent_definitions` | Agent capabilities | `/agent-enhance` |
| `patterns_{stack}` | Stack-specific patterns | `/template-create` |
| `task_{id}_turns` | Turn-level for specific task | Selective capture |

---

## Next Steps After Prototype

If the prototype validates the approach:

1. **Measure Impact**: Track task success rate, iteration count, context usage
2. **Refine Schemas**: Adjust episode schemas based on what's actually useful
3. **Tune Queries**: Optimize group_id combinations for best context
4. **Plan DeepAgents Migration**: Use learnings to design the middleware properly
5. **Consider MCP Server**: Evaluate if Graphiti MCP server is better than SDK integration

If the prototype doesn't add value:

1. **Analyze Why**: Is it the data, the queries, or the concept?
2. **Simplify**: Maybe just pattern/agent sync is valuable without full episode tracking
3. **Pivot**: Consider simpler approaches (local SQLite, structured JSON)
