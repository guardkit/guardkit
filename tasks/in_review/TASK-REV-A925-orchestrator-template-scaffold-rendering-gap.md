---
id: TASK-REV-A925
title: Orchestrator template scaffold files not rendered by guardkit-init
status: review_complete
task_type: review
review_mode: architectural
review_depth: standard
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
priority: high
tags:
  - review
  - templates
  - langchain-deepagents
  - langchain-deepagents-orchestrator
  - langchain-deepagents-weighted-evaluation
  - guardkit-init
  - scaffold
  - forge
  - blocker
  - les1-regression
  - lcl-003
  - lcl-004
  - lcl-005
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
source_brief: docs/reviews/deepagents-templates/TASK-REV-FORGE-INIT-orchestrator-template-scaffold-rendering-gap.md
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 5
  recommendations_count: 6
  decision: pending
  report_path: .claude/reviews/TASK-REV-A925-review-report.md
  completed_at: 2026-04-18T00:00:00Z
---

# Task: Orchestrator template scaffold files not rendered by `guardkit-init`

## Type

Architectural review + root-cause investigation → fix

## Severity

**BLOCKER** — blocks Forge Phase 0 (`/system-arch`) and silently affects any
consumer of `langchain-deepagents-orchestrator`. Also a regression indicator
against `TASK-LCL-004` and `TASK-LCL-005` from the `langchain-template-lessons`
feature (LES1 implementation).

## Context

On **2026-04-18**, after completing the full `langchain-template-lessons`
feature (LES1 Waves 1–3, all 12 `TASK-LCL-*` tasks) and re-running `install.sh`
cleanly, we initialised the `forge` repo from `langchain-deepagents-orchestrator`:

```bash
cd ~/Projects/appmilla_github/forge
guardkit-init langchain-deepagents-orchestrator
```

`guardkit-init` reported success with no errors or warnings:

- 7 template-specific agents copied
- 17 global agents added
- Rules structure verified (15 rule files)
- Project configuration created

However, the consumer repo is **missing the entire orchestrator code scaffold**:

- ✗ No `pyproject.toml` (expected: from LCL-004's `pyproject.toml.template` with `[providers]` extras)
- ✗ No `AGENTS.md` (expected: from LCL-005's `AGENTS.md.template` with R2A1 ainvoke contract)
- ✗ No `src/` directory at all
- ✗ No `agent.py` (expected: from `agent.py.template`)
- ✗ No `langgraph.json`
- ✓ `.claude/` populated (correct)
- ✓ `docs/`, `tasks/`, `.guardkit/` populated (correct)
- ✓ 24 agents in `.claude/agents/` (correct)

## Evidence (captured 2026-04-18)

### 1. Source repo contains the files (LCL-004 and LCL-005 landed correctly)

```bash
find ~/Projects/appmilla_github/guardkit/installer/core/templates/langchain-deepagents-orchestrator/ \
  -name "pyproject.toml*" -o -name "AGENTS.md*"
```

Output:

```
.../templates/other/other/AGENTS.md.template
.../templates/other/other/pyproject.toml.template
```

### 2. Installed template cache contains the files (install.sh copied correctly)

```bash
find ~/.agentecflow/templates/langchain-deepagents-orchestrator/ \
  -name "pyproject.toml*" -o -name "AGENTS.md*" -o -name "agent.py.template"
```

Output:

```
.../templates/other/other/agent.py.template
.../templates/other/other/AGENTS.md.template
.../templates/other/other/pyproject.toml.template
```

### 3. Installed template directory structure

Under `~/.agentecflow/templates/langchain-deepagents-orchestrator/templates/other/`:

- `agents/`         — rendered in consumer (`.claude/agents` landed)
- `example-domain/` — rendering status unknown
- `lib/`            — rendering status unknown
- `other/`          — **NOT RENDERED** (contains `agent.py`, `AGENTS.md`, `pyproject.toml`)
- `prompts/`        — rendering status unknown
- `tools/`          — rendering status unknown

### 4. Consumer repo after `guardkit-init`

```bash
$ ls -la src/                    # (empty — directory does not exist)
$ test -f AGENTS.md && echo Y || echo N
N
$ test -f pyproject.toml && grep -q "providers" pyproject.toml && echo Y || echo N
N
```

## Hypothesis

`guardkit-init`'s template file resolver has an **incomplete mapping** for the
`templates/other/<category>/` convention. The nested `templates/other/other/`
subdirectory — by convention the bucket for project-root files that don't fit
a named category (`agents`, `lib`, `prompts`, `tools`) — is silently skipped.

**Alternatives to rule out:**

- **Manifest declaration gap**: `manifest.json` may fail to list
  `templates/other/other/**` as init-time outputs, even if resolver logic
  supports nested `other/`
- **Jinja rendering error** swallowed by the CLI output layer
- **Different scaffold-shipping contract** between base `langchain-deepagents`
  and `langchain-deepagents-orchestrator` templates (if base ships these files
  via a different path, the resolver may expect that path universally)

## Why this is a LES1 §8 regression

LES1 §8 ("doc/code co-evolution, prevent stale patterns reaching consumers")
and the LES1 TEMPLATE-NOTES Category A/B framework were the entire
justification for Wave 1 task **LCL-003** ("Add template-validate smoke test
that renders and imports each template's entrypoint"). This defect is
**precisely** the class LCL-003 was supposed to prevent — a template that
passes `/task-review` at source level, is copied correctly by `install.sh`,
reports success at `guardkit-init`, and produces a broken consumer project
with no diagnostic trail.

**Confirm during investigation:**

- Whether LCL-003 was actually implemented (the review recommended it; confirm
  commit history shows it landed)
- If implemented, why it didn't catch this — does the smoke test render the
  orchestrator template, and if so, does it check for the scaffold files?
- If not implemented, this becomes a dual finding: LCL-003 gap + init defect

## Required Investigation

1. **Reproduce**: Fresh `guardkit-init langchain-deepagents-orchestrator` into
   an empty directory. Confirm scaffold files are missing. Capture verbose
   output if available (`--verbose`, `--debug`, or env-var equivalent).

2. **Trace the init resolver**: Identify the module in
   `installer/core/commands/` (likely `lib/template_merger.py` or related)
   that walks the template source and decides which files to render.
   Establish whether it traverses `templates/other/<sub>/<sub>/` nesting.

3. **Compare with base template**: Does `guardkit-init langchain-deepagents`
   produce `pyproject.toml` / `AGENTS.md` in the consumer repo? If yes, the
   base template ships these files via a different path — investigate the
   divergence. If no, the bug is older than LCL-004/005 and all three
   `langchain-deepagents*` templates have been shipping broken scaffolds.

4. **Compare with fastapi-python**: Does `guardkit-init fastapi-python`
   produce the expected scaffold files? This is the 9.5/10 confidence
   template — if it works, the bug is orchestrator-specific; if it doesn't,
   the bug is CLI-wide and has been latent for much longer.

5. **Review manifest contract**: Check `manifest.json` schema and the
   orchestrator template's `manifest.json`. Determine whether templates must
   declare init-time outputs explicitly or whether the resolver auto-discovers
   the `templates/` subtree.

6. **Regression against LES1**: Read
   `.claude/reviews/TASK-REV-LES1-review-report.md`. Specifically verify
   whether LCL-003 (template-validate smoke test) was implemented and whether
   it covers the orchestrator template's scaffold files.

## Acceptance Criteria

### Fix

- [ ] `guardkit-init langchain-deepagents-orchestrator` into an empty directory produces:
  - [ ] `pyproject.toml` at project root (with `[providers]` extras from LCL-004)
  - [ ] `AGENTS.md` at project root (with R2A1 contract from LCL-005)
  - [ ] `agent.py` at project root (or `src/<project>/agent.py` per template design)
  - [ ] `langgraph.json` at project root
  - [ ] All other files declared by the template manifest
- [ ] `guardkit-init langchain-deepagents` and
      `guardkit-init langchain-deepagents-weighted-evaluation` both produce
      `pyproject.toml` and `AGENTS.md` correctly (regression check)

### Diagnostic trail

- [ ] `guardkit-init` fails loudly (non-zero exit, visible error) if a declared
      template output file fails to render
- [ ] `guardkit-init` emits a rendered-file manifest (count + list of files
      written) in its summary output, so consumers can verify completeness
      without manually grepping

### Regression prevention

- [ ] Implement or fix LCL-003 template-validate smoke test to cover **all
      three** `langchain-deepagents*` templates AND the `fastapi-python`
      template as canary. Test must: render the template to a temp dir,
      assert the presence of `pyproject.toml`, `AGENTS.md`, and the primary
      entry point, then `pip install .[providers]` + import the package's
      top-level module
- [ ] Smoke test runs as part of `install.sh` post-install validation OR as a
      `guardkit doctor` sub-check
- [ ] Document the `templates/other/<category>/` convention in the template
      authoring guide, explicitly including the nested `other/other/` bucket

### Forge repo recovery

- [ ] Re-run `guardkit-init langchain-deepagents-orchestrator` in the forge
      repo AFTER the fix lands; verify scaffold files now present
- [ ] Forge repo's `.guardkit/context-manifest.yaml` must survive the re-init
      (pre-existing file, should not be overwritten)

## Scope Boundaries

**In scope:**

- Root-cause the orchestrator template rendering gap
- Fix the resolver / manifest / template-shape issue (whichever layer is broken)
- Close the regression-prevention gap for all `langchain-deepagents*` templates
- Document the convention for template authors

**Out of scope:**

- Redesigning the template file-layout convention (accept current shape; fix
  the renderer to honour it)
- Adding new features to `guardkit-init` beyond the diagnostic-trail improvement
- Changes to other templates unless the investigation proves a common root cause

## Related

- `.claude/reviews/TASK-REV-LES1-review-report.md` — LES1 review, specifically
  LCL-003 (template-validate smoke test) and BLOCKER-2 (`[providers]` extras)
- `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`
  — LES1 §8 doc/code co-evolution principle
- `~/Projects/appmilla_github/forge/docs/research/ideas/forge-build-plan.md` —
  blocked pending this fix; `/system-arch` cannot run against an empty scaffold
- Source brief: `docs/reviews/deepagents-templates/TASK-REV-FORGE-INIT-orchestrator-template-scaffold-rendering-gap.md`

## Decision Checkpoint Expected Output

`/task-review` should produce findings on:

- Exact root cause (resolver vs manifest vs template-shape)
- Blast radius across the three `langchain-deepagents*` templates and other templates
- Whether LCL-003 landed and, if so, why it didn't catch this
- Specific fix path with code-level pointers

Then choose `[I]mplement` to create the fix tasks.

## Priority

**BLOCKER.** The forge is the pipeline orchestrator — the capstone agent of
the Software Factory. Every day spent on the Forge build against a broken
scaffold is wasted work. Additionally, the Forge has a hard dependency
sequence (nats-infrastructure → nats-core tests → specialist-agent Phase 3 →
forge). While the upstream prerequisites are being closed, fixing this
template defect is pure parallelisable work with no blocking dependencies.

## Capture for LES2

Regardless of fix outcome, this incident is **primary evidence** for LES2:

- A template passed `/task-review` at source level (LCL-004, LCL-005 acceptance)
- `install.sh` succeeded (correct files in correct paths in cache)
- `guardkit-init` reported success (no errors, clean summary)
- Consumer repo was broken (no packaging descriptor, no entry point, no AGENTS.md)
- No diagnostic trail until manual verification in the consumer repo

This is Category A (no diagnostic trail) + Category C (retry/re-render context
lost) + LES1 §8 (doc/code co-evolution failure) in a single incident. Write
it up as `cross-agent-lessons-from-forge-init-incident.md` in the guardkit
repo's `docs/research/ideas/` once the fix lands.

## Implementation Notes

- This is a review / analysis task. Execute via `/task-review TASK-REV-A925`.
- Recommend `--mode=architectural` given the cross-template scope and
  installer-layer involvement.
- Full source brief is preserved at
  `docs/reviews/deepagents-templates/TASK-REV-FORGE-INIT-orchestrator-template-scaffold-rendering-gap.md`
  and should be treated as the canonical problem statement.
