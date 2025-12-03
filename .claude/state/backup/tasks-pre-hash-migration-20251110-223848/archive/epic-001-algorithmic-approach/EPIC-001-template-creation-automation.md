---
id: EPIC-001
title: Template Creation Automation - AI-Powered Template Commands
status: backlog
created: 2025-11-01T15:30:00Z
priority: high
type: epic
estimated_duration: 11 weeks
tags: [template-automation, ai-powered, agent-discovery, pattern-extraction]
---

# EPIC-001: Template Creation Automation

## Vision

Dramatically reduce the barrier to creating custom project templates from **3-5 hours to 35-40 minutes** (75-80% reduction) through AI-powered pattern extraction and community agent discovery.

## Overview

Two powerful commands that transform how teams create and customize templates:

1. **`/template-create`** - Analyze existing codebases and automatically generate templates
2. **`/template-init`** - Interactive guided creation for greenfield projects

## Strategic Goals

- **Lower Adoption Barrier**: Single command vs. multi-step manual process
- **Improve Quality**: AI-captured patterns vs. manual interpretation
- **Accelerate Teams**: 100+ community agents discoverable and integrated
- **Enable Consistency**: Generated templates follow established structure

## Features

### Feature 1: `/template-create` Command (Weeks 1-7)
Analyze existing codebases and extract architectural patterns automatically.

**Child Tasks**:
- TASK-037: Technology stack detection
- TASK-038: Architecture pattern analyzer
- TASK-039: Code pattern extraction
- TASK-040: Naming convention inference
- TASK-041: Layer structure detection
- TASK-042: Manifest generator
- TASK-043: Settings generator
- TASK-044: CLAUDE.md generator
- TASK-045: Code template generator
- TASK-046: Template validation
- TASK-047: Command orchestrator

### Feature 2: Agent Discovery System (Weeks 3-5)
Multi-source agent discovery with intelligent matching.

**Child Tasks**:
- TASK-048: Subagents.cc scraper
- TASK-049: GitHub agent parsers
- TASK-050: Agent matching algorithm
- TASK-051: Interactive selection UI
- TASK-052: Agent download and integration

### Feature 3: `/template-init` Command (Weeks 6-8)
Interactive Q&A for greenfield template creation.

**Child Tasks**:
- TASK-053: Q&A flow structure
- TASK-054: Basic information section
- TASK-055: Technology stack section
- TASK-056: Architecture section
- TASK-057: Testing strategy section
- TASK-058: Quality standards section
- TASK-059: Agent discovery integration
- TASK-060: Command orchestrator

### Feature 4: Distribution & Versioning (Weeks 9-10)
Template packaging, versioning, and distribution.

**Child Tasks**:
- TASK-061: Template packaging system
- TASK-062: Template versioning
- TASK-063: Update/merge functionality
- TASK-064: Distribution helpers

### Feature 5: Testing & Documentation (Weeks 10-11)
End-to-end testing and comprehensive documentation.

**Child Tasks**:
- TASK-065: Integration tests
- TASK-066: User documentation
- TASK-067: Example templates

## Success Metrics

### Quantitative
- Template creation time: <40 minutes (75% reduction)
- Pattern accuracy: >90% correct identification
- Agent discovery: 100+ agents indexed
- Adoption rate: 50% of teams create custom template within 1 month

### Qualitative
- "Easy to get started with guardkit"
- Developers discover valuable agents
- Templates accurately reflect conventions
- Reduced support requests

## Implementation Phases

### Phase 1: Pattern Extraction (Weeks 1-2)
Core pattern detection and analysis engine.

### Phase 2: Agent Discovery (Weeks 3-4)
Multi-source agent scraping and matching.

### Phase 3: Template Generation (Weeks 5-6)
Template file generation and validation.

### Phase 4: Interactive Creator (Weeks 7-8)
Q&A flow and guided creation.

### Phase 5: Testing & Docs (Weeks 9-10)
Comprehensive testing and documentation.

### Phase 6: Release (Week 11)
Final QA, release notes, community announcement.

## Dependencies

### Prerequisites
- Existing local template system (COMPLETED ✅)
- Template installer support (COMPLETED ✅)
- Manual template guide (COMPLETED ✅)

### External Dependencies
- Access to subagents.cc API (or web scraping)
- Access to GitHub API for agent repositories
- Web scraping libraries (Beautiful Soup, Puppeteer)

## Risks & Mitigations

### Risk 1: Pattern Detection Accuracy
**Severity**: High | **Probability**: Medium

**Mitigation**:
- Start with well-known patterns (MVVM, Clean Architecture)
- Interactive mode for user confirmation
- Extensive testing across codebases

### Risk 2: Agent Source Availability
**Severity**: Medium | **Probability**: Low

**Mitigation**:
- Cache discovered agents locally
- Support multiple sources (failover)
- Graceful degradation if sources unavailable

### Risk 3: Scope Creep
**Severity**: Medium | **Probability**: High

**Mitigation**:
- MVP first: React/TypeScript + basic patterns
- Defer advanced features to v2
- Clear task boundaries

### Risk 4: Complexity Management
**Severity**: High | **Probability**: Medium

**Mitigation**:
- Break into small tasks (<8 hours each)
- Independent, testable components
- Continuous integration and validation

## Related Documentation

- [Template Creation Commands - Full Proposal](../../docs/proposals/template-creation-commands.md)
- [Template Creation Commands - Summary](../../docs/proposals/template-creation-commands-summary.md)
- [Template Creation Workflow Guide](../../docs/guides/template-creation-workflow.md)
- [Creating Local Templates](../../docs/guides/creating-local-templates.md)

## Progress Tracking

**Total Tasks**: 31
- Backlog: 31
- In Progress: 0
- Completed: 0

**Overall Progress**: 0%

## Notes

This epic represents a transformational feature for guardkit adoption. The AI-powered approach differentiates us from other template systems and leverages community agent resources effectively.

**Key Innovation**: First system to combine automatic pattern extraction with multi-source agent discovery.

---

**Created**: 2025-11-01
**Target Start**: TBD
**Target Completion**: TBD (11 weeks from start)
**Owner**: AI Engineer Team
