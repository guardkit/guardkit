# Review Report: TASK-REV-C1B4

**Task**: Audit `installer/core/commands/lib/` for dead CLI shims and misfiled modules
**Mode**: technical-debt (audit)
**Depth**: standard
**Parent**: TASK-FIX-E841 (deleted `template_validate_cli.py` + its integration test)
**Date**: 2026-04-11

---

## Executive Summary

- **Primary finding (E841 follow-up)**: `upfront_complexity_cli.py` — the only remaining `*_cli.py` file in `commands/lib/` — **imports and runs cleanly**, but **nothing invokes it**. It is structurally healthy but functionally dead. Its companion `upfront_complexity_adapter.py` is likewise only imported by the dead CLI and a single test. Both are residue from abandoned TASK-005 design (ADR-005) that was never wired into `/impact-analysis` or `/task-work`.
- **Bonus finding**: The `template-validate-cli` symlink under `~/.agentecflow/bin/` is now **dangling** — E841 deleted the target file but did not clean up the stale symlink. `install.sh` does not prune stale symlinks on re-run, which is why this went unnoticed.
- **Directory hygiene**: `commands/lib/` contains ~87 Python files plus 8 Markdown files, 1 shell script, and 7 subpackages. Problems: **15 orphaned `test_*.py` files that pytest does not collect** (config: `testpaths = tests`), 4 demo scripts intermixed with production libraries, 8 READMEs and docs sitting next to code, and **3 versioned `graphiti_diagnose*.py` variants** with no imports and hardcoded infrastructure hosts.
- **Root cause of silent rot**: `install.sh`'s `setup_python_bin_symlinks()` function (lines 1797–1910) performs a blind `find ... -name "*.py"` walk and creates a shell symlink for every file. Dead files get promoted to "installed CLI tools" automatically — and when files are deleted, their symlinks rot silently. E841 was the first observed symptom; it will not be the last.

---

## Section 1 — CLI Shim Audit

### Scope verification

```bash
$ ls installer/core/commands/lib/*_cli.py
installer/core/commands/lib/upfront_complexity_cli.py
```

Confirmed: only one `*_cli.py` file remains after E841.

### `upfront_complexity_cli.py`

**Import check** (same method as E841 used for `template_validate_cli.py`):

```bash
$ python3 -c "from installer.core.commands.lib import upfront_complexity_cli; \
              print('IMPORT OK:', upfront_complexity_cli.__file__)"
IMPORT OK: .../installer/core/commands/lib/upfront_complexity_cli.py
```

**Result**: ✅ Imports cleanly. Dual-path import (`from .upfront_complexity_adapter import ...` with a fallback to flat `from upfront_complexity_adapter import ...`) resolves correctly — structurally unlike the broken `template_validate_cli.py` which depended on a non-existent `global.lib.*` path.

**End-to-end `--help` check**:

```bash
$ python3 installer/core/commands/lib/upfront_complexity_cli.py --help
usage: upfront_complexity_cli.py [-h] --task-id TASK_ID --title TITLE
                                 [--description DESCRIPTION] ...
Evaluate task complexity from requirements and recommend splitting
...
```

**Result**: ✅ Runs end-to-end without import errors. Full argparse help is displayed. Unlike the E841 shim, this file would work if something called it.

**Invocation search** (filtered to exclude historical artifacts `.claude/reviews/`, `docs/reviews/`, `docs/archive/`, `docs/implementation-plans/`, `docs/adr/`, `tasks/completed/`, `tasks/archived/`, `.claude/state/backup/`, and the task file itself):

| Search | Target | Live hits |
|---|---|---|
| Grep `upfront_complexity_cli` / `upfront-complexity-cli` across entire tree | Shell scripts, slash command `.md` files, Python modules | **0 live hits** |
| Grep `from .*upfront_complexity_cli` / `import upfront_complexity_cli` | Any Python importer | **0 hits** |
| Grep `upfront_complexity` across `installer/core/commands/*.md` (slash commands) | Any command referencing this file | **0 hits** |
| Inspect `/impact-analysis` command spec (`impact-analysis.md`) | Confirm which module it actually invokes | **Invokes `guardkit.planning.impact_analysis.run_impact_analysis` — a completely different module** |
| `tests/TASK-008-FINAL-TEST-RESULTS.txt` coverage report | Runtime coverage during that test run | **0% coverage, lines 13–356** |

Only non-historical references found:
- The file's own docstring (self-reference: `python3 upfront_complexity_cli.py --task-id ...`)
- Install logs documenting symlink creation (`Created: upfront-complexity-cli → upfront_complexity_cli.py`) — these prove only that the blind install-time walker picked it up, not that anything called it

**Symlink check**:

```bash
$ ls -la ~/.agentecflow/bin/upfront-complexity-cli
... -> .../installer/core/commands/lib/upfront_complexity_cli.py
```

Symlink exists, target resolves. But this is **not evidence of liveness** — see Section 2's root-cause note: `install.sh` blindly symlinks every non-test `.py` file in `commands/lib/` regardless of whether anything invokes it. Presence of the symlink proves only that the installer ran, not that the file is live.

**Companion module**: `upfront_complexity_adapter.py`

Searching for importers of the adapter (same filters applied):

| Importer | Status |
|---|---|
| `upfront_complexity_cli.py` | The dead CLI above — does not count as live |
| `tests/unit/test_upfront_adapter.py` | Test-only importer (via `importlib.util.spec_from_file_location`) |
| `docs/implementation-plans/TASK-005-revised-plan.md` | Historical design doc |
| `docs/adr/ADR-005-upfront-complexity-refactored-architecture.md` | Historical ADR |

**No live production import exists.** The adapter exists to be called by the CLI; the CLI is dead; the only thing keeping the adapter "green" is a single unit test that imports the file directly by path and tests it in isolation.

**Design-intent check**: Per ADR-005 and the TASK-005 revised plan, `upfront_complexity_cli.py` was designed to be the command-handler backing `/impact-analysis` (or an earlier precursor: upfront complexity evaluation during `/task-create` / `/task-work`). The actual `/impact-analysis` slash command, as it exists today, routes through `guardkit.planning.impact_analysis.run_impact_analysis` — a Python package inside the `guardkit` library, not this CLI shim. At some point the architecture pivoted and the CLI handler in `commands/lib/` was orphaned without being deleted. This is the **exact same failure mode** as E841's `template_validate_cli.py`: a handler built for an early version of a slash command, bypassed when the command was reworked to call a Python package directly, and left to rot.

### Classification

| File | Import check | `--help` check | Live invocation? | Classification | Recommendation |
|---|---|---|---|---|---|
| `upfront_complexity_cli.py` | ✅ OK | ✅ OK | **❌ None found** | **Dead** (structurally healthy, functionally orphaned) | **Delete** (together with `upfront_complexity_adapter.py` and its unit test) |

### Bonus finding — Dangling symlink from E841

```bash
$ ls -la ~/.agentecflow/bin/template-validate-cli
... -> .../installer/core/commands/lib/template_validate_cli.py
$ test -e ~/.agentecflow/bin/template-validate-cli && echo OK || echo DANGLING
DANGLING
```

E841 deleted `installer/core/commands/lib/template_validate_cli.py`, but the `template-validate-cli` symlink in `~/.agentecflow/bin/` still points at the deleted file. `install.sh` does not remove stale symlinks on re-run — it only creates or updates them when a target exists. This is the inverse bug of E841: the shim was dead because it had no working target; this symlink is dead because its target no longer exists. Both share the same operational risk: silent rot, no user impact report, unbounded staleness.

**Out-of-scope note**: Fixing this exact dangling symlink is cheap (`rm ~/.agentecflow/bin/template-validate-cli`), but the root cause — `install.sh`'s blind-walk-and-symlink — is systemic and deserves its own follow-up task. See Section 5.

---

## Section 2 — Directory Classification Summary

Source: Explore subagent shape-check of `installer/core/commands/lib/` (top-level files only; subpackages counted separately).

### Counts per category

| Category | Count |
|---|---|
| command-library (imported by a slash command or orchestrator that a slash command invokes) | 63 |
| test-file (`test_*.py` in wrong location) | 15 |
| demo-script (`demo_*.py`) | 4 |
| documentation (`.md`) | 8 |
| shell-script (`.sh`) | 1 |
| cli-entry-point (has `main()` or `if __name__`, not imported) | 3 |
| versioned-duplicate (`_v2`, `_v3`) | 2 |
| orphan (nothing imports + no CLI entry) | **1 hidden orphan** (see below) |
| **Total Python files (top-level)** | **~87** |

Plus **7 subpackages** (`agent_validator/`, `agentic_init/`, `clarification/`, `metrics/`, `review_modes/`, `template_init/`, and data dirs `review_templates/`, `templates/`).

### CLI entry-points (3)

- `graphiti_check.py` — has a dedicated wrapper script, excluded from blind symlink (install.sh line 1859). Live — used by `/task-review` and other commands via the wrapper.
- `graphiti_diagnose.py` — standalone diagnostic, not imported anywhere. Exploratory but plausibly useful for troubleshooting.
- `upfront_complexity_cli.py` — **dead** (see Section 1).

### Hidden orphan

The Explore subagent reported "no orphans", but its classifier gave `upfront_complexity_adapter.py` a pass because it is imported by `upfront_complexity_cli.py`. Since the CLI itself is dead (no live caller), the adapter is effectively orphaned too:

- `upfront_complexity_adapter.py` — imported only by `upfront_complexity_cli.py` (dead) and `tests/unit/test_upfront_adapter.py` (test-only, uses `importlib` path-based loading). No live production code path reaches it.

This is a case of a **transitive orphan**: a module kept alive by a single importer that is itself dead. A naive "is it imported anywhere?" classifier won't catch this; you need to walk the live-reachability graph from entry points. For this review I traced it manually.

### Versioned duplicates (2)

All three `graphiti_diagnose*.py` files share the same mtime and are all blindly symlinked by `install.sh` into `~/.agentecflow/bin/`:

| File | Abstraction | Hardcoded host? | Classification |
|---|---|---|---|
| `graphiti_diagnose.py` | Uses `guardkit.knowledge.graphiti_client.GraphitiClient` (async, correct abstraction layer) | No — reads from `load_graphiti_config()` | Likely the current standard |
| `graphiti_diagnose_v2.py` | Direct Redis via `redis.Redis("whitestocks", 6379)` | **Yes** — hardcoded `whitestocks:6379` | Exploratory fallback written when graphiti-core wasn't returning results |
| `graphiti_diagnose_v3.py` | Direct Redis via `r.execute_command("GRAPH.LIST")`, iterates hardcoded target_graphs list | **Yes** — hardcoded `whitestocks:6379` | Even more exploratory — schema probe, embedded target-graph list |

**Reading of the history** (from the file docstrings): These are not semantic versions — they're **three attempts to debug a specific Graphiti/FalkorDB issue** (likely "graphiti-core is searching and finding nothing"). `v2` bypassed the Graphiti abstraction to go straight to Redis; `v3` went further and inspected the multi-graph schema directly. Once the underlying issue was understood, none of the scripts were deleted. All three now coexist, all three get symlinked into `bin/` on every install, and none of them can run on any machine except the one with `whitestocks:6379` reachable.

### Subpackages (sampling)

The subpackages are internally structured and do not appear to be affected by the kitchen-sink problem. They are out of scope for this review (scope is top-level files).

### Notable observations

1. **Mixing of concerns is real**: production libraries, test files, demo scripts, exploratory diagnostics, README docs, and a shell script all coexist at the same directory level. This is the environment in which E841's shim rotted unnoticed — there is no convention that tells a reader "this file is supposed to be alive" vs. "this file is a demo".
2. **The blind-symlink installer amplifies the problem**: every non-`test_` `.py` file at this level gets promoted to a shell command in `~/.agentecflow/bin/`. The demo scripts (`demo-plan-markdown`, `demo-template-qa`, etc.), the exploratory diagnostics (`graphiti-diagnose-v2`, `-v3`), and the dead CLI (`upfront-complexity-cli`) all become global commands on every user's PATH via this mechanism. Users do not know that these are not intended to be called.
3. **No true orphans in the narrow sense**: the Explore pass found no file that is both un-imported AND lacks a `main()` entry. Every file has at least one reason to exist. The problem is that "has an entry point" and "is something you should run" are not the same thing.

---

## Section 3 — Test File Location Finding

**Question**: Are `test_*.py` files in `commands/lib/` collected and run by pytest? If so, should they be moved to `tests/`?

### Evidence

`pytest.ini`:

```ini
[pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests           # ← critical line
```

`pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

**Both config files set `testpaths = tests`.** This means pytest's default auto-collection walks only the `tests/` directory. It does **not** walk `installer/core/commands/lib/`. The 15 `test_*.py` files there will be collected **only** if someone explicitly runs:

```bash
pytest installer/core/commands/lib/test_X.py
# or
pytest installer/core/commands/lib/
```

Neither invocation appears in any CI config, pre-commit hook, or `/task-work` quality gate that I could find.

### The 15 orphaned test files

```
test_agent_invocation_tracker.py
test_agent_invocation_validator.py
test_complexity.py
test_complexity_comprehensive.py
test_enforcement_resilience.py
test_full_review.py
test_fulltext_fix.py
test_micro_basic.py
test_micro_task_detector.py
test_micro_workflow.py
test_phase_gate_validator.py
test_plan_integration.py
test_plan_markdown.py
test_quick_review.py
test_refinement_handler.py
```

### Finding

**These tests are not run automatically by any gate**. They are technically importable pytest files, but they exist outside the test discovery path. They fall into one of three states, which I did not individually investigate (out of scope — the question was "collected and run"?):

- (a) **Duplicates** of tests that already live under `tests/` (safe to delete once verified)
- (b) **Unique coverage** that was never moved to `tests/` (needs migration)
- (c) **Dead tests** against APIs that have since changed (same failure mode as E841's `test_template_validation_cli.py` which asserted against `parse_args` that no longer existed)

**Recommendation**: Audit each file individually in a follow-up task. For each: either (1) move to `tests/unit/` and confirm it still passes, or (2) delete if duplicative or broken. Do **not** bulk-move — some of them are likely dead in the same way the E841 test file was dead, and blind-moving them into the collected path would introduce failures into the suite.

---

## Section 4 — Graphiti Diagnose Versioning Finding

**Question**: Which version of `graphiti_diagnose*.py` is live, and are the others dead?

### Evidence

| File | First 20 lines tell us | Imported by anything live? | Symlinked into `bin/`? |
|---|---|---|---|
| `graphiti_diagnose.py` | GraphitiClient + `load_graphiti_config()` — **correct abstraction** | No — standalone CLI | Yes (`graphiti-diagnose`) |
| `graphiti_diagnose_v2.py` | Bypasses Graphiti, uses `redis.Redis("whitestocks", 6379)` directly — **hardcoded host** | No | Yes (`graphiti-diagnose-v2`) |
| `graphiti_diagnose_v3.py` | Same direct-Redis approach, enumerates a hardcoded target_graphs list for schema probing | No | Yes (`graphiti-diagnose-v3`) |

No Python module in the repo imports any of the three. No slash command references them. No shell script calls them. No hook calls them. The only "evidence of use" is the fact that `install.sh` creates the three symlinks on every install (confirmed by the install log artifacts under `docs/reviews/linux_install/`).

### Finding

- **`graphiti_diagnose.py`** is the one worth keeping: it uses the project's own Graphiti abstraction and reads config from `load_graphiti_config()`, so it works on any machine with a valid `.guardkit/graphiti.yaml`.
- **`_v2.py` and `_v3.py` are hardcoded to `whitestocks:6379`** (this user's Synology NAS, per `graphiti-knowledge-graph.md`). They are not portable. They are **single-use diagnostic scripts** that were written to debug a specific incident and then left behind. On any other machine they will immediately fail with a connection error. They do not belong in the installed `bin/` directory.

**Recommendation**:
- Keep `graphiti_diagnose.py`.
- Delete `graphiti_diagnose_v2.py` and `graphiti_diagnose_v3.py`, OR move them under `docs/troubleshooting/graphiti-diagnostics/` as historical exploration notes.
- Do not preserve them under the `commands/lib/` tree where the installer will continue to symlink them.

---

## Section 5 — Recommended Follow-up Tasks

Each task below is individually actionable. Hashes are intentionally left as `{hash}` — they will be generated by `/task-create` when `[I]mplement` is chosen, or by the reviewer manually.

### Priority: medium (address soon)

1. **TASK-FIX-{hash} — Delete dead `upfront_complexity_cli.py` + `upfront_complexity_adapter.py` + their unit test.**
   *Rationale*: Same failure mode as E841's `template_validate_cli.py` — structurally healthy but functionally orphaned from an abandoned TASK-005 design that never made it into any live command path. The one unit test (`tests/unit/test_upfront_adapter.py`) only exercises the adapter in isolation via `importlib.util` and does not prove live integration. Deleting all three files removes ~350 lines of dead code and prevents future confusion about what `/impact-analysis` actually uses.
   *Evidence*: Section 1, Section 2 "hidden orphan".

2. **TASK-FIX-{hash} — Clean up dangling `template-validate-cli` symlink under `~/.agentecflow/bin/` and teach `install.sh` to prune stale symlinks on re-run.**
   *Rationale*: E841's cleanup was incomplete — the symlink points at a deleted file. More broadly, `setup_python_bin_symlinks()` in `install.sh` (lines 1797–1910) never removes symlinks whose targets have been deleted, so every time a `commands/lib/` file gets removed, its symlink rots. Add a pre-pass that walks `~/.agentecflow/bin/`, tests each symlink with `[ -e ]`, and removes any dangling entries before creating new ones.
   *Evidence*: Section 1 "Bonus finding".

3. **TASK-ISH-{hash} — Replace `install.sh`'s blind directory walk with an explicit CLI manifest.**
   *Rationale*: The **root cause** of both E841 and this review: `install.sh` lines 1826–1910 find every non-test `.py` file in `commands/lib/` and symlink it into `~/.agentecflow/bin/` without any signal that the file was intended to be a user-facing CLI. This promotes demo scripts, exploratory diagnostics, and dead handlers to globally-installed commands. Replace with an opt-in manifest (a `bin-entries.txt` or `[tool.guardkit.bin-entries]` section in `pyproject.toml`) listing the files that should become shell commands. Everything else stays internal. This is the structural fix that prevents the next E841.
   *Evidence*: Section 2 "Root cause of silent rot", Section 4 (v2/v3 hardcoded scripts got symlinked into bin/ despite being single-use).

### Priority: low (tidy-up, not urgent)

4. **TASK-TSE-{hash} — Audit and relocate the 15 orphaned `test_*.py` files in `installer/core/commands/lib/`.**
   *Rationale*: `testpaths = tests` in both `pytest.ini` and `pyproject.toml` means these files are not auto-collected. Some are likely dead (E841 already found one broken test file in this directory), some may be duplicates of existing `tests/` content, some may be unique coverage. Audit each individually: move to `tests/unit/` if unique and passing, delete otherwise. **Do not bulk-move** — dead tests will break the suite if suddenly collected.
   *Evidence*: Section 3.

5. **TASK-FIX-{hash} — Delete or archive exploratory `graphiti_diagnose_v2.py` and `graphiti_diagnose_v3.py`.**
   *Rationale*: Both hardcode `whitestocks:6379` and cannot run on any machine but the original user's. They were written to debug a specific incident, not as portable tools. Keep `graphiti_diagnose.py` (uses the `GraphitiClient` abstraction and reads config). Optionally relocate v2/v3 under `docs/troubleshooting/graphiti-diagnostics/` as historical notes rather than deleting outright.
   *Evidence*: Section 4.

6. **TASK-REF-{hash} — Relocate demo scripts and verification shell script out of `commands/lib/`.**
   *Rationale*: `demo_agent_tracker_integration.py`, `demo_phase_gate_integration.py`, `demo_plan_markdown.py`, `demo_template_qa.py`, and `verify_micro_implementation.sh` are manual runners for development, not part of the slash-command library. They should live under `examples/` or `scripts/` so that nothing in `commands/lib/` is ambiguous about whether it is "live". Pairs naturally with task #3 (bin manifest) — once the manifest is in place, moving these out of `commands/lib/` is purely cosmetic.
   *Evidence*: Section 2 counts (4 demos + 1 shell script at top level).

7. **TASK-REF-{hash} — Relocate the 8 Markdown files (`README*.md`, `*_README.md`, spec docs) out of `commands/lib/`.**
   *Rationale*: `README.md`, `README-CHECKPOINT-DISPLAY.md`, `README-PLAN-MODIFIER.md`, `QUICK-START-PLAN-MODIFIER.md`, `QUICK_REVIEW_API.md`, `AGENT_TRACKER_INTEGRATION.md`, `MICRO_TASK_README.md`, and `graphiti-preamble.md` should live under `docs/internals/commands-lib/` or similar. Code and documentation at the same directory level is exactly the visual noise that let the E841 shim hide in plain sight. Note: `graphiti-preamble.md` is specifically referenced by `/task-review` spec — the move must update that reference.
   *Evidence*: Section 2 counts.

### Not recommended

- **Do not** refactor the 63 legitimate `command-library` files. They are the directory's intended content and they work.
- **Do not** move the 7 subpackages. They are internally structured and out of scope for this review.

---

## Analysis Metadata

- **Files inspected directly**: `upfront_complexity_cli.py`, `upfront_complexity_adapter.py` (import only), `graphiti_diagnose.py` (first 20 lines), `graphiti_diagnose_v2.py` (first 20 lines), `graphiti_diagnose_v3.py` (first 20 lines), `install.sh` (sections 1797–1910), `pytest.ini`, `pyproject.toml`, `impact-analysis.md`
- **Grep passes**: ~12, filtered against historical artifacts per task notes
- **Symlink checks**: `~/.agentecflow/bin/` directory listing, dangling-symlink probe for `template-validate-cli`
- **Import checks**: `python3 -c "from ... import ..."` for `upfront_complexity_cli` + `python3 ... --help` end-to-end run
- **Subagent delegation**: Explore subagent for the Section 2 shape-check across ~87 files (per task notes recommending parallel reads for this step)
- **Historical artifacts excluded from "live reference" counts**: `.claude/reviews/`, `docs/reviews/`, `docs/archive/`, `docs/implementation-plans/`, `docs/adr/`, `tasks/completed/`, `tasks/archived/`, `.claude/state/backup/`, and the task file itself

## References

- Parent fix task: [TASK-FIX-E841](../../tasks/in_review/TASK-FIX-E841-repair-or-deprecate-template-validate-cli.md)
- Target directory: [installer/core/commands/lib/](../../installer/core/commands/lib/)
- Install script: [installer/scripts/install.sh](../../installer/scripts/install.sh) (lines 1797–1910)
- ADR-005 (historical context for the dead CLI): [docs/adr/ADR-005-upfront-complexity-refactored-architecture.md](../../docs/adr/ADR-005-upfront-complexity-refactored-architecture.md)
