# Template Create Architecture

This document describes the architecture of the `/template-create` command, including the evolution from heuristic-only analysis to AI-powered multi-phase analysis.

## Overview

The `/template-create` command analyzes a codebase and generates a template package including:
- `manifest.json` - Template metadata
- `settings.json` - Template configuration
- `CLAUDE.md` - AI assistant instructions
- `templates/` - Code templates extracted from the codebase
- `agents/` - Specialized AI agent definitions

## Architecture Evolution

### Version 1: Single-Phase AI (main branch - stable)

The original design used AI only in Phase 5 for agent generation.

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN BRANCH PATTERN                       │
│                  (Single-Phase AI Invocation)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: Codebase Analysis                                 │
│    └── HeuristicAnalyzer (NO AI)                           │
│        ├── File pattern detection                          │
│        ├── Framework detection via config files            │
│        └── Fixed confidence score (75%)                    │
│                                                             │
│  Phases 2-4: Manifest, Settings, Templates                  │
│    └── Deterministic processing                            │
│                                                             │
│  Phase 4: Save checkpoint "templates_generated"             │
│                                                             │
│  Phase 5: Agent Recommendation (AI INVOCATION)              │
│    └── AgentBridgeInvoker.invoke()                         │
│        ├── Exit 42 → Claude invokes agent                  │
│        ├── Resume with cached response                     │
│        └── Parse agent specs, generate stubs               │
│                                                             │
│  Phases 6-9: Write agents, CLAUDE.md, package assembly      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Code (main branch):**
```python
# Phase 1: Heuristic only
analyzer = CodebaseAnalyzer(
    max_files=10,
    bridge_invoker=None  # No AI in Phase 1
)

# Phase 5: AI invocation
generator = AIAgentGenerator(
    inventory,
    ai_invoker=self.agent_invoker  # AI here only
)
```

**Characteristics:**
- Simple, single checkpoint-resume cycle
- Lower quality analysis (75% fixed confidence)
- Basic pattern detection
- Reliable agent generation

---

### Version 2: Multi-Phase AI (progressive-disclosure branch - evolved)

TASK-ENH-D960 introduced AI-powered codebase analysis in Phase 1, significantly improving template quality.

```
┌─────────────────────────────────────────────────────────────┐
│              PROGRESSIVE-DISCLOSURE PATTERN                  │
│               (Multi-Phase AI Invocation)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: AI Codebase Analysis (AI INVOCATION #1)           │
│    ├── Save checkpoint "pre_ai_analysis"                   │
│    └── AgentBridgeInvoker.invoke()                         │
│        ├── Exit 42 → Claude invokes architectural-reviewer │
│        ├── Resume with cached response                     │
│        └── Rich analysis (98% confidence, 9 patterns, etc) │
│                                                             │
│  Phases 2-4: Manifest, Settings, Templates                  │
│    └── Uses rich AI analysis for better output             │
│                                                             │
│  Phase 4: Save checkpoint "templates_generated"             │
│                                                             │
│  Phase 5: Agent Recommendation (AI INVOCATION #2)           │
│    ├── clear_cache() ← CRITICAL for multi-phase pattern   │
│    └── AgentBridgeInvoker.invoke()                         │
│        ├── Exit 42 → Claude invokes agent                  │
│        ├── Resume with NEW cached response                 │
│        └── Parse agent specs, generate stubs               │
│                                                             │
│  Phases 6-9: Write agents, CLAUDE.md, package assembly      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Code (progressive-disclosure branch):**
```python
# Phase 1: AI-powered analysis
self._save_checkpoint("pre_ai_analysis", phase=WorkflowPhase.PHASE_1)
analyzer = CodebaseAnalyzer(
    max_files=10,
    bridge_invoker=self.agent_invoker  # AI in Phase 1
)

# Phase 5: Clear cache, then AI invocation
def _phase5_agent_recommendation(self, analysis):
    self.agent_invoker.clear_cache()  # Enable new AI request
    generator = AIAgentGenerator(
        inventory,
        ai_invoker=self.agent_invoker
    )
```

**Characteristics:**
- Two checkpoint-resume cycles (Phase 1, Phase 5)
- High quality analysis (98% dynamic confidence)
- Rich pattern detection (9 patterns, 6 layers, 20 example files)
- Code smell detection and specific improvements
- Requires cache clearing between phases

---

## Quality Comparison

| Aspect | Heuristic (V1) | AI-Powered (V2) |
|--------|---------------|-----------------|
| Confidence Score | 75% (fixed) | 98% (dynamic) |
| Patterns Detected | Basic (folder names) | 9 detailed patterns |
| Layers | Generic detection | 6 layers with descriptions |
| Example Files | Simple selection | 20 files with patterns & concepts |
| Quality Assessment | 70/100 (fixed) | 78/100 with specific issues |
| Code Smells | None detected | 4 specific issues identified |
| Improvements | Generic suggestions | Specific, actionable items |

---

## AgentBridgeInvoker Pattern

The `AgentBridgeInvoker` implements the checkpoint-resume pattern for Python→Claude agent invocation.

### Single-Phase Pattern (V1)

```python
class AgentBridgeInvoker:
    def __init__(self):
        self._cached_response = None  # Single cache

    def invoke(self, agent_name, prompt):
        if self._cached_response is not None:
            return self._cached_response  # Return cached
        # Write request, exit 42

    def load_response(self):
        # Load from file, set _cached_response
```

### Multi-Phase Pattern (V2)

```python
class AgentBridgeInvoker:
    def __init__(self):
        self._cached_response = None

    def invoke(self, agent_name, prompt):
        if self._cached_response is not None:
            return self._cached_response
        # Write request, exit 42

    def load_response(self):
        # Load from file, set _cached_response

    def clear_cache(self):  # NEW in V2
        """Clear cached response for next phase's AI invocation."""
        self._cached_response = None
```

---

## Checkpoint Flow

### V1 (Single-Phase AI)

```
Start → Phase 1 (heuristic) → Phase 2-4 → [CHECKPOINT] → Phase 5 (AI) → Exit 42
                                                              ↓
Resume ←──────────────────────────────────────────────────────┘
   └→ Phase 5 (cached) → Phase 6-9 → Complete
```

### V2 (Multi-Phase AI)

```
Start → [CHECKPOINT] → Phase 1 (AI) → Exit 42
                            ↓
Resume ←────────────────────┘
   └→ Phase 1 (cached) → Phase 2-4 → [CHECKPOINT] → Phase 5 (AI) → Exit 42
                                                         ↓
   Resume ←──────────────────────────────────────────────┘
      └→ Phase 5 (cached) → Phase 6-9 → Complete
```

---

## State Management

### Checkpoint Data

```python
phase_data = {
    "qa_answers": ...,
    "analysis": {...},      # CodebaseAnalysis (rich in V2)
    "manifest": {...},
    "settings": {...},
    "templates": [...],
    "agent_inventory": [...],
    "agents": [...]
}
```

### Resume Routing

```python
def run(self):
    if self.config.resume:
        state = self.state_manager.load_state()
        phase = state.phase

        if phase == WorkflowPhase.PHASE_1:
            return self._run_from_phase_1()  # V2 only
        elif phase == WorkflowPhase.PHASE_7:
            return self._run_from_phase_7()
        else:
            return self._run_from_phase_5()  # Default (V1 compatible)
```

---

## File Reference

| File | Purpose |
|------|---------|
| `installer/global/commands/lib/template_create_orchestrator.py` | Main orchestrator |
| `installer/global/lib/agent_bridge/invoker.py` | AgentBridgeInvoker class |
| `installer/global/lib/agent_bridge/state_manager.py` | Checkpoint state management |
| `installer/global/lib/codebase_analyzer/ai_analyzer.py` | CodebaseAnalyzer |
| `installer/global/lib/codebase_analyzer/agent_invoker.py` | HeuristicAnalyzer fallback |
| `installer/global/lib/agent_generator/agent_generator.py` | AIAgentGenerator |

---

## Future Considerations

### Request-Keyed Caching

For more robust multi-phase AI, consider implementing request-keyed caching:

```python
class AgentBridgeInvoker:
    def __init__(self):
        self._response_cache: Dict[str, str] = {}

    def _cache_key(self, agent_name, prompt):
        return hashlib.sha256(f"{agent_name}:{prompt}".encode()).hexdigest()[:16]

    def invoke(self, agent_name, prompt):
        key = self._cache_key(agent_name, prompt)
        if key in self._response_cache:
            return self._response_cache[key]
        # Write request, exit 42
```

This would eliminate the need for explicit `clear_cache()` calls.

### Additional AI Phases

If future phases need AI invocation, follow the pattern:
1. Save checkpoint before the phase
2. Call `clear_cache()` at phase entry
3. Invoke AI via bridge
4. Handle exit 42 and resume

---

## Related Tasks

- **TASK-ENH-D960**: Enabled AI in Phase 1 (quality improvement)
- **TASK-FIX-29C1**: Clear cache fix for multi-phase AI
- **TASK-REV-993B**: Review that identified the cache issue
- **TASK-IMP-D93B**: Progressive disclosure implementation
