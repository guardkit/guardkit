# TASK-PHASE-5-CHECKPOINT: AI Agent Creation

**Task ID**: TASK-PHASE-5-CHECKPOINT
**Title**: Implement AI-Powered Agent Creation (Not Just Discovery)
**Status**: BACKLOG
**Priority**: HIGH
**Complexity**: 6/10 (Medium)
**Estimated Hours**: 2-3
**Phase**: 4 of 8 (Template-Create Redesign)

---

## Problem Statement

### Current Issue

Phase 5 uses hard-coded pattern detection that only identifies 1 agent (14% coverage) instead of 7-9 agents (78-100% coverage).

**Evidence:**
```
Agents detected: 1 (testing-specialist)
Expected: 7-9 agents
Missing: Repository, Service, CQRS, MVVM, ErrorOr, Navigation, Domain specialists
```

### Critical Principle: CREATE, Not Just Recommend

Per AGENT-STRATEGY-high-level-design.md:
> "Claude Code should **create appropriate agents** based on codebase analysis, not just discover existing ones."

This phase must CREATE agents to fill gaps, not just recommend from a list.

---

## Solution Design

### AI-First Agent Creation Flow

1. **Inventory existing agents** (user custom > template > global)
2. **Analyze codebase** for needed capabilities
3. **Identify gaps** between existing and needed
4. **CREATE new agents** to fill gaps
5. **Return both** "use existing" and "create new" lists

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `installer/global/commands/lib/template_create_orchestrator.py` | MODIFY | Replace hard-coded detection with AI creation |

---

## Implementation Details

### Phase 5 with AI Agent Creation

```python
# In template_create_orchestrator.py

from docs.proposals.template_create.AI_PROMPTS_SPECIFICATION import (
    PHASE_4_AGENT_CREATION_PROMPT,
    PHASE_4_CONFIDENCE_THRESHOLD
)


def _phase5_agent_creation(
    self,
    analysis: CodebaseAnalysis,
    output_path: Path
) -> AgentCreationResult:
    """
    Phase 5: AI-Powered Agent Creation with checkpoint-resume.

    Key principle: CREATE agents, don't just recommend.

    Args:
        analysis: Codebase analysis from Phase 1
        output_path: Template output directory

    Returns:
        AgentCreationResult with existing and new agents

    Raises:
        CheckpointRequested: If external agent invocation needed
    """
    self._print_phase_header("Phase 5: AI Agent Creation")

    # Check if resuming with response
    if self.checkpoint_manager.has_agent_response():
        self._print_info("  Resuming from checkpoint...")
        return self._complete_phase_5_from_response(analysis)

    # Inventory existing agents
    self._print_info("  📦 Scanning existing agents...")
    existing_agents = self._inventory_existing_agents()

    self._print_info(f"    User custom: {len(existing_agents['user_custom'])}")
    self._print_info(f"    Template: {len(existing_agents['template'])}")
    self._print_info(f"    Global: {len(existing_agents['global'])}")

    # Build creation prompt
    self._print_info("  🤖 Requesting AI agent creation...")

    prompt = PHASE_4_AGENT_CREATION_PROMPT.format(
        codebase_analysis=json.dumps(analysis.to_dict(), indent=2),
        user_custom_agents=json.dumps(existing_agents['user_custom'], indent=2),
        template_agents=json.dumps(existing_agents['template'], indent=2),
        global_agents=json.dumps(existing_agents['global'], indent=2)
    )

    # Create agent request
    request = {
        "request_id": str(uuid.uuid4()),
        "version": "1.0",
        "phase": 5,
        "phase_name": "agent_creation",
        "agent_name": "architectural-reviewer",
        "prompt": prompt,
        "context": {
            "project_path": str(self.project_path),
            "output_path": str(output_path),
            "template_name": self.template_name,
            "mode": "agent_creation"  # Important: creation mode
        },
        "timeout_seconds": 180,  # Longer for complex analysis
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    # Save checkpoint
    state = TemplateCreateState(
        phase=5,
        phase_name="agent_creation",
        checkpoint_name="before_agent_invocation",
        output_path=str(output_path),
        project_path=str(self.project_path),
        template_name=self.template_name,
        phase_data={
            "codebase_analysis": analysis.to_dict(),
            "existing_agents": existing_agents
        }
    )

    self.checkpoint_manager.save_checkpoint(state, request)

    self._print_info("  📝 Request written to: .agent-request.json")
    self._print_info("  🔄 Checkpoint: Resume after agent responds")

    raise CheckpointRequested(
        agent_name="architectural-reviewer",
        phase=5,
        phase_name="agent_creation"
    )


def _inventory_existing_agents(self) -> Dict[str, List[Dict]]:
    """
    Scan all agent sources in priority order.

    Returns:
        Dict with user_custom, template, global agent lists
    """
    inventory = {
        "user_custom": [],
        "template": [],
        "global": []
    }

    # 1. User custom agents (HIGHEST priority)
    user_agents_path = Path(".claude/agents")
    if user_agents_path.exists():
        for agent_file in user_agents_path.glob("*.md"):
            metadata = self._parse_agent_metadata(agent_file)
            if metadata:
                inventory["user_custom"].append(metadata)

    # 2. Template agents (if using existing template)
    if self.base_template:
        template_agents_path = Path(f"installer/local/templates/{self.base_template}/agents")
        if template_agents_path.exists():
            for agent_file in template_agents_path.glob("*.md"):
                metadata = self._parse_agent_metadata(agent_file)
                if metadata:
                    inventory["template"].append(metadata)

    # 3. Global built-in agents
    global_agents_path = Path("installer/global/agents")
    if global_agents_path.exists():
        for agent_file in global_agents_path.glob("*.md"):
            metadata = self._parse_agent_metadata(agent_file)
            if metadata:
                inventory["global"].append(metadata)

    return inventory


def _parse_agent_metadata(self, agent_file: Path) -> Optional[Dict]:
    """Parse agent metadata from markdown file."""
    try:
        content = agent_file.read_text(encoding='utf-8')

        # Parse YAML frontmatter
        if content.startswith('---'):
            end = content.find('---', 3)
            if end > 0:
                import yaml
                frontmatter = yaml.safe_load(content[3:end])
                return {
                    "name": frontmatter.get("name", agent_file.stem),
                    "description": frontmatter.get("description", ""),
                    "tools": frontmatter.get("tools", []),
                    "tags": frontmatter.get("tags", []),
                    "path": str(agent_file)
                }
    except Exception as e:
        self.logger.warning(f"Failed to parse {agent_file}: {e}")

    return None


def _complete_phase_5_from_response(
    self,
    analysis: CodebaseAnalysis
) -> AgentCreationResult:
    """
    Complete Phase 5 using agent response from checkpoint.

    Args:
        analysis: Codebase analysis for context

    Returns:
        AgentCreationResult with existing and created agents
    """
    response = self.checkpoint_manager.load_agent_response()

    if not response or response.get("status") != "success":
        error_msg = response.get("error_message", "Unknown error") if response else "No response"
        self._print_warning(f"  ⚠️  Agent creation failed: {error_msg}")
        return self._fallback_to_basic_agents()

    try:
        result_data = json.loads(response.get("response", "{}"))

        # Check confidence
        confidence = result_data.get("confidence", 0)
        if confidence < PHASE_4_CONFIDENCE_THRESHOLD:
            self._print_warning(f"  ⚠️  Low confidence ({confidence:.0%}), using basic agents")
            return self._fallback_to_basic_agents()

        # Parse result
        use_existing = [
            ExistingAgent(
                name=a["name"],
                source=a["source"],
                reason=a["reason"]
            )
            for a in result_data.get("use_existing", [])
        ]

        create_new = [
            NewAgent(
                name=a["name"],
                priority=a["priority"],
                rationale=a["rationale"],
                key_patterns=a["key_patterns"],
                example_files=a.get("example_files", []),
                capabilities=a["capabilities"],
                content_outline=a["content_outline"]
            )
            for a in result_data.get("create_new", [])
        ]

        total = len(use_existing) + len(create_new)
        self._print_info(f"  ✓ Agent creation complete (confidence: {confidence:.0%})")
        self._print_info(f"  ✓ Using existing: {len(use_existing)} agents")
        self._print_info(f"  ✓ Creating new: {len(create_new)} agents")
        self._print_info(f"  ✓ Total: {total} agents")

        return AgentCreationResult(
            use_existing=use_existing,
            create_new=create_new,
            total_count=total,
            confidence=confidence
        )

    except (json.JSONDecodeError, KeyError) as e:
        self._print_warning(f"  ⚠️  Failed to parse response: {e}")
        return self._fallback_to_basic_agents()


def _fallback_to_basic_agents(self) -> AgentCreationResult:
    """
    Fallback to basic agent set when AI creation fails.

    Returns minimal set of always-useful agents.
    """
    self._print_info("  Using basic agent set (fallback)")

    basic_agents = [
        ExistingAgent(
            name="architectural-reviewer",
            source="global",
            reason="General architecture review"
        ),
        ExistingAgent(
            name="code-reviewer",
            source="global",
            reason="Code quality review"
        ),
        ExistingAgent(
            name="test-verifier",
            source="global",
            reason="Test execution"
        ),
        ExistingAgent(
            name="testing-specialist",
            source="global",
            reason="Test creation"
        )
    ]

    return AgentCreationResult(
        use_existing=basic_agents,
        create_new=[],
        total_count=4,
        confidence=0.5  # Low confidence for fallback
    )


def _run_from_phase_5(self) -> OrchestrationResult:
    """
    Resume orchestration from Phase 5 checkpoint.

    Called when orchestrator detects Phase 5 checkpoint and agent response.
    """
    self._print_info("Resuming from Phase 5 checkpoint...")

    # Load state
    state = self.checkpoint_manager.load_checkpoint()
    if not state:
        raise OrchestrationError("Failed to load checkpoint state")

    output_path = Path(state.output_path)

    # Restore analysis from phase data
    analysis = CodebaseAnalysis.from_dict(
        state.phase_data.get("codebase_analysis", {})
    )

    # Complete Phase 5 with response
    agent_result = self._complete_phase_5_from_response(analysis)

    # Continue with Phase 6 (agent file writing)
    return self._continue_from_phase_6(agent_result, output_path)
```

### Data Classes for Agent Creation

```python
# In models.py

@dataclass
class ExistingAgent:
    """Agent that already exists and should be used."""
    name: str
    source: str  # "custom", "template", or "global"
    reason: str


@dataclass
class NewAgent:
    """Agent to be created."""
    name: str
    priority: int
    rationale: str
    key_patterns: List[str]
    example_files: List[str]
    capabilities: List[str]
    content_outline: Dict[str, Any]


@dataclass
class AgentCreationResult:
    """Result of agent creation phase."""
    use_existing: List[ExistingAgent]
    create_new: List[NewAgent]
    total_count: int
    confidence: float

    def get_all_agent_names(self) -> List[str]:
        """Get all agent names (existing + new)."""
        existing = [a.name for a in self.use_existing]
        new = [a.name for a in self.create_new]
        return existing + new
```

---

## Acceptance Criteria

### Functional

- [ ] Inventories agents from all 3 sources (user, template, global)
- [ ] AI creates agents to fill capability gaps
- [ ] Returns 7-9 total agents for typical project
- [ ] Respects priority hierarchy (user custom > template > global)
- [ ] Creates content outlines for new agents (used by Phase 7.5)

### Quality

- [ ] Test coverage >= 90%
- [ ] Handles missing directories gracefully
- [ ] Fallback works when AI fails

### Output

- [ ] All major patterns have agent coverage
- [ ] New agents have complete content outlines
- [ ] No duplicate agents

---

## Test Specifications

### Integration Tests

```python
# tests/integration/test_phase_5_agent_creation.py

class TestPhase5AgentCreation:
    """Integration tests for Phase 5 agent creation."""

    def test_creates_agents_for_patterns(self, tmp_path):
        """Test that AI creates agents for detected patterns."""
        # Setup: Analysis with multiple patterns
        analysis = CodebaseAnalysis(
            patterns=[
                PatternDetection(name="Repository", confidence=0.95, ...),
                PatternDetection(name="ErrorOr", confidence=0.90, ...),
                PatternDetection(name="MVVM", confidence=0.88, ...)
            ],
            ...
        )

        # Mock successful AI response
        mock_response = {
            "use_existing": [
                {"name": "architectural-reviewer", "source": "global", "reason": "..."}
            ],
            "create_new": [
                {
                    "name": "repository-pattern-specialist",
                    "priority": 9,
                    "rationale": "Repository pattern detected",
                    "key_patterns": ["Repository"],
                    "capabilities": ["Create repositories"],
                    "content_outline": {...}
                },
                {
                    "name": "erroror-pattern-specialist",
                    "priority": 8,
                    ...
                }
            ],
            "confidence": 0.92
        }

        # Execute
        result = orchestrator._complete_phase_5_from_response(analysis)

        # Verify
        assert result.total_count >= 7
        assert len(result.create_new) >= 2
        assert any(a.name == "repository-pattern-specialist" for a in result.create_new)

    def test_respects_user_custom_priority(self, tmp_path):
        """Test that user custom agents take priority."""
        # Setup: User has custom agent
        user_agent_dir = tmp_path / ".claude" / "agents"
        user_agent_dir.mkdir(parents=True)
        (user_agent_dir / "my-custom-specialist.md").write_text(
            "---\nname: my-custom-specialist\n---"
        )

        # Mock response should NOT recreate user's agent
        # ... test implementation

    def test_fallback_on_low_confidence(self):
        """Test fallback to basic agents on low confidence."""
        mock_response = {
            "confidence": 0.45,  # Below threshold
            ...
        }

        result = orchestrator._complete_phase_5_from_response(...)

        # Should use basic set
        assert result.total_count == 4
        assert len(result.create_new) == 0


class TestAgentInventory:
    """Tests for agent inventory scanning."""

    def test_scans_all_sources(self, tmp_path):
        """Test scanning all three agent sources."""
        # Create agents in each location
        # ...

        inventory = orchestrator._inventory_existing_agents()

        assert len(inventory["user_custom"]) == expected_user
        assert len(inventory["template"]) == expected_template
        assert len(inventory["global"]) == expected_global
```

---

## Dependencies

### Depends On
- TASK-AGENT-BRIDGE-COMPLETE (Phase 2) - needs checkpoint manager
- TASK-PHASE-1-CHECKPOINT (Phase 3) - needs analysis results

### Blocks
- TASK-PHASE-7-5-CHECKPOINT (Phase 5) - needs agent list with content outlines

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Agents created | 7-9 total | manifest.json |
| Pattern coverage | 78-100% | All major patterns have agents |
| Confidence | 0.85+ | AI response |
| User agents respected | 100% | Never recreated |

---

## AI Integration Details

### Agent Used
`architectural-reviewer` (in agent creation mode)

### Prompt Reference
See `AI-PROMPTS-SPECIFICATION.md`, Phase 4 section

### Key Difference from Discovery
- **Discovery**: Find existing agents that match
- **Creation**: CREATE new agents to fill gaps

### Output Structure
Must include:
- `use_existing`: Agents from inventory to use
- `create_new`: NEW agents with content outlines for Phase 7.5

### Confidence Threshold
- 0.70 minimum for auto-proceed
- Below 0.70 triggers fallback to basic 4-agent set

---

## Notes

- This is called "Phase 5" in the proposal but is the 4th implementation task
- The content_outline in created agents is used by Phase 7.5 for enhancement
- Priority scores (1-10) determine which agents are most important

---

**Created**: 2025-11-18
**Phase**: 4 of 8 (Template-Create Redesign)
**Related**: AI-PROMPTS-SPECIFICATION.md, AGENT-STRATEGY-high-level-design.md
