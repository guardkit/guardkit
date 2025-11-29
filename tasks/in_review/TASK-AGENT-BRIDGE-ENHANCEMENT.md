# TASK-AGENT-BRIDGE-ENHANCEMENT: Implement Agent Bridge for Agent Enhancement

**Status**: 🔴 Blocked - Requires architectural decision  
**Priority**: P2 - Enhancement (not blocking core functionality)  
**Created**: 2025-11-15  
**Related**: TASK-ENHANCE-AGENT-FILES (partial implementation exists)

---

## Problem Statement

Phase 7.5 (Agent Enhancement) is currently disabled because the implementation assumes a direct AI client exists, but the Taskwright architecture uses the **agent bridge pattern** for all AI interactions.

### Current State
- ❌ Phase 7.5 temporarily disabled in orchestrator
- ✅ Agent files created with basic descriptions (3/10 quality)
- ✅ `AgentEnhancer` implementation exists but can't be used
- ⚠️ No regression - templates still work correctly

### Desired State
- ✅ Agent files enhanced with template references, examples, and best practices (9/10 quality)
- ✅ Uses agent bridge pattern (consistent with `architectural-reviewer`)
- ✅ Follows AI-first architecture (no hard-coded mappings)

---

## Background

### What the AgentEnhancer Does

The `AgentEnhancer` (already implemented in `installer/global/lib/template_creation/agent_enhancer.py`) performs two AI-powered operations:

1. **Template Discovery** (Phase 1)
   - Analyzes agent metadata (name, description, technologies)
   - Identifies relevant templates from the template collection
   - Assigns priority levels (primary, secondary, tertiary)
   - Returns: `List[TemplateRelevance]`

2. **Content Generation** (Phase 2)
   - Reads identified template code
   - Generates comprehensive documentation sections:
     - Purpose (1-2 sentences)
     - When to Use (3-4 scenarios)
     - Related Templates (2-3 primary templates with explanations)
     - Example Pattern (code snippet + explanation)
     - Best Practices (3-5 practices with examples)
   - Returns: Enhanced markdown content (750-1050 words)

### Why It Failed

The `AgentEnhancer` was designed to use an `AIClient` with a `generate(prompt, max_tokens)` method. However:

```python
# In orchestrator - tried to import from non-existent location
_ai_client_module = importlib.import_module('installer.global.lib.ai.ai_client')
AIClient = _ai_client_module.AIClient
ai_client = AIClient()  # Would raise NotImplementedError even if imported
```

The `AIClient` at `installer.global.lib.template_generator.ai_client` is a mock that raises `NotImplementedError` - it's not meant for production use.

### The Agent Bridge Pattern

The Taskwright architecture uses **agent bridge pattern** for all AI interactions:

```python
# How architectural-reviewer works:
1. Write .agent-request.json with prompt
2. Exit with code 42 (signals "agent needed")
3. External agent (Claude Code) processes request
4. Agent writes .agent-response.json
5. Resume orchestrator, read response
6. Continue workflow
```

This pattern is already used by:
- `architectural-reviewer` (codebase analysis)
- `complexity-evaluator` (task complexity assessment)

---

## Implementation Approach: Agent Bridge Integration

**Architecture**: Create `agent-content-enhancer` agent

**Why This Approach**:
- ✅ Follows existing system architecture
- ✅ Consistent with other agents
- ✅ Reuses agent bridge infrastructure
- ✅ Agent can use full Claude context window
- ✅ Supports checkpoint-resume pattern
- ✅ Future-proof for additional AI-powered phases

**Complexity**:
- ⚠️ More complex than direct API integration
- ⚠️ Requires creating new agent
- ⚠️ Two-phase workflow (exit, resume)

**Implementation Steps**:

1. **Create Agent Definition** (`installer/global/agents/agent-content-enhancer.md`)
   ```markdown
   ---
   name: agent-content-enhancer
   description: Enhances agent files with template-specific content
   priority: 8
   technologies: [markdown, documentation]
   ---
   
   # Agent Content Enhancer
   
   Specialized agent for enhancing agent documentation files.
   
   ## Capabilities
   - Template relevance discovery (AI-powered pattern matching)
   - Code analysis and pattern extraction
   - Documentation generation with examples
   
   ## Input Format
   Receives `.agent-request.json` with:
   - Agent metadata (name, description, technologies)
   - Available templates list
   
   ## Output Format
   Returns `.agent-response.json` with:
   - Template relevance analysis
   - Enhanced content sections
   ```

2. **Modify AgentEnhancer** to use bridge pattern:
   ```python
   class AgentEnhancer:
       def __init__(self, bridge_invoker):
           self.bridge = bridge_invoker
       
       def enhance_agent_file(self, agent_file, all_templates):
           # Build request payload
           request = {
               "agent_metadata": ...,
               "available_templates": ...,
               "operation": "enhance"
           }
           
           # Invoke agent via bridge
           response = self.bridge.invoke_agent(
               agent_name="agent-content-enhancer",
               request_data=request
           )
           
           # Parse response and update agent file
           ...
   ```

3. **Update Orchestrator** to use bridge:
   ```python
   def _phase7_5_enhance_agents(self, output_path):
       # Create bridge invoker for agent enhancement
       enhancement_invoker = AgentBridgeInvoker(
           phase=7.5,
           phase_name="agent_enhancement"
       )
       
       # Initialize enhancer with bridge
       enhancer = AgentEnhancer(enhancement_invoker)
       
       # May exit with code 42 if agent invocation needed
       results = enhancer.enhance_all_agents(output_path)
       ...
   ```

4. **Add Checkpoint Support**:
   - Save state before Phase 7.5
   - Resume after agent response received
   - Similar to Phase 6 (agent generation) pattern

**Estimated Effort**: ~8-12 hours  
**Risk**: Low (follows proven pattern)

---

## Acceptance Criteria

When implemented, the system should:

- [ ] Agent files enhanced with rich content (9/10 quality)
- [ ] Template references based on AI analysis (not hard-coded)
- [ ] Code examples extracted from actual templates
- [ ] Best practices derived from template patterns
- [ ] Follows chosen architecture pattern consistently
- [ ] No errors or warnings during template creation
- [ ] Checkpoint-resume works if using agent bridge
- [ ] Documentation updated with enhancement process
- [ ] Tests added for enhancement workflow

---

## Files Involved

**Existing**:
- `installer/global/lib/template_creation/agent_enhancer.py` (needs bridge integration)
- `installer/global/commands/lib/template_create_orchestrator.py` (Phase 7.5 disabled)

**New**:
- `installer/global/agents/agent-content-enhancer.md` (agent definition)
- Tests for bridge integration



---

## Related Documentation

- Agent Bridge Pattern: `installer/global/lib/agent_bridge/README.md`
- Architectural Reviewer Example: `installer/global/lib/codebase_analyzer/agent_invoker.py`
- Agent Enhancer Implementation: `installer/global/lib/template_creation/agent_enhancer.py`
- TASK-ENHANCE-AGENT-FILES: Original enhancement task (partial completion)

---

## Notes

- Phase 7.5 is currently disabled with a clear message
- Template creation works correctly without enhancement
- No regression - agents still created with basic descriptions
- Enhancement is an **optional quality improvement**, not a blocker
- The `AgentEnhancer` code is already written and well-designed
- Architectural decision made: Use agent bridge pattern

---

**Next Action**: Begin implementation following steps above
