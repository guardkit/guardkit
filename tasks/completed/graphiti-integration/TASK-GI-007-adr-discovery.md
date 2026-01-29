---
completed_at: 2026-01-28 23:45:00+00:00
complexity: 5
conductor_workspace: wave5-2
created_at: 2026-01-24 00:00:00+00:00
dependencies:
- TASK-GI-001
- TASK-GI-004
estimated_minutes: 180
feature_id: FEAT-GI
id: TASK-GI-007
implementation_mode: task-work
implementation_results:
  code_review_notes: Approved with minor recommendations - excellent test coverage
    and comprehensive implementation
  code_review_status: APPROVED
  coverage: 93%
  development_mode: tdd
  files_created:
  - guardkit/knowledge/adr_discovery.py
  - tests/knowledge/test_adr_discovery.py
  files_modified:
  - guardkit/knowledge/adr_discovery.py (path filtering bug fix)
  - tests/knowledge/test_adr_discovery.py (confidence threshold fix)
  tests_passed: 85
  tests_total: 85
parent_review: TASK-REV-GI01
priority: 3
status: completed
tags:
- graphiti
- adr
- discovery
- code-analysis
- medium-priority
task_type: feature
title: ADR Discovery from Code Analysis
wave: 5
---

# TASK-GI-007: ADR Discovery from Code Analysis

## Overview

**Priority**: Medium (Enables learning from existing codebases)
**Dependencies**: TASK-GI-001 (Core Infrastructure), TASK-GI-004 (ADR Lifecycle)

## Problem Statement

When `/template-create` analyzes an existing codebase, it discovers patterns, conventions, and structural decisions that were made during development. These are **implicit ADRs** - architectural decisions that exist in the code but were never formally documented.

Examples:
- "We use feature-based directory organization"
- "We use dependency injection for database sessions"
- "Pydantic schemas follow {Entity}{Operation} naming"

These discovered decisions should be captured as ADRs so future sessions understand "why things are the way they are."

## Strategic Context

This feature captures **discovered ADRs** from code analysis, complementing the **explicit ADRs** from TASK-GI-004. Together they provide:

- Explicit ADRs: Decisions made consciously during workflow (has rationale)
- Discovered ADRs: Decisions inferred from existing code (may lack rationale)

Discovered ADRs can later be linked to explicit ADRs that validate or supersede them.

## Goals

1. Extract implicit decisions during `/template-create` code analysis
2. Create discovered ADRs with code evidence
3. Assign confidence scores based on consistency
4. Link discovered ADRs to templates

## Non-Goals

- Replace explicit ADR creation
- Analyze arbitrary codebases outside template-create
- Provide rationale for discovered decisions (unknown)

## Types of Discovered Decisions

### 1. Structural Decisions
```
Evidence: "src/{feature}/router.py, schemas.py, models.py, crud.py"
Discovered ADR: "Feature-based organization with standard file naming"
Confidence: 95% (consistent across all features)
```

### 2. Technology Decisions
```
Evidence: "requirements.txt contains FastAPI, SQLAlchemy, Pydantic"
Discovered ADR: "Async Python stack with typed ORM"
Confidence: 100% (direct evidence)
```

### 3. Pattern Decisions
```
Evidence: "All routes use Depends(get_db)"
Discovered ADR: "Dependency injection for database sessions"
Confidence: 90% (9/10 routes follow pattern)
```

### 4. Convention Decisions
```
Evidence: "UserCreate, UserUpdate, UserPublic, UserInDB"
Discovered ADR: "Pydantic schemas use {Entity}{Operation} naming"
Confidence: 85% (some exceptions found)
```

## Technical Approach

### Discovery During Template Analysis

```python
# guardkit/knowledge/adr_discovery.py

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

@dataclass
class DiscoveredDecision:
    """A decision discovered from code analysis."""

    category: str  # structural, technology, pattern, convention
    title: str
    description: str
    evidence: List[str]  # Files/patterns supporting this
    confidence: float  # 0.0 to 1.0
    exceptions: List[str]  # Violations of the pattern

async def discover_adrs_from_codebase(
    source_path: Path,
    analysis_results: dict
) -> List[DiscoveredDecision]:
    """Discover implicit ADRs from code analysis."""

    discovered = []

    # 1. Structural decisions
    structure_decisions = analyze_directory_structure(source_path)
    discovered.extend(structure_decisions)

    # 2. Technology decisions
    tech_decisions = analyze_dependencies(source_path)
    discovered.extend(tech_decisions)

    # 3. Pattern decisions
    pattern_decisions = analyze_code_patterns(source_path, analysis_results)
    discovered.extend(pattern_decisions)

    # 4. Convention decisions
    convention_decisions = analyze_naming_conventions(source_path, analysis_results)
    discovered.extend(convention_decisions)

    return discovered


def analyze_directory_structure(source_path: Path) -> List[DiscoveredDecision]:
    """Analyze directory structure for organizational patterns."""

    decisions = []

    # Check for feature-based organization
    src_dir = source_path / "src"
    if src_dir.exists():
        feature_dirs = [d for d in src_dir.iterdir() if d.is_dir()]

        # Check if each feature has standard files
        standard_files = {"router.py", "schemas.py", "models.py", "crud.py"}
        features_with_standard = 0

        for feature_dir in feature_dirs:
            files = {f.name for f in feature_dir.glob("*.py")}
            if files & standard_files:
                features_with_standard += 1

        if feature_dirs and features_with_standard / len(feature_dirs) > 0.7:
            decisions.append(DiscoveredDecision(
                category="structural",
                title="Feature-based organization with standard file naming",
                description="Code is organized by feature/domain with consistent file patterns",
                evidence=[str(d) for d in feature_dirs[:5]],
                confidence=features_with_standard / len(feature_dirs),
                exceptions=[]
            ))

    return decisions


def analyze_code_patterns(
    source_path: Path,
    analysis_results: dict
) -> List[DiscoveredDecision]:
    """Analyze code for common patterns."""

    decisions = []

    # Check for dependency injection
    di_evidence = []
    di_count = 0
    total_routes = 0

    for py_file in source_path.rglob("*.py"):
        content = py_file.read_text()

        if "Depends(" in content:
            di_count += content.count("Depends(")
            di_evidence.append(str(py_file.relative_to(source_path)))

        if "@router" in content or "@app" in content:
            total_routes += content.count("@router") + content.count("@app")

    if di_count > 5:
        decisions.append(DiscoveredDecision(
            category="pattern",
            title="Dependency Injection pattern",
            description="Uses FastAPI Depends() for dependency injection",
            evidence=di_evidence[:10],
            confidence=min(di_count / max(total_routes, 1), 1.0),
            exceptions=[]
        ))

    return decisions
```

### Convert to ADR Entities

```python
async def create_discovered_adrs(
    discoveries: List[DiscoveredDecision],
    template_id: str
) -> List[ADREntity]:
    """Create ADR entities from discovered decisions."""

    adrs = []

    for discovery in discoveries:
        # Only create ADR if confidence is high enough
        if discovery.confidence < 0.7:
            continue

        adr = await create_adr(
            title=discovery.title,
            context=f"Discovered during template-create analysis of {template_id}",
            decision=discovery.description,
            trigger=None,  # Discovered, not triggered by workflow
            source_type=ADRSourceType.DISCOVERED,
            source_template_id=template_id
        )

        # Add discovery-specific metadata
        adr.code_evidence = discovery.evidence
        adr.confidence = discovery.confidence

        # Update in Graphiti with additional fields
        graphiti = get_graphiti()
        if graphiti.enabled:
            await graphiti.add_episode(
                name=f"adr_{adr.id}",
                episode_body=json.dumps({
                    **adr.to_episode_body(),
                    "code_evidence": discovery.evidence,
                    "confidence": discovery.confidence,
                    "exceptions": discovery.exceptions,
                    "discovery_category": discovery.category
                }),
                group_id="adrs"
            )

        adrs.append(adr)

    return adrs
```

### Integration with template-create

```python
# guardkit/commands/template_create.py

async def create_template(source_path: Path, output_path: Path, **options):
    """Create template from source code."""

    # Existing analysis...
    analysis_results = await analyze_codebase(source_path)

    # Generate template...
    template_path = await generate_template(source_path, output_path, analysis_results)

    # NEW: Discover and create ADRs
    discoveries = await discover_adrs_from_codebase(source_path, analysis_results)
    await create_discovered_adrs(discoveries, template_path.name)

    # Sync template to Graphiti
    await sync_template_to_graphiti(template_path)

    return template_path
```

## Acceptance Criteria

- [ ] **Discoveries are made**
  - `/template-create` discovers structural decisions
  - Technology choices are identified from dependencies
  - Code patterns are detected
  - Naming conventions are identified

- [ ] **ADRs are created**
  - Discovered ADRs have `source_type=DISCOVERED`
  - Code evidence is attached
  - Confidence scores reflect consistency

- [ ] **ADRs are queryable**
  - Can search for discovered ADRs
  - Can filter by confidence level
  - Can see code evidence

- [ ] **Linked to templates**
  - Discovered ADRs link to source template
  - Can find all ADRs for a template

## Testing Strategy

1. **Unit tests**: Test individual discovery functions
2. **Integration tests**: Test full discovery on sample codebase
3. **E2E tests**: template-create creates expected ADRs

## Files to Create/Modify

### New Files
- `guardkit/knowledge/adr_discovery.py`
- `tests/knowledge/test_adr_discovery.py`

### Modified Files
- `guardkit/commands/template_create.py` (add discovery hook)

## Example Discovered ADRs

```json
{
  "id": "ADR-DISC-001",
  "title": "Feature-based organization with standard file naming",
  "status": "accepted",
  "source_type": "discovered",
  "context": "Discovered during template-create analysis of fastapi-python",
  "decision": "Code is organized by feature/domain with consistent file patterns",
  "code_evidence": [
    "src/users/router.py",
    "src/users/schemas.py",
    "src/products/router.py",
    "src/products/schemas.py"
  ],
  "confidence": 0.95,
  "discovery_category": "structural",
  "source_template_id": "fastapi-python"
}
```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| False positives (detecting patterns that aren't intentional) | Require high confidence (>0.7) |
| Missing important patterns | Start with common patterns, expand over time |
| Confidence scores inaccurate | Tune thresholds based on experience |

## Open Questions

1. Should discovered ADRs require human confirmation?
2. How do we handle conflicting discoveries across templates?
3. Should we discover anti-patterns (things done inconsistently)?

---

## Related Documents

- [TASK-GI-004: ADR Lifecycle Management](./TASK-GI-004-adr-lifecycle.md) - Explicit ADRs
- [TASK-GI-006: Template/Agent Sync](./TASK-GI-006-template-agent-sync.md) - Template sync
- [Unified Data Architecture Decision](../../docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md)