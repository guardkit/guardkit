# TASK-RENAME-LEGACY-BUILD-NEW: Build Clean Main Command

**Task ID**: TASK-RENAME-LEGACY-BUILD-NEW
**Title**: Rename Existing to Legacy, Build Clean Main template-create
**Status**: BACKLOG
**Priority**: HIGH
**Complexity**: 5/10 (Medium)
**Estimated Hours**: 2-3
**Phase**: 7 of 8 (Template-Create Redesign)

---

## Problem Statement

### Current Issue

The existing template-create command has accumulated technical debt. For a clean open source release, we need:
- A professional main command
- No version confusion (v1 vs v2)
- Safe fallback available

### Strategy

Rename existing to `template-create-legacy` (undocumented fallback), build fixed version as main `template-create`.

---

## Solution Design

### Approach

1. Rename existing files to `-legacy` suffix
2. Integrate all fixes from Phases 1-6 into new orchestrator
3. Keep legacy as undocumented fallback
4. Test on all reference projects

### File Operations

| Step | File | Action |
|------|------|--------|
| 1 | `installer/global/commands/template-create.md` | RENAME to template-create-legacy.md |
| 2 | `installer/global/commands/lib/template_create_orchestrator.py` | RENAME to template_create_legacy_orchestrator.py |
| 3 | `installer/global/commands/template-create.md` | CREATE (new clean version) |
| 4 | `installer/global/commands/lib/template_create_orchestrator.py` | CREATE (with all Phase 1-6 fixes) |

---

## Implementation Details

### Step 1: Rename Existing Files

```bash
# Rename command spec
mv installer/global/commands/template-create.md \
   installer/global/commands/template-create-legacy.md

# Rename orchestrator
mv installer/global/commands/lib/template_create_orchestrator.py \
   installer/global/commands/lib/template_create_legacy_orchestrator.py
```

### Step 2: Update Legacy Command Spec

```markdown
<!-- installer/global/commands/template-create-legacy.md -->
---
name: template-create-legacy
description: Legacy template creation (use /template-create instead)
---

# Template Create Legacy

> **Note**: This is the legacy version. Use `/template-create` for the improved version.

...existing content...
```

### Step 3: Create New Command Spec

```markdown
<!-- installer/global/commands/template-create.md -->
---
name: template-create
description: Create a template from an existing codebase using AI analysis
---

# Template Create

Create a reusable template from your existing codebase. Uses AI-powered analysis for accurate detection and comprehensive agent generation.

## Usage

```bash
/template-create [--name <name>] [--output-location <repo|personal>] [--validate]
```

## Features

- **AI-Powered Analysis**: 90%+ confidence codebase detection
- **Smart Artifact Filtering**: Excludes build outputs automatically
- **Comprehensive Agent Creation**: 7-9 specialized agents per project
- **Enhanced Agent Documentation**: 150-250 line agents with examples
- **Checkpoint-Resume**: Survives interruptions

## Workflow

1. **Phase 1**: AI Codebase Analysis (architectural-reviewer)
2. **Phase 2**: Manifest Generation
3. **Phase 3**: Settings Generation
4. **Phase 4**: Template File Generation
5. **Phase 4.5**: Completeness Validation
6. **Phase 5**: AI Agent Creation (architectural-reviewer)
7. **Phase 6**: Agent File Writing
8. **Phase 7**: CLAUDE.md Generation
9. **Phase 7.5**: AI Agent Enhancement (agent-content-enhancer)
10. **Phase 8**: Validation Report

## Quality Metrics

| Metric | Target |
|--------|--------|
| Confidence Score | 90%+ |
| Agents Created | 7-9 |
| Agent Quality | 150-250 lines |
| Language Accuracy | 95%+ |

## Examples

```bash
# Create template in personal location (default)
/template-create --name my-template

# Create in repository for team sharing
/template-create --name shared-template --output-location repo

# Validate without creating
/template-create --validate
```
```

### Step 4: Create New Orchestrator

The new orchestrator integrates all Phase 1-6 fixes:

```python
# installer/global/commands/lib/template_create_orchestrator.py

"""
Template Create Orchestrator (v2)

AI-powered template creation with checkpoint-resume support.

Features:
- Build artifact filtering (Phase 1)
- Agent bridge checkpoint-resume (Phase 2)
- AI codebase analysis (Phase 3)
- AI agent creation (Phase 4)
- AI agent enhancement (Phase 5)
- No hard-coded detection (Phase 6)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import uuid
import logging

from .exclusion_patterns import filter_files
from installer.global.lib.agent_bridge.checkpoint_manager import (
    CheckpointManager,
    CheckpointRequested,
    TemplateCreateState,
    CHECKPOINT_EXIT_CODE
)
from installer.global.lib.agent_bridge.invoker import AgentBridgeInvoker
from docs.proposals.template_create.AI_PROMPTS_SPECIFICATION import (
    PHASE_1_ANALYSIS_PROMPT,
    PHASE_4_AGENT_CREATION_PROMPT,
    PHASE_1_CONFIDENCE_THRESHOLD,
    PHASE_4_CONFIDENCE_THRESHOLD
)

logger = logging.getLogger(__name__)


class TemplateCreateOrchestrator:
    """
    Orchestrates template creation workflow with AI-powered analysis.

    This is the v2 orchestrator with all improvements:
    - Build artifact filtering
    - AI codebase analysis
    - AI agent creation (not discovery)
    - AI agent enhancement
    - Complete checkpoint-resume support
    """

    def __init__(
        self,
        project_path: Path,
        template_name: str,
        output_location: str = "personal",
        agent_invoker: Optional[AgentBridgeInvoker] = None
    ):
        self.project_path = Path(project_path)
        self.template_name = template_name
        self.output_location = output_location
        self.agent_invoker = agent_invoker
        self.checkpoint_manager = CheckpointManager()
        self.logger = logging.getLogger(__name__)

    def run(self) -> "OrchestrationResult":
        """
        Main entry point for template creation.

        Returns:
            OrchestrationResult with created template details
        """
        # Check for resume from checkpoint
        if self.checkpoint_manager.is_resuming():
            return self._resume_from_checkpoint()

        # Start fresh workflow
        return self._run_full_workflow()

    def _resume_from_checkpoint(self) -> "OrchestrationResult":
        """Resume from saved checkpoint."""
        state = self.checkpoint_manager.load_checkpoint()
        if not state:
            raise OrchestrationError("Failed to load checkpoint")

        self._print_info(f"Resuming from Phase {state.phase} ({state.phase_name})")

        # Route to appropriate resume method
        if state.phase == 1 and self.checkpoint_manager.has_agent_response():
            return self._run_from_phase_1()
        elif state.phase == 5 and self.checkpoint_manager.has_agent_response():
            return self._run_from_phase_5()
        elif state.phase == 7 and self.checkpoint_manager.has_agent_response():
            return self._run_from_phase_7()
        else:
            raise OrchestrationError(f"Cannot resume from phase {state.phase}")

    def _run_full_workflow(self) -> "OrchestrationResult":
        """Run complete workflow from beginning."""
        try:
            # Determine output path
            output_path = self._get_output_path()

            # Phase 1: AI Codebase Analysis (with artifact filtering)
            samples = self._get_filtered_samples()
            analysis = self._phase1_ai_analysis(samples, output_path)

            # Phases 2-4: Manifest, Settings, Templates
            self._phase2_manifest(analysis, output_path)
            self._phase3_settings(analysis, output_path)
            self._phase4_templates(analysis, output_path)
            self._phase4_5_validation(output_path)

            # Phase 5: AI Agent Creation
            agent_result = self._phase5_agent_creation(analysis, output_path)

            # Phase 6: Write Agent Files
            self._phase6_write_agents(agent_result, output_path)

            # Phase 7: CLAUDE.md
            self._phase7_documentation(analysis, agent_result, output_path)

            # Phase 7.5: AI Agent Enhancement
            self._phase7_5_enhance_agents(agent_result, output_path)

            # Phase 8: Validation Report
            report = self._phase8_validation(output_path)

            # Cleanup checkpoint files
            self.checkpoint_manager.clear_checkpoint()

            return OrchestrationResult(
                success=True,
                output_path=output_path,
                template_name=self.template_name,
                analysis=analysis,
                agents=agent_result,
                report=report
            )

        except CheckpointRequested as e:
            # Exit for external agent invocation
            self._print_info(f"\nCheckpoint saved. Invoke {e.agent_name} and resume.")
            import sys
            sys.exit(CHECKPOINT_EXIT_CODE)

    def _get_filtered_samples(self) -> List["FileSample"]:
        """Get file samples with build artifacts filtered out."""
        from .stratified_sampler import StratifiedSampler

        sampler = StratifiedSampler()
        all_files = sampler.get_all_files(self.project_path)

        # Filter build artifacts (Phase 1 fix)
        source_files = filter_files(all_files, self.project_path)

        return sampler.sample_stratified(source_files, max_files=30)

    # ... Phase methods from Phases 1-6 implementation ...

    def _print_info(self, message: str):
        """Print info message."""
        print(message)

    def _print_warning(self, message: str):
        """Print warning message."""
        print(f"⚠️  {message}")

    def _print_phase_header(self, title: str):
        """Print phase header."""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")
```

---

## Acceptance Criteria

### Functional

- [ ] `/template-create` command works (new version)
- [ ] `/template-create-legacy` available as fallback
- [ ] All checkpoint-resume phases functional
- [ ] E2E tests pass on 4 reference projects

### Quality

- [ ] Confidence 90%+ on all test projects
- [ ] 7-9 agents created
- [ ] Enhanced agents 150-250 lines
- [ ] No references to "legacy" in user-facing docs

---

## Test Specifications

### E2E Tests

```bash
# Test new command on all reference projects
for project in \
    ~/Projects/DeCUK.Mobile.MyDrive \
    ~/Projects/bulletproof-react \
    ~/Projects/fastapi-best-practices \
    ~/Projects/nextjs-boilerplate; do

    cd "$project"
    /template-create --validate --name "test-$(basename $project)"

    # Verify results
    echo "Project: $project"
    echo "Confidence: $(jq .confidence manifest.json)"
    echo "Agents: $(jq '.agents | length' manifest.json)"
    echo "---"
done
```

### Comparison Tests

```bash
# Compare new vs legacy output
cd ~/Projects/test-project

/template-create --name test-new
mv ~/.agentecflow/templates/test-new ~/test-new-output

/template-create-legacy --name test-legacy
mv ~/.agentecflow/templates/test-legacy ~/test-legacy-output

# Compare
diff -r ~/test-new-output ~/test-legacy-output
```

---

## Dependencies

### Depends On
- All Phases 1-6 completed

### Blocks
- TASK-OPEN-SOURCE-DOCUMENTATION (Phase 8)

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| E2E success | 100% | All 4 projects |
| Confidence | 90%+ | manifest.json |
| Agents | 7-9 | manifest.json |
| Agent quality | 150-250 lines | Line count |

---

## Notes

- Legacy command is undocumented fallback only
- Remove legacy after 4 weeks of stable operation
- This is critical for open source first impression

---

**Created**: 2025-11-18
**Phase**: 7 of 8 (Template-Create Redesign)
**Related**: Open source release preparation
