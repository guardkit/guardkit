---
id: TASK-AB-VERIFYCLI01
title: Implement --verify on the guardkit autobuild complete CLI
status: backlog
created: 2026-07-04T09:41:00Z
priority: low
tags: [autobuild, cli, feature-complete, verify, doc-cli-parity]
complexity: 3
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Implement --verify on the `guardkit autobuild complete` CLI

> **Status note: backlog, NOT scheduled — design-first / filed for later.**

## Description

Sourced from the 2026-07-04 retro cross-reference, §3 R3 (aperture gaps) and
§5 item 3 (housekeeping: "resolve the `feature-complete --verify` doc/CLI
mismatch (implement or correct the doc)").

The mismatch as found by the xref: the command doc
(`installer/core/commands/feature-complete.md:29`) advertised a `--verify`
flag ("re-run tests after merge"), but the CLI wrapper
(`guardkit/cli/autobuild.py:1095-1114`) does not implement it. The doc half
has since been corrected: `feature-complete.md:29` now marks `--verify` as
**slash-command workflow only — not implemented on the
`guardkit autobuild complete` CLI** and references this task ID
(TASK-AB-VERIFYCLI01). This task is the other half: actually implement the
flag on the CLI so the two surfaces converge on the stronger behaviour.

Why it matters beyond hygiene: R3 showed post-merge verification is a real
aperture — `after_wave: [2,3,4]` left the final waves ungated and `tests/`
outside every gate, so nothing re-ran the suite at completion. A working
`--verify` on the CLI gives headless/scripted completions the same
post-merge test re-run the slash-command workflow performs (step 11 of the
documented flow: "Run tests (if `--verify`)").

## Acceptance Criteria

- [ ] AC-001: `guardkit autobuild complete FEAT-XXX --verify` re-runs the
      project's test suite after the merge and reports the result; a
      failing verification is surfaced loudly with a non-zero exit code (it
      does not un-merge, but it must never print success).
- [ ] AC-002: Without `--verify`, behaviour is byte-for-byte today's
      (backward compatible; the flag is additive).
- [ ] AC-003: The verification runs the tests in the merged target context
      via a subprocess with the project's own interpreter/venv — not
      guardkit's — so a merged-in missing dependency cannot be masked by
      guardkit's environment.
- [ ] AC-004: The CLI path shares its logic with the slash-command
      workflow's verify step (one implementation, two entry points) rather
      than duplicating a second test-invocation path.
- [ ] AC-005: `installer/core/commands/feature-complete.md` is updated to
      remove the "slash-command workflow only" caveat (and the reference to
      this task) once the CLI flag lands; `--help` output documents the
      flag.
- [ ] AC-006: Regression tests: (a) `--verify` triggers the post-merge test
      run; (b) verify-failure → non-zero exit + explicit failure text;
      (c) no `--verify` → no test run, unchanged output; (d) a test run
      that cannot start (no runner) is reported as UNVERIFIED, never as a
      pass.

## Implementation Notes

File:line anchors from the xref (§3 R3) and current state:

- `guardkit/cli/autobuild.py:1095-1114` — the `complete` command (no
  `--verify` today; comments at `:773` and `:960` note the gap explicitly).
- `installer/core/commands/feature-complete.md:29` — now reads:
  "`--verify` | Re-run tests after merge (slash-command workflow only —
  **not implemented on the `guardkit autobuild complete` CLI**; see
  TASK-AB-VERIFYCLI01)". Also `:69`, `:128`, `:171` (workflow step 11),
  `:589`, `:773`, `:960` reference the flag/caveat.
- The slash-command workflow's verify step (feature-complete.md step 11) is
  the behaviour to implement, not a new invention.

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **CLI wrappers share the wrapped API's acquisition/execution path**
  (`.claude/rules/cli-wrapper-shares-client-acquisition-path.md`): the CLI
  `--verify` must route through the same completion/verification logic the
  slash-command workflow uses — a CLI-only second implementation is exactly
  the divergence that rule documents (and how the doc/CLI mismatch arose in
  the first place).
- **Absence of failure is not success**
  (`.claude/rules/absence-of-failure-is-not-success.md`): a verification
  that could not run (no test runner found, runner crashed, zero tests
  collected) must surface as UNVERIFIED/absent — never as a green
  "verified". Pair the verdict with a positive-evidence precondition
  (tests_run > 0).
- **Namespace hygiene / runtime parity**
  (`.claude/rules/namespace-hygiene.md`,
  `.claude/rules/smoke-gate-is-feedback-not-terminator.md` arm b): run the
  post-merge tests as a subprocess against the merged project's own
  environment, not in-process where guardkit's `sys.path` can mask a
  missing import.
- **Display derives from the enforcement source**
  (`.claude/rules/display-must-derive-from-enforcement-source-not-proxy.md`):
  the "verified" line in CLI output must derive from the actual test-run
  result object, not from "the merge succeeded".
