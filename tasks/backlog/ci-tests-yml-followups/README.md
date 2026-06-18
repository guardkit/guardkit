# CI tests.yml follow-ups (2026-06-17)

Follow-ups surfaced while greening the `Tests` CI workflow after the TASK-HMIG-011
cutover (`DEFAULT_HARNESS` sdk→langgraph) had silently red-lined `tests.yml` for
~59 tests since 2026-06-12. The CI-green fix landed in commits `4d478818` (the 59,
5 clusters) and `4831563a` (a pre-existing flaky `test_concurrent_generation`,
fixed deterministically). CI is green as of `4831563a`.

These three are non-blocking improvements (the suite is green); they close the
coverage gap the fix introduced and remove latent flakiness.

| Task | Priority | What |
|---|---|---|
| [TASK-FIX-WIREGATECI01](TASK-FIX-WIREGATECI01-gate-wiring-gate-tests-in-ci.md) | medium | The 7 `test_wiring_gate` orchestration tests now run in **no** CI job (skipped in `tests.yml`, not listed in `seam-tests.yml`). Gate them in `seam-tests.yml` after an import-chain check. |
| ✅ [TASK-FIX-SDKPINCLEAN01](../../completed/TASK-FIX-SDKPINCLEAN01/TASK-FIX-SDKPINCLEAN01-remove-redundant-sdk-pin.md) (done 2026-06-18) | low | Remove the now-redundant per-test `GUARDKIT_HARNESS=sdk` pin in `test_sdk_environment_parity.py` (a module autouse fixture now covers it). |
| [TASK-FIX-DIGESTTOK01](TASK-FIX-DIGESTTOK01-deterministic-digest-token-tests.md) | low | `test_digest_in_target_token_range` passes in CI only via the word-based fallback (tiktoken absent); with tiktoken it fails (`player.md`=291<300). Make it deterministic across both. |

## Background

`.github/workflows/tests.yml` runs the unit suite **without** guardkitfactory or
the langchain stack (those are gated separately by `seam-tests.yml`, which checks
out the sibling repo + `pip install -e`). Harness-touching unit tests therefore
must pin `GUARDKIT_HARNESS=sdk` or `skipif(not guardkitfactory)`. The local dev
env (and the GB10) have both installed, which masks these failures locally.

Not in scope here (tracked elsewhere): the quarantine burn-down
(`TASK-INFRA-CIGREEN-BURN`), and the pre-existing
`test_agent_invoker_langgraph.py::test_env_var_routes_to_langgraph` "no `cwd=`"
red (a precondition for WIREGATECI01's AC-004).
