---
id: TASK-FIX-AGENT-GEN
title: Ensure Agent Generation for Complex Codebases
status: backlog
task_type: implementation
created: 2025-12-10T16:30:00Z
updated: 2025-12-10T16:30:00Z
priority: high
tags: [template-create, agent-generation, bug-fix]
complexity: 6
implementation_mode: task-work
conductor_workspace: template-fix-wave1-agent
wave: 1
parent_review: TASK-REV-TC01
---

# Ensure Agent Generation for Complex Codebases

## Problem Statement

Phase 5 (Agent Recommendation) is failing silently for complex codebases, resulting in no agents being generated. Phase 7 then skips writing since `self.agents` is empty.

**Observed Behavior**: MyDrive template generated with no `agents/` directory.

## Root Cause

The AI-native agent generation in `AIAgentGenerator` can fail due to:
1. AI response parsing failures (JSON format issues)
2. AI invocation timeouts
3. Exit code 42 (bridge pattern) not properly resumed
4. No fallback when AI fails (heuristic fallback was deprecated)

The `_fallback_to_hardcoded()` method was marked deprecated but no replacement heuristic was added, so when AI fails, the code returns an empty list instead of falling back.

## Acceptance Criteria

- [ ] Heuristic fallback generates minimum 3 agents when AI fails
- [ ] Agents generated for: language, architecture, primary framework
- [ ] Diagnostic logging shows exactly why agents weren't generated
- [ ] MyDrive template generates at least 3 agents
- [ ] Phase 5 failures logged with actionable error messages
- [ ] Unit tests for heuristic agent generation

## Technical Specification

### File 1: agent_generator.py

**Location**: `installer/global/lib/agent_generator/agent_generator.py`

#### Change 1: Restore heuristic fallback (modify `_identify_capability_needs`, lines 121-148)

```python
def _identify_capability_needs(self, analysis: Any) -> List[CapabilityNeed]:
    """Analyze codebase to identify needed agent capabilities."""
    try:
        needs = self._ai_identify_all_agents(analysis)
        if needs:
            print(f"  ✓ AI identified {len(needs)} capability needs")
            return needs
        else:
            print("  ⚠️  AI returned no capability needs, using heuristic fallback")
            return self._heuristic_identify_agents(analysis)
    except Exception as e:
        print(f"  ⚠️  AI detection failed: {e}")
        print("  → Falling back to heuristic agent generation")
        return self._heuristic_identify_agents(analysis)
```

#### Change 2: Add guaranteed heuristic generation (new method, ~line 456)

Replace deprecated `_fallback_to_hardcoded` with:

```python
def _heuristic_identify_agents(self, analysis: Any) -> List[CapabilityNeed]:
    """
    Generate agent needs using heuristic patterns.

    Always generates at least 3 agents based on detected:
    - Primary language
    - Architecture pattern
    - Framework (if detected)
    """
    needs = []

    # Extract analysis data with multiple fallback paths
    language = getattr(analysis, 'language', None) or \
               getattr(analysis.technology, 'primary_language', None) or 'unknown'

    architecture = getattr(analysis, 'architecture_pattern', None) or \
                  getattr(analysis.architecture, 'architectural_style', None) or 'unknown'

    frameworks = getattr(analysis, 'frameworks', []) or \
                getattr(analysis.technology, 'frameworks', [])

    # 1. Language specialist (always)
    if language and language.lower() != 'unknown':
        lang_name = language.lower().replace('#', 'sharp').replace('+', 'plus')
        needs.append(CapabilityNeed(
            name=f"{lang_name}-specialist",
            description=f"Specialist for {language} development patterns",
            reason=f"Primary language is {language}",
            technologies=[language],
            example_files=[],
            priority=9
        ))

    # 2. Architecture specialist (always)
    if architecture and architecture.lower() != 'unknown':
        arch_name = architecture.lower().replace(' ', '-').replace('/', '-')
        needs.append(CapabilityNeed(
            name=f"{arch_name}-specialist",
            description=f"Specialist for {architecture} architecture patterns",
            reason=f"Uses {architecture} architecture",
            technologies=[architecture],
            example_files=[],
            priority=8
        ))

    # 3. Framework specialist (if detected, up to 2)
    for fw in frameworks[:2]:
        fw_str = str(fw)
        fw_name = fw_str.split()[0].lower().replace('.', '-')
        if fw_name and fw_name not in ['unknown', 'none']:
            needs.append(CapabilityNeed(
                name=f"{fw_name}-specialist",
                description=f"Specialist for {fw_str} framework patterns",
                reason=f"Uses {fw_str} framework",
                technologies=[fw_str],
                example_files=[],
                priority=7
            ))

    # Ensure minimum 3 agents
    if len(needs) < 3:
        needs.append(CapabilityNeed(
            name="general-specialist",
            description="General development patterns specialist",
            reason="Fallback for undetected patterns",
            technologies=[language if language != 'unknown' else 'general'],
            example_files=[],
            priority=5
        ))

    print(f"  ✓ Heuristic identified {len(needs)} capability needs")
    return needs
```

### File 2: template_create_orchestrator.py

**Location**: `installer/global/commands/lib/template_create_orchestrator.py`

#### Change 1: Add diagnostic logging to Phase 5 (modify `_phase5_agent_recommendation`)

Find the Phase 5 method and add logging:

```python
def _phase5_agent_recommendation(self, analysis: Any) -> List[Any]:
    """Phase 5: Recommend and generate custom agents."""
    self._print_phase_header("Phase 5: Agent Recommendation")

    # Diagnostic: Log analysis state
    logger.info(f"Phase 5 starting with analysis: "
                f"language={getattr(analysis.technology, 'primary_language', 'unknown')}, "
                f"architecture={getattr(analysis.architecture, 'architectural_style', 'unknown')}, "
                f"frameworks={len(getattr(analysis.technology, 'frameworks', []))}")

    # ... existing code ...

    # Diagnostic: Log result (add at end of method, before return)
    if agents:
        logger.info(f"Phase 5 complete: Generated {len(agents)} agents")
        for agent in agents:
            logger.debug(f"  - {agent.name} (confidence: {getattr(agent, 'confidence', 'N/A')}%)")
    else:
        logger.warning("Phase 5 complete: No agents generated")
        logger.warning("This may indicate AI failure or no capability gaps detected")

    return agents
```

#### Change 2: Add warning in Phase 7 (modify `_complete_workflow`)

In the workflow where agents are written:

```python
# Phase 7: Agent Writing
if self.agents:
    agent_paths = self._phase7_write_agents(self.agents, output_path)
    # ... existing logging ...
else:
    logger.warning("No agents to write - Phase 5 returned empty list")
    self.warnings.append("No agents generated - check Phase 5 logs for details")
    # Continue with workflow - agents are optional but user should know
```

## Test Cases

1. **AI success**: Verify AI-generated agents are used when available
2. **AI failure**: Verify heuristic fallback produces 3+ agents
3. **AI empty response**: Verify heuristic fallback triggered
4. **Complex codebase**: Verify language + architecture + framework agents generated
5. **Minimal codebase**: Verify at least `general-specialist` created

## Execution

```bash
/task-work TASK-FIX-AGENT-GEN
```

## Verification

```bash
# After implementation, test on MyDrive
cd ~/Projects/MyDrive
/template-create --name mydrive-test

# Verify:
# - agents/ directory exists
# - At least 3 agent files created
# - Agent names reflect detected patterns:
#   - csharp-specialist.md (language)
#   - mvvm-specialist.md (architecture)
#   - maui-specialist.md (framework)
```

## Notes

- The heuristic fallback is a safety net, not a replacement for AI generation
- Users should see clear messaging when heuristics are used
- Heuristic agents are still valuable - they're based on detected patterns
