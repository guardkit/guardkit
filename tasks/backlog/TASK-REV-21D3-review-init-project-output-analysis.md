---
id: TASK-REV-21D3
title: Review guardkit init project output and Graphiti seeding
status: review_complete
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:00:00Z
task_type: review
review_mode: architectural
review_depth: standard
priority: high
tags: [cli, graphiti, init, falkordb, vllm, seeding, developer-experience]
complexity: 5
parent_task: TASK-REV-5842
related_tasks: [TASK-4B7F]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review guardkit init project output and Graphiti seeding

## Description

Analyse the output from creating a new project (`guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/appmilla_github/guardkit`) and the ad-hoc review findings to identify actionable issues with the init workflow, Graphiti seeding, and FalkorDB integration.

## Review Scope

### Primary Input Documents

1. **Init output log**: `docs/reviews/reduce-static-markdown/init-project_1.md`
   - Full terminal output from `guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/appmilla_github/guardkit`
   - Includes FalkorDB connection, vLLM inference, seeding episodes, and error logs

2. **Informal review notes**: `docs/reviews/reduce-static-markdown/informal-review.md`
   - Ad-hoc findings from the session that created the project
   - Covers what worked, issues found, and preliminary recommendations

### Known Issues to Analyse

1. **FalkorDB "Max pending queries exceeded"** - Capacity errors during episodes 3-4 of Graphiti seeding. Need to determine: data loss? recovery? mitigation?
2. **Step 2.5 template sync "incomplete results"** - Template content sync warning after seeding. Root cause unclear.
3. **OPENAI_API_KEY required by graphiti-core** - Even with vLLM providers configured, graphiti-core constructor requires OPENAI_API_KEY. Current workaround is `OPENAI_API_KEY=dummy`.
4. **"Connection closed by server" during index building** - FalkorDB closed connection during `build_indices_and_constraints()`. Was non-blocking but needs investigation.
5. **Role constraints & implementation modes query returns 0 results** - Seeding logs show "OK" but queries against `vllm-profiling__product_knowledge` returned nothing. Root cause: system-scoped groups use unprefixed group IDs (`role_constraints`, `implementation_modes`), not project-prefixed ones. Need to verify this is by-design and whether the query tooling/docs need updating.
6. **Excessive log verbosity** - Init output is dominated by httpx INFO logs (hundreds of lines of `HTTP Request: POST ... "HTTP/1.1 200 OK"`). Review whether log levels should be adjusted.
7. **Episode timing variance** - Episodes ranged from 21s to 79s. Analyse whether this is expected for vLLM inference or indicates issues.

### Key Files to Review

- `guardkit/cli/init.py` - Init command orchestration, seeding flow
- `guardkit/knowledge/project_seeding.py` - Seeding orchestrator
- `guardkit/knowledge/seed_role_constraints.py` - Role constraint seeding
- `guardkit/knowledge/graphiti_client.py` - FalkorDB connection, group ID prefixing
- `guardkit/integrations/graphiti/constants.py` - System vs project group definitions

## Acceptance Criteria

- [ ] Root cause analysis for each of the 7 known issues
- [ ] Severity classification (critical/high/medium/low) for each issue
- [ ] Actionable recommendations with effort estimates
- [ ] Determine if FalkorDB capacity errors caused data loss
- [ ] Verify system-scoped group ID behaviour is correct by design
- [ ] Identify any additional issues not covered in the informal review
- [ ] Prioritised list of implementation tasks if [I]mplement is chosen

## Review Focus Areas

1. **FalkorDB reliability** - Connection stability, query capacity, error recovery
2. **Seeding correctness** - Data integrity, group ID namespacing, episode completion
3. **Developer experience** - Log verbosity, error messages, progress feedback
4. **vLLM integration** - Inference timing, OPENAI_API_KEY workaround, model compatibility

## Implementation Notes

This review follows from the completed TASK-REV-5842 (vLLM profiling project setup review) and TASK-4B7F (--copy-graphiti flag implementation). The init command and --copy-graphiti feature are now working, but the Graphiti seeding and FalkorDB integration have several issues that need formal analysis.
