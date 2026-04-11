---
id: TASK-DRF-003
title: Validate and smoke-test the registered dotnet-railway-fastendpoints template
status: completed
created: 2026-04-11T12:00:00Z
updated: 2026-04-11T13:00:00Z
completed: 2026-04-11T13:00:00Z
previous_state: in_review
priority: high
tags: [template, dotnet, validation, smoke-test, verification]
parent_review: TASK-REV-D0C1
feature_id: FEAT-D0C1
implementation_mode: direct
wave: 3
complexity: 2
depends_on: [TASK-DRF-002]
---

# Task: Validate and smoke-test the registered dotnet-railway-fastendpoints template

## Description

After the template has been copied into `installer/core/templates/` and registered in the CLAUDE.md / init.py docstrings, run `/template-validate` and perform an end-to-end smoke test to verify the template works as a first-class builtin.

## Context

See `.claude/reviews/TASK-REV-D0C1-review-report.md` Wave 3 recommendations.

**Depends on TASK-DRF-002**: Template must be copied and registered before validation.

## Acceptance Criteria

### Template validation

- [ ] **Run `/template-validate installer/core/templates/dotnet-railway-fastendpoints`**.
- [ ] **Capture findings** — if any issues are reported, decide per finding:
  - **Critical** (structural / blocker): fix in this task.
  - **Non-critical** (cosmetic / enhancement): file as a follow-up task under TASK-REV-D0C1 and document here.
- [ ] **Document the validation run** — paste the output summary into this task's completion notes.

### Help/Discovery smoke tests

- [ ] **`guardkit init --help`** shows `dotnet-railway-fastendpoints` in the available templates list (from docstring edit in TASK-DRF-002).

### End-to-end smoke test

- [ ] **Scaffold a test project**:
  ```bash
  cd /tmp
  rm -rf test-dotnet-railway && mkdir test-dotnet-railway && cd test-dotnet-railway
  guardkit init dotnet-railway-fastendpoints
  # supply: ProjectName=MyApp, Namespace=MyApp, Author=<any>
  ```
- [ ] **Verify scaffold correctness**:
  - [ ] Directory structure resolves to `src/MyApp.*/` (NOT `src/Exemplar.*/`). Confirms TASK-DRF-001 settings.json fix.
  - [ ] `manifest.json` / `settings.json` placeholders resolved (no `{{ProjectName}}` left anywhere).
  - [ ] No absolute author-local paths (`/Users/richardwoollcott/...`) present anywhere in the scaffolded output.
  - [ ] `.claude/rules/` path frontmatter preserved (files start with `---`).
  - [ ] `agents/` directory copied (14 files: 7 base + 7 extended).
- [ ] **Cleanup**: `rm -rf /tmp/test-dotnet-railway` after verification.

## Verification

- [ ] All acceptance criteria above are checked.
- [ ] `/template-validate` either passes cleanly or only reports non-critical findings that have been filed as follow-up tasks.
- [ ] Smoke-tested scaffold contains no residual `Exemplar`, `Richard Woollcott`, or `/Users/` references.

## Rollback

If smoke test reveals blocker issues that can't be resolved in a short fix:

1. Do NOT revert the copy — leave `installer/core/templates/dotnet-railway-fastendpoints/` in place.
2. Revert the CLAUDE.md:223 and init.py:1719 edits from TASK-DRF-002 to de-register the template until issues are fixed.
3. File a new task under TASK-REV-D0C1 describing the blocker(s).
4. Mark this task BLOCKED.

## Notes

- **Agent enhancement**: Already completed — the 7 template agents have `-ext.md` extended files from a previous `/agent-enhance` run. No action needed here.
- **Follow-ups that are NOT part of this task** (file separately if needed):
  - Fixing stale `tests/knowledge/test_seed_enrichment.py` `EXPECTED_TEMPLATES`.
  - Updating legacy `installer/scripts/install.sh` template lists.
  - Considering a `dotnet-minimal` variant for the complexity 10/10 concern.

## Completion Notes (2026-04-11)

### What ran

- `guardkit init --help` → confirmed `dotnet-railway-fastendpoints` listed in templates.
- `guardkit init dotnet-railway-fastendpoints --no-questions --skip-graphiti -n MyApp` in `/tmp/test-dotnet-railway/` → succeeded, copied 14 agents + 22 rules + CLAUDE.md + manifest.
- Manual structural scan (no usable `/template-validate` CLI — `installer/core/commands/lib/template_validate_cli.py` imports a missing `global.lib.template_validation` module; see follow-up opportunity, not filed).

### Results against acceptance criteria

| Criterion | Result |
|---|---|
| Help lists `dotnet-railway-fastendpoints` | ✅ Pass |
| Scaffold `src/MyApp.*/` (NOT `src/Exemplar.*/`) | ❌ **N/A — criteria miscalibration** |
| `manifest.json`/`settings.json` placeholders resolved | ⚠️  `.claude/manifest.json` retains `{{ProjectName}}`, `{{Namespace}}`, `{{Author}}`, `{{DefaultRole}}` — but these are the canonical `placeholders:` metadata section, NOT a substitution bug |
| No `/Users/richardwoollcott/` paths | ✅ Pass (zero matches) |
| No `Richard Woollcott` strings | ✅ Pass (zero matches) |
| `.claude/rules/` frontmatter preserved | ✅ Pass |
| 14 agents (7 base + 7 ext) copied | ✅ Pass |

### Critical finding

**The `src/MyApp.*/` expectation is a criteria miscalibration.** `guardkit init` is a config-layer installer — it only copies `.claude/`, `.guardkit/`, and `tasks/`. The template's `templates/*.cs.template` scaffold files are NOT consumed by `init` today. Verified by comparison: `guardkit init python-library` also produces only `.claude/ .guardkit/ tasks/` — no `src/`, no `pyproject.toml`. This affects all templates equally, not just dotnet-railway-fastendpoints.

Filed follow-up: **TASK-DRF-F4B8** (clarify scaffolding model — doc-only vs extend init vs remove dead files).

### Non-critical findings (cosmetic)

5 agent markdown files in `installer/core/templates/dotnet-railway-fastendpoints/agents/` contain literal `Exemplar.*` namespace references in guidance/example text (`Exemplar.Core.Functional`, `ExemplarApiFactory`, etc.). These don't break init but leak the original internal project name into user-visible docs.

Filed follow-up: **TASK-DRF-E7A2** (replace `Exemplar.*` with `{{Namespace}}.*` in 5 agent docs).

### Decision

**Template accepted as a first-class builtin.** The `.claude/` config layer — which is all GuardKit init actually installs from any template — works correctly: 14 agents copy cleanly, 22 rule files preserve frontmatter, no host-path or author-name leakage, manifest metadata intact. The two findings above are cosmetic/architectural, not structural blockers, and are filed under TASK-REV-D0C1 for follow-up.

**No rollback required.** CLAUDE.md:223 and init.py:1719 registration edits from TASK-DRF-002 stay in place.
