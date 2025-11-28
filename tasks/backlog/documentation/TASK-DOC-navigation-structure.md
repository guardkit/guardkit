# Update MkDocs Navigation Structure

**Priority**: Important
**Category**: Documentation Architecture
**Estimated Effort**: 2 hours

## Problem

New documentation pages need to be added to the MkDocs navigation structure. This task ensures all new pages are properly integrated and discoverable.

## Current State

MkDocs navigation exists but needs updates for:
- Hash-Based Task IDs (Core Concepts)
- Spec-Oriented Development (Core Concepts)
- Parallel Development (Advanced Topics)
- Agent Boundary Sections (Agent System)
- Review vs Implementation Workflows (Task Review)
- Platform-specific installation (Getting Started)

## Acceptance Criteria

1. Update `mkdocs.yml` navigation structure
2. Organize under appropriate sections:
   - **Core Concepts**:
     - Hash-Based Task IDs
     - Spec-Oriented Development
     - Workflow Phases
     - Quality Gates
     - Task States
   - **Advanced Topics**:
     - Parallel Development
     - Design-First Workflow
     - UX Integration
   - **Agent System**:
     - Agent Discovery
     - Agent Enhancement
     - Boundary Sections
   - **Task Review**:
     - Review vs Implementation Workflows
     - Review Modes
     - Review Depth Levels
3. Ensure logical ordering within sections
4. Verify all links work after navigation update
5. Check for orphaned pages

## Implementation Notes

- Review current mkdocs.yml structure
- Group related concepts together
- Use clear, descriptive navigation labels
- Consider adding section descriptions
- Test navigation flow for new users

## References

- mkdocs.yml
- All new documentation task files
- Existing navigation structure
