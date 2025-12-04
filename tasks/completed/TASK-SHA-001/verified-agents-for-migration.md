# Agent Duplication Verification Report

**Generated**: 2025-12-03T16:28:17Z
**Threshold**: 80% for duplicate classification
**Manual Review Range**: 50%-80%

## Verification Method

This report uses **line-based similarity analysis** to identify duplicate agents:

1. Reads agent files from both repositories
2. Compares line content using sorted diff matching
3. Calculates similarity percentage: (2 × matching_lines) / (total_lines) × 100
4. Classifies agents:
   - **Duplicate**: ≥80% match
   - **Manual Review**: 50%-80% match
   - **Unique**: <50% match

## RequireKit Status

RequireKit found at: ../require-kit\n\nAll agents from both repositories have been compared.

## Summary

| Category | Count |
|----------|-------|
| Truly Duplicated (≥80%) | 0 |
| Manual Review (50-80%) |        4 |
| Low Similarity (<50%) |        1 |
| GuardKit-Only |       14 |
| RequireKit-Only |        2 |

## Truly Duplicated Agents (≥80%)

These agents are confirmed duplicates and should be reviewed for consolidation:

None found.

## Manual Review Required (50%-80%)

These agents have partial overlap and need manual inspection:


- **architectural-reviewer** - 72% match
- **code-reviewer** - 61% match
- **task-manager** - 64% match
- **test-orchestrator** - 74% match

## Low Similarity Agents (<50%)

These agents exist in BOTH repositories but have significantly diverged (not worth consolidating):


- **test-verifier** - 47% match (diverged)

## GuardKit-Only Agents (No Equivalent in RequireKit)

These agents are unique to GuardKit and don't need consolidation:


- agent-content-enhancer
- build-validator
- complexity-evaluator
- database-specialist
- debugging-specialist
- devops-specialist
- dotnet-domain-specialist
- figma-react-orchestrator
- git-workflow-manager
- pattern-advisor
- python-api-specialist
- react-state-specialist
- security-specialist
- zeplin-maui-orchestrator

## RequireKit-Only Agents (New to RequireKit)

These agents exist only in RequireKit and may need to be evaluated for GuardKit inclusion:


- bdd-generator
- requirements-analyst

## Migration Recommendations

### Action Items
1. **Review Duplicates**: Consolidate agents marked as truly duplicated
2. **Manual Inspection**: Review agents in the manual review section to determine if consolidation is beneficial
3. **Unique Assessment**: Evaluate RequireKit-only agents for potential GuardKit integration

### Notes
- This analysis is based on line-level matching and may miss structural similarities
- Manual code review is recommended for agents in the manual review category
- Consider domain-specific differences when evaluating consolidation
