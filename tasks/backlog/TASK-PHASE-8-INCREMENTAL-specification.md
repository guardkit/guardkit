# TASK-PHASE-8-INCREMENTAL: Incremental Agent Enhancement Workflow

**Task ID**: TASK-PHASE-8-INCREMENTAL
**Priority**: MEDIUM
**Complexity**: 6/10 (Medium Task)
**Estimated Duration**: 5-7 days
**Status**: Specification Complete - Ready for Implementation
**Depends On**: TASK-PHASE-7.5-SIMPLE (can run in parallel but Option 1 is MVP)

---

## Overview

Add incremental agent enhancement workflow that gives users control over which agents to enhance and when. Provides alternative to fully automated Phase 7.5 (Option 1).

**Key Additions**:
- ✅ `--create-agent-tasks` flag for `/template-create` command
- ✅ Phase 8: Create individual tasks for each agent
- ✅ New `/agent-enhance` command for single-agent enhancement
- ✅ Shared modules for code reuse (prompt_builder, parser, applier)

**User Benefits**:
- Control: Enhance agents individually at your own pace
- Prioritization: Work on most important agents first
- Flexibility: Mix automated and manual enhancement
- Transparency: Each agent is a tracked task with clear acceptance criteria

---

## Acceptance Criteria

### 1. Command Flag Addition

- [ ] **AC1.1**: `--create-agent-tasks` flag added to `/template-create` command spec
- [ ] **AC1.2**: Flag documented in command help text
- [ ] **AC1.3**: `OrchestrationConfig` dataclass has `create_agent_tasks: bool = False` field
- [ ] **AC1.4**: Flag parsing works correctly (argparse or equivalent)
- [ ] **AC1.5**: Backward compatible (flag optional, defaults to False)

### 2. Phase 8 Implementation

- [ ] **AC2.1**: `_run_phase_8_create_agent_tasks` method added to orchestrator
- [ ] **AC2.2**: Phase only runs if `config.create_agent_tasks` is True
- [ ] **AC2.3**: Creates one task per agent file
- [ ] **AC2.4**: Task metadata includes agent_file, template_dir, template_name, agent_name
- [ ] **AC2.5**: Returns `PhaseResult` with `tasks_created` count and `task_ids` list
- [ ] **AC2.6**: Logs task IDs and `/task-work` command for user

### 3. `/agent-enhance` Command

- [ ] **AC3.1**: New command file created: `installer/global/commands/agent-enhance.py`
- [ ] **AC3.2**: Command spec created: `installer/global/commands/agent-enhance.md`
- [ ] **AC3.3**: Accepts two path formats: `template/agent` and `/path/to/agent.md`
- [ ] **AC3.4**: Supports `--dry-run` flag (show preview without applying)
- [ ] **AC3.5**: Supports `--strategy` flag (ai|static|hybrid)
- [ ] **AC3.6**: Supports `--verbose` flag (show detailed process)
- [ ] **AC3.7**: Returns correct exit codes (0=success, 1=not found, 2=template error, 3=enhancement error, 4=validation error, 5=permission error)
- [ ] **AC3.8**: Shows clear success/error messages
- [ ] **AC3.9**: Displays enhancement summary (sections added, templates referenced, examples included)

### 4. SingleAgentEnhancer Module

- [ ] **AC4.1**: Module created: `installer/global/lib/agent_enhancement/enhancer.py`
- [ ] **AC4.2**: `SingleAgentEnhancer` class with `__init__(strategy, dry_run, verbose)`
- [ ] **AC4.3**: `enhance(agent_file, template_dir)` method returns `EnhancementResult`
- [ ] **AC4.4**: Three strategies implemented: ai, static, hybrid
- [ ] **AC4.5**: AI strategy uses direct Task tool invocation
- [ ] **AC4.6**: Static strategy uses keyword matching (simple, fast, no AI)
- [ ] **AC4.7**: Hybrid strategy tries AI, falls back to static on failure
- [ ] **AC4.8**: Dry-run mode generates diff without applying
- [ ] **AC4.9**: Verbose mode shows detailed progress

### 5. Shared Modules

- [ ] **AC5.1**: `prompt_builder.py` module created (~100 lines)
- [ ] **AC5.2**: `EnhancementPromptBuilder` class with `build()` method
- [ ] **AC5.3**: Used by both Option 1 and Option 2 (DRY compliance)
- [ ] **AC5.4**: `parser.py` module created (~80 lines)
- [ ] **AC5.5**: `EnhancementParser` class with `parse()` method
- [ ] **AC5.6**: Handles markdown-wrapped JSON, bare JSON
- [ ] **AC5.7**: `applier.py` module created (~100 lines)
- [ ] **AC5.8**: `EnhancementApplier` class with `apply()` and `generate_diff()` methods
- [ ] **AC5.9**: All shared modules have comprehensive docstrings and type hints

### 6. Task Integration

- [ ] **AC6.1**: Task metadata schema defined for agent enhancement tasks
- [ ] **AC6.2**: Task creation uses correct priority (medium)
- [ ] **AC6.3**: Task description includes agent file path and template directory
- [ ] **AC6.4**: Task acceptance criteria clearly defined
- [ ] **AC6.5**: `/task-work` integration works (calls `/agent-enhance` command)
- [ ] **AC6.6**: Task completion criteria met when agent enhanced

### 7. Testing

- [ ] **AC7.1**: 15 unit tests passing (100% pass rate)
- [ ] **AC7.2**: 5 integration tests passing (100% pass rate)
- [ ] **AC7.3**: Test coverage ≥85% for new code
- [ ] **AC7.4**: Command argument parsing tested (4 tests)
- [ ] **AC7.5**: All three strategies tested (ai, static, hybrid)
- [ ] **AC7.6**: Task creation tested
- [ ] **AC7.7**: End-to-end workflow tested (create tasks → enhance agents)

### 8. Documentation

- [ ] **AC8.1**: `/agent-enhance` command spec complete
- [ ] **AC8.2**: Workflow guide updated (incremental enhancement section)
- [ ] **AC8.3**: CLAUDE.md updated (incremental workflow documented)
- [ ] **AC8.4**: Examples provided (common use cases)
- [ ] **AC8.5**: Comparison table (automated vs incremental)

---

## Implementation Specification

### Phase 8: Task Creation

```python
# File: installer/global/commands/lib/template_create_orchestrator.py

def _run_phase_8_create_agent_tasks(
    self,
    state: TemplateCreateState
) -> PhaseResult:
    """
    Phase 8: Create individual agent enhancement tasks (optional).

    Only runs if config.create_agent_tasks is True.

    Creates one task per agent file for incremental enhancement.
    Tasks can be worked through individually using /task-work.

    Args:
        state: Current template creation state

    Returns:
        PhaseResult with task_ids and tasks_created count

    Raises:
        TaskCreationError: If task creation fails
    """

    if not self.config.create_agent_tasks:
        logger.info("Skipping agent task creation (--create-agent-tasks not specified)")
        return PhaseResult(success=True, tasks_created=0)

    template_dir = state.output_path
    template_name = template_dir.name
    agent_files = list((template_dir / "agents").glob("*.md"))

    if not agent_files:
        logger.warning("No agent files found to create tasks for")
        return PhaseResult(success=True, tasks_created=0)

    logger.info(f"Creating enhancement tasks for {len(agent_files)} agents...")

    # Import task creator
    from installer.global.commands.lib.task_creator import create_task

    task_ids = []
    for agent_file in agent_files:
        agent_name = agent_file.stem

        # Create task
        task_id = create_task(
            title=f"Enhance {agent_name} agent for {template_name} template",
            description=f"""
Enhance the {agent_name} agent with template-specific content:
- Add related template references
- Include code examples from templates
- Document best practices
- Add anti-patterns to avoid (if applicable)

Agent File: {agent_file}
Template Directory: {template_dir}

Use the /agent-enhance command:
/agent-enhance {template_name}/{agent_name}
""".strip(),
            metadata={
                "type": "agent_enhancement",
                "agent_file": str(agent_file),
                "template_dir": str(template_dir),
                "template_name": template_name,
                "agent_name": agent_name
            },
            priority="medium",
            acceptance_criteria=[
                "Agent file enhanced with template-specific sections",
                "Relevant templates identified and documented",
                "Code examples from templates included",
                "Best practices documented",
                "Anti-patterns documented (if applicable)"
            ]
        )

        task_ids.append(task_id)
        logger.info(f"  ✓ Created {task_id} for {agent_name}")

    logger.info(f"\n✓ Created {len(task_ids)} agent enhancement tasks")
    logger.info("  Work through them with: /task-work <TASK-ID>")
    logger.info(f"  Task IDs: {', '.join(task_ids)}")

    return PhaseResult(
        success=True,
        tasks_created=len(task_ids),
        task_ids=task_ids
    )
```

### `/agent-enhance` Command

```python
# File: installer/global/commands/agent-enhance.py

"""
/agent-enhance Command

Enhance a single agent with template-specific content.
"""

import sys
from pathlib import Path
from typing import Optional
import logging
import argparse

import importlib
_enhancer_module = importlib.import_module(
    'installer.global.lib.agent_enhancement.enhancer'
)
SingleAgentEnhancer = _enhancer_module.SingleAgentEnhancer

logger = logging.getLogger(__name__)


def main(args: list[str]) -> int:
    """Main entry point for /agent-enhance command."""

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog="agent-enhance",
        description="Enhance a single agent with template-specific content"
    )
    parser.add_argument(
        "agent_path",
        help="Agent path (template-dir/agent-name or /path/to/agent.md)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be enhanced without applying"
    )
    parser.add_argument(
        "--strategy",
        choices=["ai", "static", "hybrid"],
        default="ai",
        help="Enhancement strategy (default: ai)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed enhancement process"
    )

    parsed_args = parser.parse_args(args)

    # Resolve agent file and template directory
    agent_file, template_dir = resolve_paths(parsed_args.agent_path)

    if not agent_file.exists():
        logger.error(f"Agent file not found: {agent_file}")
        return 1

    if not template_dir.exists():
        logger.error(f"Template directory not found: {template_dir}")
        return 2

    # Create enhancer
    enhancer = SingleAgentEnhancer(
        strategy=parsed_args.strategy,
        dry_run=parsed_args.dry_run,
        verbose=parsed_args.verbose
    )

    # Enhance agent
    try:
        logger.info(f"Enhancing {agent_file.name}...")

        result = enhancer.enhance(
            agent_file=agent_file,
            template_dir=template_dir
        )

        if result.success:
            logger.info(f"✓ Enhanced {agent_file.name}")
            logger.info(f"  Sections added: {len(result.sections)}")
            logger.info(f"  Templates referenced: {len(result.templates)}")
            logger.info(f"  Code examples: {len(result.examples)}")

            if parsed_args.dry_run:
                logger.info("\n[DRY RUN] Changes not applied")
                print("\n--- Preview ---")
                print(result.diff)

            return 0
        else:
            logger.error(f"✗ Enhancement failed: {result.error}")
            return 3

    except ValidationError as e:
        logger.error(f"✗ Validation failed: {e}")
        return 4

    except PermissionError as e:
        logger.error(f"✗ Cannot write to agent file: {e}")
        return 5

    except Exception as e:
        logger.exception(f"✗ Unexpected error: {e}")
        return 3


def resolve_paths(agent_path_str: str) -> tuple[Path, Path]:
    """
    Resolve agent file and template directory from input path.

    Handles two formats:
    1. "template-dir/agent-name" (relative, slash-separated)
    2. "/absolute/path/to/agent.md" (absolute path)

    Args:
        agent_path_str: Input path string

    Returns:
        (agent_file, template_dir) tuple

    Raises:
        ValueError: If path format is invalid
    """

    agent_path = Path(agent_path_str)

    if agent_path.is_absolute() and agent_path.exists():
        # Absolute path format
        agent_file = agent_path
        template_dir = agent_file.parent.parent  # agents/ -> template/
        return (agent_file, template_dir)

    elif "/" in agent_path_str:
        # Relative "template/agent" format
        parts = agent_path_str.split("/")
        template_name = parts[0]
        agent_name = parts[1]

        # Look in global templates
        template_dir = Path(f"installer/global/templates/{template_name}")
        if not template_dir.exists():
            # Look in local templates
            template_dir = Path.home() / ".agentecflow" / "templates" / template_name

        agent_file = template_dir / "agents" / f"{agent_name}.md"
        return (agent_file, template_dir)

    else:
        raise ValueError(
            f"Invalid agent path format: {agent_path_str}\n"
            "Expected: 'template-dir/agent-name' or '/path/to/agent.md'"
        )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

### SingleAgentEnhancer Module

```python
# File: installer/global/lib/agent_enhancement/enhancer.py

"""
Single Agent Enhancer

Enhances individual agent files with template-specific content.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json
import logging

# Import shared modules
import importlib
_prompt_builder = importlib.import_module(
    'installer.global.lib.agent_enhancement.prompt_builder'
)
_parser = importlib.import_module(
    'installer.global.lib.agent_enhancement.parser'
)
_applier = importlib.import_module(
    'installer.global.lib.agent_enhancement.applier'
)

EnhancementPromptBuilder = _prompt_builder.EnhancementPromptBuilder
EnhancementParser = _parser.EnhancementParser
EnhancementApplier = _applier.EnhancementApplier

logger = logging.getLogger(__name__)


@dataclass
class EnhancementResult:
    """Result of agent enhancement."""
    success: bool
    agent_name: str
    sections: List[str]  # Sections added
    templates: List[str]  # Templates referenced
    examples: List[str]   # Code examples included
    diff: str            # Unified diff
    error: Optional[str] = None
    strategy_used: Optional[str] = None


class SingleAgentEnhancer:
    """Enhances a single agent with template-specific content."""

    def __init__(
        self,
        strategy: str = "ai",
        dry_run: bool = False,
        verbose: bool = False
    ):
        """
        Initialize enhancer.

        Args:
            strategy: Enhancement strategy (ai|static|hybrid)
            dry_run: If True, don't apply changes
            verbose: If True, show detailed process
        """
        self.strategy = strategy
        self.dry_run = dry_run
        self.verbose = verbose

        # Create supporting components
        self.prompt_builder = EnhancementPromptBuilder()
        self.parser = EnhancementParser()
        self.applier = EnhancementApplier()

    def enhance(
        self,
        agent_file: Path,
        template_dir: Path
    ) -> EnhancementResult:
        """
        Enhance single agent with template-specific content.

        Args:
            agent_file: Path to agent file
            template_dir: Path to template directory

        Returns:
            Enhancement result with success status and details
        """

        agent_name = agent_file.stem

        try:
            # 1. Load agent metadata
            if self.verbose:
                logger.info(f"Loading agent metadata from {agent_file}")

            agent_metadata = self._load_agent_metadata(agent_file)

            # 2. Discover relevant templates
            if self.verbose:
                logger.info(f"Discovering relevant templates in {template_dir}")

            templates = self._discover_relevant_templates(
                agent_metadata,
                template_dir
            )

            if self.verbose:
                logger.info(f"Found {len(templates)} relevant templates")

            # 3. Generate enhancement
            if self.verbose:
                logger.info(f"Generating enhancement using '{self.strategy}' strategy")

            enhancement = self._generate_enhancement(
                agent_metadata,
                templates,
                template_dir
            )

            # 4. Validate enhancement
            if self.verbose:
                logger.info("Validating enhancement")

            self._validate_enhancement(enhancement)

            # 5. Apply enhancement (if not dry run)
            if not self.dry_run:
                if self.verbose:
                    logger.info(f"Applying enhancement to {agent_file}")

                self.applier.apply(agent_file, enhancement)

            # 6. Generate diff
            diff = self.applier.generate_diff(agent_file, enhancement)

            return EnhancementResult(
                success=True,
                agent_name=agent_name,
                sections=enhancement.get("sections", []),
                templates=[str(t) for t in templates],
                examples=enhancement.get("examples", []),
                diff=diff,
                strategy_used=self.strategy
            )

        except Exception as e:
            logger.exception(f"Enhancement failed for {agent_name}")
            return EnhancementResult(
                success=False,
                agent_name=agent_name,
                sections=[],
                templates=[],
                examples=[],
                diff="",
                error=str(e),
                strategy_used=self.strategy
            )

    def _generate_enhancement(
        self,
        agent_metadata: dict,
        templates: List[Path],
        template_dir: Path
    ) -> dict:
        """Generate enhancement using selected strategy."""

        if self.strategy == "ai":
            return self._ai_enhancement(agent_metadata, templates, template_dir)
        elif self.strategy == "static":
            return self._static_enhancement(agent_metadata, templates)
        elif self.strategy == "hybrid":
            # Try AI, fallback to static
            try:
                return self._ai_enhancement(agent_metadata, templates, template_dir)
            except Exception as e:
                logger.warning(f"AI enhancement failed, falling back to static: {e}")
                return self._static_enhancement(agent_metadata, templates)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _ai_enhancement(
        self,
        agent_metadata: dict,
        templates: List[Path],
        template_dir: Path
    ) -> dict:
        """AI-powered enhancement."""

        # Build prompt using shared prompt builder
        prompt = self.prompt_builder.build(
            agent_metadata,
            templates,
            template_dir
        )

        # Invoke AI (direct Task tool invocation)
        from anthropic_sdk import task
        result = task(
            agent="agent-content-enhancer",
            prompt=prompt,
            timeout=300
        )

        # Parse response using shared parser
        enhancement = self.parser.parse(result)

        return enhancement

    def _static_enhancement(
        self,
        agent_metadata: dict,
        templates: List[Path]
    ) -> dict:
        """Static keyword-based enhancement (Option C from TASK-09E9)."""

        # Simple keyword matching
        agent_name = agent_metadata["name"]
        keywords = agent_name.split('-')

        related_templates = []
        for template in templates:
            if any(kw in template.stem.lower() for kw in keywords):
                related_templates.append(str(template))

        return {
            "sections": ["related_templates"],
            "related_templates": "\n\n## Related Templates\n\n" + "\n".join([
                f"- {t}" for t in related_templates
            ]),
            "examples": [],
            "best_practices": ""
        }

    def _load_agent_metadata(self, agent_file: Path) -> dict:
        """Load agent metadata from frontmatter."""
        import frontmatter

        agent_doc = frontmatter.loads(agent_file.read_text())
        return agent_doc.metadata

    def _discover_relevant_templates(
        self,
        agent_metadata: dict,
        template_dir: Path
    ) -> List[Path]:
        """Discover templates relevant to agent."""

        # For now, return all templates
        # Could be enhanced with AI-powered relevance scoring
        return list(template_dir.rglob("*.template"))

    def _validate_enhancement(self, enhancement: dict) -> None:
        """Validate enhancement structure."""

        required_keys = ["sections"]
        for key in required_keys:
            if key not in enhancement:
                raise ValidationError(f"Missing required key: {key}")

        if not isinstance(enhancement["sections"], list):
            raise ValidationError("'sections' must be a list")
```

---

## Test Specifications

### Unit Tests (15 tests)

**Command Tests** (4 tests):
1. `test_parse_args_template_agent_format` - Parse "template/agent" format
2. `test_parse_args_direct_path_format` - Parse "/path/to/agent.md" format
3. `test_command_returns_error_if_agent_not_found` - Exit code 1
4. `test_command_dry_run_shows_preview` - --dry-run displays diff

**Enhancer Tests** (8 tests):
5. `test_ai_strategy_invokes_task_tool` - AI strategy calls Task
6. `test_static_strategy_uses_keyword_matching` - Static matches keywords
7. `test_hybrid_strategy_falls_back_to_static` - Hybrid fallback on AI failure
8. `test_enhance_returns_result_with_details` - Result includes sections, templates, examples
9. `test_dry_run_generates_diff_without_applying` - Dry-run doesn't modify file
10. `test_verbose_mode_logs_progress` - Verbose shows detailed steps
11. `test_enhance_handles_missing_frontmatter` - Graceful degradation
12. `test_enhance_validates_enhancement_structure` - Validation works

**Task Creation Tests** (3 tests):
13. `test_create_task_for_each_agent` - One task per agent
14. `test_task_includes_correct_metadata` - Metadata complete
15. `test_phase_8_skipped_if_flag_not_set` - Only runs when requested

### Integration Tests (5 tests)

1. `test_end_to_end_task_creation_and_enhancement` - Full workflow
2. `test_agent_enhance_command_integration` - Command works standalone
3. `test_mixed_workflow_automation_and_manual` - Hybrid usage
4. `test_shared_modules_used_by_both_options` - DRY verification
5. `test_task_system_integration` - Task metadata works with /task-work

---

## Usage Examples

### Example 1: Create Tasks Then Enhance Individually

```bash
# Step 1: Create template with task creation flag
/template-create --validate --create-agent-tasks

# Output:
# ✓ Created 7 agent enhancement tasks
#   Task IDs: TASK-A01, TASK-A02, TASK-A03, TASK-A04, TASK-A05, TASK-A06, TASK-A07
#   Work through them with: /task-work <TASK-ID>

# Step 2: Work through high-priority agents first
/task-work TASK-A01  # Repository pattern specialist
/task-work TASK-A04  # MAUI ViewModel specialist

# Step 3: Skip low-priority agents (optional)
# TASK-A07 can wait

# Result: Enhanced high-priority agents, deferred low-priority ones
```

### Example 2: Direct Agent Enhancement

```bash
# Enhance specific agent without tasks
/agent-enhance react-typescript/testing-specialist

# Output:
# ✓ Enhanced testing-specialist.md
#   Sections added: 3
#   Templates referenced: 12
#   Code examples: 5
```

### Example 3: Dry-Run Preview

```bash
# Preview enhancement without applying
/agent-enhance my-template/repository-specialist --dry-run

# Output:
# ✓ Enhanced repository-specialist.md
#   Sections added: 4
#   Templates referenced: 8
#   Code examples: 3
#
# [DRY RUN] Changes not applied
#
# --- Preview ---
# ## Related Templates
# - templates/domain/Repository.cs.template
# - templates/domain/IRepository.cs.template
# ...
```

### Example 4: Static Strategy (No AI)

```bash
# Use simple keyword matching (fast, no AI)
/agent-enhance my-template/repository-specialist --strategy=static

# Output:
# ✓ Enhanced repository-specialist.md
#   Sections added: 1 (related_templates only)
#   Templates referenced: 3
#   Code examples: 0 (static strategy doesn't generate examples)
```

### Example 5: Hybrid Strategy (AI with Fallback)

```bash
# Try AI, fallback to static if AI fails
/agent-enhance my-template/repository-specialist --strategy=hybrid --verbose

# Output (if AI works):
# Loading agent metadata...
# Discovering relevant templates...
# Found 15 relevant templates
# Generating enhancement using 'hybrid' strategy...
# AI enhancement successful
# ✓ Enhanced repository-specialist.md

# Output (if AI fails):
# Loading agent metadata...
# Discovering relevant templates...
# Found 15 relevant templates
# Generating enhancement using 'hybrid' strategy...
# ⚠ AI enhancement failed, falling back to static: TimeoutError
# ✓ Enhanced repository-specialist.md (using static strategy)
```

---

## Edge Cases

### 1. No Templates Match Agent (Static Strategy)
- **Scenario**: Agent name is "custom-workflow-manager", no templates contain "custom", "workflow", or "manager"
- **Expected**: Create "Related Templates" section with empty list or "No matching templates found"
- **Test**: `test_static_strategy_handles_no_matches`

### 2. AI Returns Empty Enhancement
- **Scenario**: AI determines no enhancement needed
- **Expected**: Return success with 0 sections added
- **Test**: `test_enhance_handles_empty_enhancement`

### 3. Task Creation Fails Midway
- **Scenario**: Task 3/7 fails to create
- **Expected**: Continue creating remaining tasks, report partial success
- **Test**: `test_phase_8_continues_on_task_creation_failure`

### 4. User Provides Malformed Path
- **Scenario**: `/agent-enhance invalid/path/format`
- **Expected**: Exit code 1, clear error message explaining formats
- **Test**: `test_command_handles_malformed_path`

---

## Performance Characteristics

### Individual Enhancement
- **AI Strategy**: 2-5 minutes per agent
- **Static Strategy**: <5 seconds per agent (no AI)
- **Hybrid Strategy**: 2-5 minutes (same as AI, with fallback safety)

### Task Creation (Phase 8)
- **Time**: <5 seconds (7 tasks × 0.5 sec each)
- **Memory**: Negligible (~1 KB per task)

### Comparison to Option 1
| Aspect | Option 1 (Automated) | Option 2 (Incremental) |
|--------|----------------------|------------------------|
| **Total Time** | 14-35 min (all agents) | User-dependent (enhance as needed) |
| **User Control** | None | Full control |
| **Overhead** | None | Task creation (~5 sec) |
| **Flexibility** | Fixed sequence | Prioritize agents |

---

## Success Metrics

### Functional Targets
- **Task Creation**: 100% success rate (one task per agent)
- **Individual Enhancement**: ≥70% success rate per agent
- **Command Usability**: <5 min to understand and use
- **Strategy Selection**: All 3 strategies work correctly

### User Experience Targets
- **Transparency**: Clear progress at each step
- **Control**: Can enhance agents in any order
- **Flexibility**: Can mix automated + manual
- **Feedback**: Clear success/failure messages

---

## Implementation Checklist

### Day 1: Phase 8 Task Creation
- [ ] Add `--create-agent-tasks` flag to command spec
- [ ] Update `OrchestrationConfig` dataclass
- [ ] Implement `_run_phase_8_create_agent_tasks` method
- [ ] Add to phase dispatcher
- [ ] Test: Create tasks for 3 agents
- [ ] Commit: "feat: Add Phase 8 agent task creation"

### Day 2: `/agent-enhance` Command Structure
- [ ] Create command file (`agent-enhance.py`)
- [ ] Create command spec (`agent-enhance.md`)
- [ ] Implement argument parsing
- [ ] Implement path resolution (`resolve_paths`)
- [ ] Add exit code handling
- [ ] Test: Command parsing and path resolution
- [ ] Commit: "feat: Add /agent-enhance command structure"

### Day 3: SingleAgentEnhancer Module
- [ ] Create module file (`enhancer.py`)
- [ ] Implement `SingleAgentEnhancer` class
- [ ] Implement AI strategy
- [ ] Implement static strategy
- [ ] Implement hybrid strategy
- [ ] Test: All three strategies
- [ ] Commit: "feat: Add SingleAgentEnhancer module"

### Day 4: Shared Modules
- [ ] Create `prompt_builder.py` module
- [ ] Create `parser.py` module
- [ ] Create `applier.py` module
- [ ] Refactor Option 1 to use shared modules (DRY)
- [ ] Test: Shared modules work for both options
- [ ] Commit: "refactor: Extract shared enhancement modules"

### Day 5: Integration & Testing
- [ ] Write 15 unit tests
- [ ] Write 5 integration tests
- [ ] Verify ≥85% coverage
- [ ] Test end-to-end workflow
- [ ] Fix any bugs found
- [ ] Commit: "test: Add comprehensive tests for Option 2"

### Day 6: Documentation
- [ ] Update CLAUDE.md (incremental workflow section)
- [ ] Create workflow guide
- [ ] Add usage examples
- [ ] Document strategy differences
- [ ] Create comparison table
- [ ] Commit: "docs: Document incremental enhancement workflow"

### Day 7: Integration Testing & Polish
- [ ] Test on real reference template
- [ ] Verify task integration works
- [ ] Test mixed workflow (automated + manual)
- [ ] Polish error messages
- [ ] Final testing
- [ ] Commit: "polish: Final touches for Option 2"

---

## Related Documents

- [TASK-PHASE-7.5-SIMPLE](TASK-PHASE-7-5-SIMPLE-specification.md) - Automated enhancement (Option 1)
- [Phase 7.5 Replacement Architectural Review](../reviews/phase-7-5-replacement-architectural-review.md) - Design specs
- [Template-Create Path Forward](../reviews/template-create-path-forward.md) - Strategic direction

---

**Document Status**: READY FOR IMPLEMENTATION
**Last Updated**: 2025-11-20
**Dependencies**: TASK-PHASE-7.5-SIMPLE (can run in parallel, but Option 1 is MVP)
**Estimated Start Date**: After Option 1 complete or in parallel with senior dev
**Estimated Completion**: 5-7 days from start
