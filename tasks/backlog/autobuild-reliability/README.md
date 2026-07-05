# autobuild-reliability — task index

Seventeen tasks (15 filed 2026-07-04, 2 on 2026-07-05 from the ABL-001 run-3
credential-leak retro) from the retro cross-reference
[`docs/retro/autobuild-retro-xref-2026-07-04.md`](../../../docs/retro/autobuild-retro-xref-2026-07-04.md)
(five retros: R1 `nats_core` stub, R2 parallel-wave worktree pollution,
R3 self-defeating boundary tests, R4 undefined BDD step, R5 ABL-005 infra
chain / `--resume` venv-resolution — see xref §8 addendum). Every task
carries a "Regression constraints" section naming the `.claude/rules/*.md`
rules that bound its fix — read it before touching the code.

Ten tasks are being implemented in the same session that filed them
(**implementing-now**; the task files are the tracking records). Five are
filed for later (**design-first**; do not pick up without a design pass) —
four from the retro xref plus one filed by the 2026-07-04
post-implementation code review of this batch.

| Task | Priority | Status | What |
|---|---|---|---|
| [TASK-AB-STALEATTRIB01](TASK-AB-STALEATTRIB01-actionable-parity-feedback-authorship-join.md) | high | implementing-now | Actionable parity/smoke feedback (`test_output`, conditional rationale) + authorship join against `files_authored` with narrow stale-assertion permission (§5 items 4+5) |
| [TASK-AB-NULLEVID01](TASK-AB-NULLEVID01-deterministic-null-evidence-guard.md) | high | implementing-now | Deterministic approve→feedback override when evidence `gathering_status != "complete"`, incl. `coach_turn_N.json` re-persist (§5 item 7) |
| [TASK-AB-SKIPVIS01](TASK-AB-SKIPVIS01-skip-count-visibility.md) | medium | implementing-now | Thread `tests_skipped` through the independent-test oracle as advisory evidence (absent → `None`) (§5 item 8) |
| [TASK-AB-STALLTAX01](TASK-AB-STALLTAX01-parallel-interference-stall-subtype.md) | medium | implementing-now | `STALL_PARALLEL_INTERFERENCE` co-fire stall subtype keyed on `failure_classification=='parallel_contention'` + failing-test aggregation in the stall message (§5 item 9) |
| [TASK-AB-WAVECTL01](TASK-AB-WAVECTL01-concurrency-affordances-final-wave-gate.md) | high | implementing-now | Wire `recommended_parallel` into concurrency resolution (env > flag > YAML > auto-detect), final-wave smoke-gate loader warning, `--auto-serialise-overlap` default-on (§5 items 6+10) |
| [TASK-AB-COACHSUBPROC01](TASK-AB-COACHSUBPROC01-coach-test-execution-subprocess-default.md) | medium | implementing-now | Make `coach.test_execution: subprocess` the default; SDK becomes opt-in (corpus-wide 100%-failure evidence) (§5 item 15) |
| [TASK-AB-BASETEMP01](TASK-AB-BASETEMP01-worktree-scoped-pytest-basetemp.md) | low | implementing-now | Worktree-scoped pytest `--basetemp` for orchestrator-run deterministic test executions (§5 item 16) |
| [TASK-AB-INVARIANTTEST01](TASK-AB-INVARIANTTEST01-transient-assertion-guidance.md) | medium | implementing-now | Transient-assertion ("invariant-not-snapshot") guidance in three Player-prompt locations + Coach-side check + negative-boundary spec guidance in /feature-plan (§5 item 13) |
| [TASK-AB-RESUMEVENV01](TASK-AB-RESUMEVENV01-resume-path-venv-resolution.md) | high | implementing-now | Resume-path venv resolution: probe `<worktree>/.venv` too, thread `venv_python` through the hash-match skip, WARN + record the interpreter instead of silent `sys.executable` fallback (xref §8 / R5 defect #4) |
| [TASK-AB-ZEROTESTLOUD01](TASK-AB-ZEROTESTLOUD01-zero-collected-tests-verifier-infrastructure.md) | high | implementing-now | Zero-collected-tests surfaced as verifier infrastructure: machine-readable marker + environment-stall co-fire + honest feedback framing; verdict semantics unchanged (xref §8 / R5 lesson #1) |
| [TASK-AB-ENVTAMPER01](TASK-AB-ENVTAMPER01-environment-integrity-contract.md) | high | design-first | Environment-integrity contract: post-bootstrap skip-guard dependency parity probe + product-file `sys.modules` probe as tree-sitter dialect DATA in guardkitfactory.wiring (cross-repo) (§5 item 11) |
| [TASK-AB-BDDAUTHOR01](TASK-AB-BDDAUTHOR01-bdd-authoring-sweep.md) | high | design-first | BDD authoring sweep, artefact-activated on authored glue; `scenarios_undefined` blocking within the sweep only; preserves `bdd-pending-is-not-failed` by construction (§5 item 12) |
| [TASK-AB-WTISO01](TASK-AB-WTISO01-per-task-worktree-isolation.md) | medium | design-first | Per-task worktree isolation for parallel waves — the structural fix for R2; design doc covering evidence boundary, checkpoints, rollback, locks, merge semantics (§5 item 14) |
| [TASK-AB-VERIFYCLI01](TASK-AB-VERIFYCLI01-implement-verify-on-autobuild-complete-cli.md) | low | design-first | Implement `--verify` on the `guardkit autobuild complete` CLI (doc currently marks it slash-command-only and references this task) (§3 R3 / §5 item 3) |
| [TASK-AB-REVIEWCLEAN01](TASK-AB-REVIEWCLEAN01-post-review-consolidations.md) | low | design-first | Consolidations deferred from the 2026-07-04 post-implementation code review: one pytest-summary parser, shared Coach-guard override-and-persist (single-persist-per-turn), `IndependentTestResult` factory, coach-turn walkers over `_coach_report_issues`, shared parity/smoke framing composer |
| [TASK-AB-SECRETSCRUB01](TASK-AB-SECRETSCRUB01-secret-scrubbing-publication-boundary.md) | high | ready-to-implement | Scrub secret-shaped strings at the evidence→publication boundary (task-md turn history, review summaries) + repo lint for tracked run-state artifacts — from the ABL-001 run-3 credential leak (2026-07-05) |
| [TASK-AB-HERMETICTEST01](TASK-AB-HERMETICTEST01-hermetic-env-test-guidance.md) | low | ready-to-implement | Hermetic-env test guidance: env-reading config tests must pin the full env surface (three-location prompt pattern + planner note + ops rule: no live creds in loop env) (2026-07-05) |

Do-not-refile ledger (already landed, per xref §4): `--max-parallel` /
`GUARDKIT_MAX_PARALLEL_TASKS`, A7B2/A7B3/ABFIX-005, `bootstrap_extras` +
uv-sources redirect, the eight 2026-06-17/18 follow-ups, PARITYWAVE01, and
full-suite last-wave gating via `smoke_gates.after_wave: "all"` (config, not
code).
