---
id: TASK-OBS-396E
title: sdk_debug default-on via repo allowlist, size-capped rotation, keep-out-of-git guarantee, Appendix A conformance
task_type: feature
priority: high
feature_id: FEAT-OBSC
wave: 4
implementation_mode: task-work
complexity: 6
dependencies: [TASK-OBS-C440, TASK-OBS-80FE, TASK-OBS-9F43]
status: backlog
decision_of_record: D-OBS-2 (FILED 2026-07-09) — gates OBS-3
created: 2026-07-09
---

# TASK-OBS-396E: sdk_debug default-on via repo allowlist, size-capped rotation, keep-out-of-git guarantee, Appendix A conformance

## Description

Flip `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG` semantics to a config-level default per
D-OBS-2, so Player/Coach raw traces (the flywheel's teacher data — Story B, the
DF-006 survival fallback) are captured by default in named non-client repos. Today
the capture is opt-in (`sdk_debug.py:31`, default OFF) and **zero sdk_debug dirs
exist anywhere on disk**; every frontier Player run since June is unrecoverable
teacher data.

**The D-OBS-2 prerequisite triple is unconditional**: (1) message-stream redaction
(TASK-OBS-C440, a hard dependency of this task), (2) keep-out-of-git guarantee and
(3) size-capped rotation — the latter two delivered inside this task, **structurally
ordered before the flip** (see Changes 2-3a: the default-on path refuses to activate
unless the caps are configured and the ignore check passes at startup, so a partial
delivery can never ship the flip with a defective guard). Two additional hard
dependencies this feature imposes beyond the D-OBS-2 triple: durability of the
captured dirs (TASK-OBS-80FE — sdk_debug output lives under the worktree and dies
with prune without it; archive home per D-OBS-4), and model attribution
(TASK-OBS-9F43), which feeds the Appendix A artifact-identity field.

## Changes

1. **Repo allowlist default** (D-OBS-2 verbatim): capture defaults ON only in
   `guardkit`, `study-tutor`, `forge`, `fleet-*`; client/FinProxy repos stay opt-in
   per run. Repo identity: derive from the repo root directory name with the git
   remote name as cross-check; the allowlist is a DATA constant in `sdk_debug.py`
   (structural, greppable), optionally overridable via config. The env var keeps
   absolute precedence in **both** directions (`GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=0`
   force-off in an allowlisted repo; `=1` force-on in a client repo for an authorized
   run).
2. **Size-capped rotation**: per-turn cap on `messages.jsonl` (truncate with an
   explicit `[TRUNCATED at <N> bytes]` marker line) and a per-task total cap on the
   `sdk_debug/` dir (oldest-turn pruning), both tunable via env with documented
   defaults (suggested: 20MB/turn, 200MB/task — operator policy, not the rule).
   Rotation must never make capture silently absent: a pruned turn leaves a
   `PRUNED.marker` naming what was dropped.
3. **Keep-out-of-git guarantee**: a CI test that (a) `git check-ignore` confirms the
   sdk_debug paths (worktree and archive-root forms) are ignored, and (b) the narrow
   `!` allow-patterns in `.gitignore` (the TASK-HMIG-009/010 audit exceptions under
   `.guardkit/autobuild/`) do NOT un-ignore any `sdk_debug/` path. The guarantee is a
   test, not a convention (structural-defence rule).
3a. **Structural flip-gating (D-OBS-2 ordering made runtime-enforced, not
   wave-enforced)**: the allowlist default-on path activates ONLY when its guards
   hold at startup — rotation caps resolve to positive values AND the
   keep-out-of-git check passes for the target sdk_debug dir. If either guard is
   absent/broken, capture stays OFF with a WARNING naming the failed prerequisite
   (loud absent-signal, never silent). This makes the "prerequisites before the
   flip" contract hold even against a partial or weakly-verified delivery of this
   task — the flip cannot ship with a defective guard.
4. **WS4 Appendix A conformance table** — the AC that makes capture = flywheel input
   by construction. Document, in `docs/guides/autobuild-instrumentation-guide.md`, a
   per-field map of the Appendix A contract
   (`ai-transition/docs/ws4-learning-flywheel-scope-and-build-plan-2026-07-07.md`,
   Appendix A) to capture location:
   | Appendix A field | Where captured |
   |---|---|
   | 1. Player input (full assembled prompt + injected context refs) | `prompt.txt` per turn/role; injected context refs enumerated (see below) |
   | 2. Raw pre-strip output (+ post-strip) | `messages.jsonl` (raw); post-strip = player report JSONs (archived by TASK-OBS-80FE) |
   | 3. Human curation events | **N/A in autobuild** (no human in the loop) — explicit documented gap, owned by FEAT-SPL-005 on the specialist-agent side |
   | 4. Artifact identity (trained-prompt hash, model/checkpoint id, role.yaml sha) | model id via TASK-OBS-9F43; role + turn in the dir structure; `prompt_profile` (the trained-prompt-hash analogue, wired by 9F43); agent-definition identity (guardkit's role.yaml-sha analogue = hash of the active agent .md / digest file) recorded alongside — each sub-field dispositioned, none silent |
   | 5. Correlation ids (planning correlation_id, task/feature ids, spec-id, run_id) | task/feature ids in dir structure + run_id join (TASK-OBS-9F43); planning correlation_id + spec-id are explicit N/A-for-autobuild (they originate in the WS1/forge planning loop, owner: FEAT-SPL-005 side) — stated as verified N/A, not silence |
   | 6. Memory retrievals actually injected (entry ids + scopes) | if the run injects fleet-memory retrievals into prompts, record ids+scopes alongside `prompt.txt`; if none are injected on the autobuild path, state that as a verified N/A, not silence |
   Each row is either captured-with-location or an explicit gap with an owner —
   "a role session that is not captured to this contract is not a flywheel input."
5. **Default-harness verification**: capture must be verified on the **LangGraph**
   harness (the default since TASK-HMIG-011), whose buffered-yield substrate differs
   from the streaming SDK harness (`selector.py:92` notes sdk_debug_dir is
   SDK-specific for stream preservation). If the LangGraph path yields no per-event
   stream to preserve, that is a surfaced, documented gap (absent signal ≠ captured),
   with prompt.txt capture still guaranteed (preservation happens in agent_invoker
   before harness selection, `agent_invoker.py:3966`).

## Acceptance Criteria

- [ ] AC-1: In a repo named `guardkit` (and a `fleet-x` fixture), a run with the env
      var **unset** produces sdk_debug dirs; in a fixture repo named like a client
      repo, the same run produces none; `=0`/`=1` override both directions. All four
      cases pinned by tests.
- [ ] AC-2: Caps enforced: an oversized synthetic stream yields a truncation marker at
      the configured byte cap; per-task pruning leaves `PRUNED.marker`. Capture never
      exceeds the caps and never silently drops without a marker.
- [ ] AC-2b: Structural flip-gating (Change 3a) pinned by tests: with rotation caps
      unset/invalid or the keep-out-of-git check failing, an allowlisted repo does
      NOT capture and a WARNING names the failed prerequisite; with both guards
      green, capture activates.
- [ ] AC-3: The keep-out-of-git CI test exists and passes, covering the `!`
      allow-pattern interaction.
- [ ] AC-4: The Appendix A conformance table exists in the instrumentation guide with
      every one of the 6 fields dispositioned (captured-with-location or
      explicit-gap-with-owner); fields 4-5 demonstrably joinable on a real events +
      sdk_debug pair.
- [ ] AC-5: Capture verified on the default (LangGraph) harness: either messages are
      preserved there too, or the gap is asserted by a test and documented — never
      inferred from absence.
- [ ] AC-6: Captured dirs survive worktree cleanup via the TASK-OBS-80FE archive
      (integration test joins the two: run → cleanup → archived sdk_debug present).

## Test Strategy

Fixture repos for allowlist identity; synthetic oversized streams for rotation;
`git check-ignore` assertions for the guarantee; one end-to-end joining capture →
archive. Every positive AC asserts presence of the artifact, never absence of error.
