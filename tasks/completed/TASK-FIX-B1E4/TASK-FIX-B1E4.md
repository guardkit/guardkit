---
id: TASK-FIX-B1E4
title: Install ~/.agentecflow/bin/generate-feature-yaml symlink via bin-entries.txt
status: completed
task_type: implementation
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T16:55:00Z
completed: 2026-04-22T16:55:00Z
previous_state: in_review
state_transition_reason: "All 5 ACs verified; manifest entry lands symlink; R1 regression test green"
completed_location: tasks/completed/TASK-FIX-B1E4/
priority: low
complexity: 2
tags: [installer, bin-symlinks, feature-plan, r1-wiring, hygiene]
parent_review: TASK-REV-AC53
parent_task: TASK-AC-53445
implementation_mode: direct
depends_on: []
---

# Task: Install ~/.agentecflow/bin/generate-feature-yaml symlink via bin-entries.txt

## Problem Statement

`installer/core/commands/feature-plan.md` Step 8 (imperative execution
trace at lines 2176, 2200, and 2468) instructs the runtime to:

```
Execute: python3 ~/.agentecflow/bin/generate-feature-yaml …
```

but `~/.agentecflow/bin/generate-feature-yaml` is not present on the
current install. `ls ~/.agentecflow/bin/` shows symlinks for
`agent-enhance`, `agent-format`, `agent-validate`, `gk`, `gki`,
`graphiti-check`, `graphiti-diagnose`, `guardkit`, `guardkit-init` —
but no `generate-feature-yaml`. The root cause is that
`installer/core/commands/lib/generate_feature_yaml.py` is absent from
[`installer/core/commands/bin-entries.txt`](../../installer/core/commands/bin-entries.txt),
which that file's own header declares is the **sole source of truth**
for which Python scripts under `installer/core/commands/` get exposed
as CLI commands in `~/.agentecflow/bin/`:

> *"This file is the SOLE source of truth for which Python scripts under
> `installer/core/commands/` should be exposed as user-facing shell
> commands in `~/.agentecflow/bin/` by install.sh."*
>
> — `bin-entries.txt` preamble

The R1 linter wiring (TASK-FIX-3C9D) lives inside
`generate_feature_yaml.py` `main()` at
[`generate_feature_yaml.py:711-713`](../../installer/core/commands/lib/generate_feature_yaml.py#L711-L713).
Under a strict Claude-as-runtime that refuses to substitute paths for a
missing binary, the imperative Step 8 call would fail, and the R1 AC
linter would not run. The 2026-04-22 TASK-FIX-7B2E dynamic run fired
anyway, which implies Claude-as-runtime resolved the path to the repo's
`installer/core/commands/lib/generate_feature_yaml.py` directly or ran
the producer's logic inline — but that is interpretation-dependent and
the same non-determinism failure mode TASK-FIX-3C9D closed on the prose
side. Closing the installer-symlink gap makes the deterministic chain
Step 8 → producer → R1 linter hold without needing Claude-as-runtime to
fill in the missing binary.

## Origin

Filed from the [I]mplement path of TASK-REV-AC53's decision checkpoint
(verdict: **clean** on the TASK-AC-53445 delivery surface; this
observation was explicitly flagged as *out of scope* for the re-audit
and recommended for separate filing). Re-audit report:
[`docs/reviews/TASK-REV-AC53-reaudit-task-ac-53445.md`](../../docs/reviews/TASK-REV-AC53-reaudit-task-ac-53445.md)
§"Incidental observations" item 1.

## Scope

### In-Scope

1. Add one line to
   [`installer/core/commands/bin-entries.txt`](../../installer/core/commands/bin-entries.txt)
   under the "Library-resident CLIs" section:
   ```
   installer/core/commands/lib/generate_feature_yaml.py
   ```
   The basename-with-underscores-to-hyphens rule (documented in
   `bin-entries.txt` lines 11-13) will produce
   `~/.agentecflow/bin/generate-feature-yaml` on next install.
2. Verify the resulting symlink is invoked cleanly by running
   `installer/scripts/install.sh` locally (or an equivalent reinstall
   flow) and then running the producer directly:
   ```
   python3 ~/.agentecflow/bin/generate-feature-yaml --help
   ```
   — confirm it runs without Python path errors.
3. Verify the R1 linter header still fires end-to-end by re-running the
   existing subprocess-driven test
   `tests/integration/feature_plan/test_generate_feature_yaml_linter.py`
   (added by TASK-FIX-3C9D) after reinstall. It should still pass —
   this test exercises the producer script directly, so it is already
   the correct regression surface. No new test code needed.

### Out-of-Scope

- Changing anything about `generate_feature_yaml.py`'s implementation.
  The producer is correct as-is; the gap is purely deployment.
- Re-wiring Step 10.5 or the AC linter callsite. TASK-FIX-3C9D's
  remediation is already landed and correct.
- Auditing other missing bin entries. If this audit surfaces that other
  scripts are also missing from `bin-entries.txt`, file each as its own
  task — do not rollup here.
- Rewriting the installer's bin deployment logic. The manifest
  mechanism works; it just needs the missing entry.

## Acceptance Criteria

- [ ] `installer/core/commands/bin-entries.txt` lists
      `installer/core/commands/lib/generate_feature_yaml.py` under the
      "Library-resident CLIs" section, with a one-line comment
      explaining why (R1 linter producer; referenced by
      `feature-plan.md` Step 8's `Execute:` line).
- [ ] After running `installer/scripts/install.sh`,
      `ls -la ~/.agentecflow/bin/generate-feature-yaml` shows a symlink
      pointing to `installer/core/commands/lib/generate_feature_yaml.py`.
- [ ] `python3 ~/.agentecflow/bin/generate-feature-yaml --help` exits 0
      and prints the script's usage.
- [ ] `tests/integration/feature_plan/test_generate_feature_yaml_linter.py`
      continues to pass (no regression in R1 wiring).
- [ ] Install does not print an informational warning about
      `generate_feature_yaml.py` being an un-manifested `.py` file
      (`bin-entries.txt` lines 35-38 describe this warning).

## Implementation Notes

- `bin-entries.txt` already has a precedent for library-resident CLIs
  with explanatory comments — see `graphiti_diagnose.py` (lines 51-53).
  Follow that shape.
- Do **not** add a dedicated wrapper script in `install.sh`
  `create_cli_commands` — `generate_feature_yaml.py` is a straight
  `if __name__ == "__main__"` script and the symlink mechanism is
  sufficient. Wrappers are reserved for scripts that need PYTHONPATH
  shimming or argv massaging (see `graphiti-check` for the wrapper
  pattern).
- This is explicitly a **low-priority hygiene task**. It hardens the R1
  wiring chain against a stricter future runtime but does not change
  current behaviour — the linter fires today via Claude-as-runtime
  path resolution. Schedule after TASK-COH-RUN1 cohort runs land; do
  not block the cohort on this.

## Non-Goals / Guardrails

- Do not promote this to high-priority — the R1 wiring IS currently
  firing via path-resolution fallback (TASK-FIX-7B2E confirmed dynamic
  firing on 2026-04-22). This is hygiene, not correctness.
- Do not touch the `feature-plan.md` Step 8 `Execute:` line. The path
  is correct; the binary just needs to exist.
- Do not rewrite `install.sh`'s symlink logic. The manifest mechanism
  (TASK-ISH-D09E, TASK-FIX-CF8D) is deliberate and correct.

## Related

- Source of this task: [`docs/reviews/TASK-REV-AC53-reaudit-task-ac-53445.md`](../../docs/reviews/TASK-REV-AC53-reaudit-task-ac-53445.md) §"Incidental observations" item 1
- Bin-entries manifest: [`installer/core/commands/bin-entries.txt`](../../installer/core/commands/bin-entries.txt)
- Producer script: [`installer/core/commands/lib/generate_feature_yaml.py`](../../installer/core/commands/lib/generate_feature_yaml.py)
- Spec imperative that references the missing binary: [`installer/core/commands/feature-plan.md:2468`](../../installer/core/commands/feature-plan.md#L2468)
- R1 remediation that landed the callsite inside the producer: `tasks/completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md`
- Manifest rationale: `bin-entries.txt` preamble + TASK-ISH-D09E + TASK-FIX-CF8D
