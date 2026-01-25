---
id: TASK-FP-4F81
title: "Add existing code audit step to /feature-plan command"
status: backlog
task_type: implementation
created: 2025-12-24T00:00:00Z
updated: 2025-12-24T00:00:00Z
priority: medium
tags: [feature-plan, process-improvement, code-audit, subtask-generation]
complexity: 4
estimated_hours: 2-3
origin: TASK-REV-FB02
origin_finding: "Wave 2-4 tasks duplicated existing CLI implementation"
---

# Add Existing Code Audit Step to /feature-plan Command

## Problem Statement

During the TASK-REV-FB02 architectural review, it was discovered that Wave 2-4 tasks created by `/feature-plan` for the feature-build command duplicated existing functionality in `guardkit/cli/autobuild.py`.

**Root Cause**: The `/feature-plan` workflow designs solutions from first principles without auditing existing codebase for related implementations.

**Impact**:
- Wasted planning effort (Wave 2 was 100% duplicate)
- Potential for duplicate code if implemented
- Maintenance burden from parallel implementations

## Solution

Add an **Existing Code Audit** step to the `/feature-plan` command workflow, executed before subtask generation.

## Requirements

### Functional Requirements

1. **FR-1**: Before generating subtasks, search for existing implementations
   - Search for related files by name patterns
   - Search for related code by keyword/function names
   - Present findings to user before proceeding

2. **FR-2**: Display audit results with integration options
   ```
   ══════════════════════════════════════════════════════════════════
   📋 EXISTING CODE AUDIT
   ══════════════════════════════════════════════════════════════════

   Found 3 potentially related files:

   1. guardkit/cli/autobuild.py (400 lines)
      - Contains: `guardkit autobuild task` command
      - Relevance: HIGH - implements CLI for autobuild

   2. guardkit/orchestrator/autobuild.py (1095 lines)
      - Contains: AutoBuildOrchestrator class
      - Relevance: HIGH - core orchestration logic

   3. guardkit/orchestrator/agent_invoker.py (651 lines)
      - Contains: AgentInvoker with SDK placeholder
      - Relevance: HIGH - SDK integration point

   Options:
     [C]ontinue - Proceed with subtask generation (existing code noted)
     [I]ntegrate - Generate subtasks that extend/modify existing code
     [R]eview - Open files for review before deciding
     [A]bort - Cancel feature planning

   Your choice [C/I/R/A]:
   ```

3. **FR-3**: Adjust subtask generation based on audit findings
   - If existing CLI found → Don't generate new CLI tasks
   - If existing orchestrator found → Generate modification tasks, not creation
   - If placeholder found → Generate replacement tasks

4. **FR-4**: Add audit findings to feature README.md
   - Document what existing code was found
   - Explain integration approach chosen
   - Link to existing files

### Non-Functional Requirements

1. **NFR-1**: Audit should complete in <10 seconds
2. **NFR-2**: Use Glob and Grep tools for search (not full codebase scan)
3. **NFR-3**: Relevance scoring based on file path and content matching

## Implementation Approach

### Phase Integration

Insert audit step into `/feature-plan` workflow:

```
Current Flow:
1. Create review task
2. Execute architectural review
3. [I]mplement → Generate subtasks

Proposed Flow:
1. Create review task
2. Execute architectural review
3. [I]mplement → **NEW: Existing Code Audit**
4. Generate subtasks (informed by audit)
```

### Search Strategy

```python
def audit_existing_code(feature_description: str) -> AuditResult:
    """Search for existing code related to the feature."""

    # Extract keywords from feature description
    keywords = extract_keywords(feature_description)
    # e.g., "feature-build" → ["feature", "build", "autobuild", "cli"]

    # Search for related files
    file_patterns = [
        f"**/*{kw}*.py" for kw in keywords
    ]

    # Search for related code
    code_patterns = [
        f"class.*{kw}",
        f"def.*{kw}",
        f"@click.command.*{kw}",
    ]

    # Score and rank findings
    findings = []
    for file in glob(file_patterns):
        relevance = calculate_relevance(file, keywords)
        findings.append(Finding(file=file, relevance=relevance))

    return AuditResult(findings=sorted(findings, key=lambda f: -f.relevance))
```

### Files to Modify

1. **installer/core/commands/feature-plan.md**
   - Add audit step documentation
   - Add `[I]ntegrate` option at [I]mplement checkpoint

2. **installer/core/lib/implement_orchestrator.py** (or create)
   - Add `audit_existing_code()` function
   - Add `display_audit_results()` function
   - Modify `handle_implement_option()` to call audit first

3. **installer/core/lib/subtask_generator.py** (or existing)
   - Accept `audit_findings` parameter
   - Adjust task generation based on findings

## Acceptance Criteria

- [ ] `/feature-plan` searches for existing code before generating subtasks
- [ ] User is presented with audit findings and options
- [ ] `[I]ntegrate` option adjusts subtask generation
- [ ] Feature README.md includes audit findings section
- [ ] Audit completes in <10 seconds
- [ ] No false positives for unrelated files (relevance scoring)
- [ ] Existing code audit can be skipped with `--skip-audit` flag

## Testing

### Test Case 1: Feature with existing implementation
```bash
/feature-plan "implement autobuild CLI"
# Should find: guardkit/cli/autobuild.py
# Should suggest: Integration with existing CLI
```

### Test Case 2: Feature with no existing implementation
```bash
/feature-plan "implement new export format"
# Should find: No related files
# Should proceed: Normal subtask generation
```

### Test Case 3: Feature with partial implementation
```bash
/feature-plan "add SDK integration to autobuild"
# Should find: agent_invoker.py with placeholder
# Should suggest: Replacement/completion tasks
```

## Related

- **TASK-REV-FB02**: Origin of this improvement (architectural review finding)
- **TASK-FB-W2**: Example of superseded task (100% duplicate)
- **/feature-plan command spec**: `installer/core/commands/feature-plan.md`

## Notes

This improvement addresses a process gap discovered during the feature-build review. By auditing existing code before generating subtasks, `/feature-plan` will:

1. Avoid generating duplicate implementations
2. Suggest integration with existing code
3. Reduce wasted effort on planning already-implemented features
4. Improve subtask accuracy and relevance
