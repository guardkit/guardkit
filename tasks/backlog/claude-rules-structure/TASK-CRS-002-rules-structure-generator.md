---
id: TASK-CRS-002
title: Implement RulesStructureGenerator Class
status: completed
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T13:05:00Z
completed: 2025-12-11T13:05:00Z
priority: high
tags: [rules-structure, generator, template-create]
complexity: 6
parent_feature: claude-rules-structure
wave: 2
implementation_mode: task-work
conductor_workspace: claude-rules-wave2-1
estimated_hours: 4-6
actual_hours: 1.5
dependencies:
  - TASK-CRS-001
---

# Task: Implement RulesStructureGenerator Class

## Description

Create a new `RulesStructureGenerator` class that generates the modular `.claude/rules/` directory structure for Claude Code's new memory system.

## Background

Claude Code supports a 4-tier memory hierarchy with modular rules:
- Path-specific rules only load when relevant files are touched
- Recursive discovery in subdirectories
- Conditional loading with `paths:` frontmatter

## Output Structure

```
.claude/
├── CLAUDE.md                          # Core (~5KB)
└── rules/
    ├── code-style.md                  # paths: **/*.{ext}
    ├── testing.md                     # paths: **/*.test.*, **/tests/**
    └── patterns/
    │   ├── repository.md
    │   └── mvvm.md
    └── agents/
        ├── specialist-a.md            # paths: **/relevant/**
        └── specialist-b.md
```

## Implementation

### File: `installer/core/lib/template_generator/rules_structure_generator.py`

```python
"""
Rules Structure Generator

Generates modular .claude/rules/ structure for Claude Code's memory system.
Implements path-specific conditional loading for reduced context window usage.
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..codebase_analyzer.models import CodebaseAnalysis


@dataclass
class RuleFile:
    """Represents a single rules file."""
    path: str  # Relative path (e.g., "rules/code-style.md")
    content: str
    paths_filter: Optional[str] = None  # paths: frontmatter value


class RulesStructureGenerator:
    """
    Generate modular .claude/rules/ structure for Claude Code.

    This implements the new Claude Code memory system that supports:
    - Path-specific rules (only load when relevant)
    - Recursive discovery in subdirectories
    - Conditional loading with paths: frontmatter
    """

    def __init__(
        self,
        analysis: CodebaseAnalysis,
        agents: List,
        output_path: Path
    ):
        self.analysis = analysis
        self.agents = agents
        self.output_path = output_path

    def generate(self) -> Dict[str, str]:
        """
        Generate rules structure.

        Returns:
            Dictionary mapping file paths to content
        """
        rules = {}

        # 1. Core CLAUDE.md (minimal, ~5KB)
        rules["CLAUDE.md"] = self._generate_core_claudemd()

        # 2. Code style rules
        rules["rules/code-style.md"] = self._generate_code_style_rules()

        # 3. Testing rules (conditional)
        rules["rules/testing.md"] = self._generate_testing_rules()

        # 4. Pattern-specific rules
        for pattern in self.analysis.architecture.patterns:
            pattern_slug = self._slugify(pattern)
            rules[f"rules/patterns/{pattern_slug}.md"] = self._generate_pattern_rules(pattern)

        # 5. Agent rules (one per agent)
        for agent in self.agents:
            agent_slug = self._slugify(agent.name)
            rules[f"rules/agents/{agent_slug}.md"] = self._generate_agent_rules(agent)

        return rules

    def _generate_core_claudemd(self) -> str:
        """Generate minimal core CLAUDE.md (~5KB)."""
        # Implementation...

    def _generate_code_style_rules(self) -> str:
        """Generate code style rules with path filtering."""
        # Implementation...

    def _generate_testing_rules(self) -> str:
        """Generate testing rules with path filtering."""
        # Implementation...

    def _generate_pattern_rules(self, pattern: str) -> str:
        """Generate rules for a specific design pattern."""
        # Implementation...

    def _generate_agent_rules(self, agent) -> str:
        """Generate rules file for an agent."""
        # Implementation...

    def _infer_agent_paths(self, agent_name: str) -> str:
        """Infer path patterns for conditional agent loading."""
        # Implementation...

    def _slugify(self, name: str) -> str:
        """Convert name to slug format."""
        return name.lower().replace(" ", "-").replace("_", "-")
```

## Key Implementation Details

### Path Pattern Inference

```python
def _infer_agent_paths(self, agent_name: str) -> str:
    """Infer path patterns for conditional agent loading."""
    path_mappings = {
        'repository': '**/Repositories/**/*.cs, **/repositories/**/*.py',
        'viewmodel': '**/ViewModels/**/*.cs, **/*ViewModel.cs',
        'service': '**/Services/**/*.cs, **/services/**/*.py',
        'engine': '**/Engines/**/*.cs, **/*Engine.cs',
        'testing': '**/tests/**/*.*, **/*.test.*',
        'api': '**/Controllers/**/*.cs, **/api/**/*.py, **/router*.py',
        'database': '**/models/*.py, **/crud/*.py, **/db/**',
        'query': '**/*query*, **/*api*, **/*fetch*',
        'form': '**/*form*, **/*validation*',
        'component': '**/components/**/*.tsx, **/components/**/*.jsx',
    }

    agent_lower = agent_name.lower()
    for key, paths in path_mappings.items():
        if key in agent_lower:
            return paths

    return ""  # No conditional loading (always load)
```

### Frontmatter Generation

```python
def _generate_frontmatter(self, paths: Optional[str]) -> str:
    """Generate YAML frontmatter with paths filter."""
    if not paths:
        return ""
    return f"""---
paths: {paths}
---

"""
```

## Acceptance Criteria

- [ ] `RulesStructureGenerator` class implemented
- [ ] Generates core CLAUDE.md under 5KB
- [ ] Generates code-style.md with language-specific paths
- [ ] Generates testing.md with test file paths
- [ ] Generates pattern rules in `rules/patterns/`
- [ ] Generates agent rules in `rules/agents/` with paths frontmatter
- [ ] Path patterns correctly inferred from agent names
- [ ] All generated files are valid markdown
- [ ] Unit tests cover all public methods

## Testing

```bash
pytest tests/lib/template_generator/test_rules_generator.py -v
```

## Notes

- This is Wave 2 (depends on Wave 1 size limit fix)
- Use `/task-work` for full quality gates
- Core logic for TASK-FIX-SIZE-F8G2 Phase 2

## Completion Summary

**Status**: ✅ Completed
**Date**: 2025-12-11T13:05:00Z
**Actual Time**: 1.5 hours (estimated: 4-6 hours)

### Implementation Details

Created `RulesStructureGenerator` class with full functionality:

1. **Core Components**:
   - Main generator class with `generate()` method
   - Path inference system for conditional loading
   - Frontmatter generation for YAML filtering
   - Helper methods for language-specific content

2. **Generated Structure**:
   - `CLAUDE.md` - Minimal core guide (<5KB)
   - `rules/code-style.md` - Language-specific style rules
   - `rules/testing.md` - Testing guidelines and requirements
   - `rules/patterns/*.md` - Design pattern documentation
   - `rules/agents/*.md` - Agent-specific guidance with path inference

3. **Key Features**:
   - Path-specific conditional loading (reduces context window)
   - Intelligent agent path mapping (repository, api, testing, etc.)
   - Language-aware command generation (install, test, dev)
   - Stack-specific best practices and conventions

### Testing Results

- **41 unit tests** - All passing ✅
- **99% code coverage** - Exceeds requirements ✅
- **Test categories**:
  - RuleFile dataclass tests
  - Core generator functionality
  - CLAUDE.md generation
  - Code style rules generation
  - Testing rules generation
  - Pattern rules generation
  - Agent rules generation
  - Path inference logic
  - Frontmatter generation
  - Helper methods

### Files Created/Modified

1. `installer/core/lib/template_generator/rules_structure_generator.py` (NEW)
   - 500+ lines, comprehensive implementation
   - All public methods documented
   - Type hints throughout

2. `installer/core/lib/template_generator/__init__.py` (MODIFIED)
   - Added exports for RulesStructureGenerator and RuleFile

3. `installer/core/lib/template_generator/tests/test_rules_generator.py` (NEW)
   - 41 comprehensive unit tests
   - 99% coverage

4. `installer/core/lib/template_generator/tests/example_output.md` (NEW)
   - Documentation showing example generated output
   - Demonstrates all major features

### Acceptance Criteria Verification

✅ **All 9 criteria met:**

1. ✅ RulesStructureGenerator class implemented
2. ✅ Generates core CLAUDE.md under 5KB (verified by test)
3. ✅ Generates code-style.md with language-specific paths
4. ✅ Generates testing.md with test file paths
5. ✅ Generates pattern rules in `rules/patterns/`
6. ✅ Generates agent rules in `rules/agents/` with paths frontmatter
7. ✅ Path patterns correctly inferred from agent names
8. ✅ All generated files are valid markdown
9. ✅ Unit tests cover all public methods (99% coverage)

### Integration Points

This generator integrates with:
- `CodebaseAnalysis` model (technology, architecture, quality info)
- Agent metadata system (for agent-specific rules)
- Path resolution for output directory handling

### Next Steps

Ready for integration into `/template-create` command (Wave 3).
See TASK-CRS-003 for integration work.
