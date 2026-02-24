# vLLM Autobuild Fixes

**Feature ID**: FEAT-7a2e
**Parent Review**: [TASK-REV-ED10](../../review_complete/TASK-REV-ED10-analyse-vllm-coach-sdk-failures-gb10-autobuild.md)
**Status**: Backlog — ready to implement
**Created**: 2026-02-23

---

## Problem

AutoBuild against a local vLLM server on the GB10 machine fails with `UNRECOVERABLE_STALL` at
Wave 2. The root cause is a model name mismatch in the Coach Validator: it hardcodes
`model="claude-haiku-4-5-20251001"` in its SDK call, but vLLM only serves `claude-sonnet-4-6`.
Every Coach turn returns `invalid_request` in ~0.8s and the stall detector fires after 3 turns.

A secondary issue (independent of the stall) is that the environment bootstrap fails on Debian/Ubuntu
(PEP 668 protection on system Python) with 0/6 packages installed.

These issues were analysed in TASK-REV-ED10 (revised) with high-confidence root cause identification.

## Solution

Six targeted tasks address all identified issues:

| Task | Recommendation | Priority | Effort | Files |
|------|---------------|----------|--------|-------|
| [TASK-FIX-f1a2](TASK-FIX-f1a2-coach-sdk-model-fix.md) | R1+R2: Coach SDK model fix + base URL bypass | **Critical** | Low | coach_validator.py |
| [TASK-FIX-b3c4](TASK-FIX-b3c4-bootstrap-venv-fallback.md) | R3: Bootstrap venv fallback for PEP 668 | High | Medium | environment_bootstrap.py |
| [TASK-FIX-d5e6](TASK-FIX-d5e6-failure-classification.md) | R4: SDK error classification + stall message | Medium | Low | coach_validator.py, autobuild.py |
| [TASK-FIX-g7h8](TASK-FIX-g7h8-align-model-fields.md) | R5: Align model fields + env var config | Medium | Low | agent_invoker.py, coach_validator.py |
| [TASK-DOC-i1j2](TASK-DOC-i1j2-vllm-serve-docs.md) | R6: Document SERVED_MODEL_NAME alignment | Low | Minimal | vllm-serve.sh, docs/ |
| [TASK-FIX-k3l4](TASK-FIX-k3l4-asyncio-cancel-scope.md) | R7: Suppress asyncio cancel scope noise | Low | Minimal | agent_invoker.py |

## Quick Win

**TASK-FIX-f1a2 alone unblocks GB10.** It is a 1-line removal (plus ~10 lines for the base URL
bypass helper). All other tasks improve robustness and observability but are not required to
get autobuild working against vLLM.

## Execution Order

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for the full 3-wave execution strategy.

Wave 1 tasks (TASK-FIX-f1a2 + TASK-FIX-b3c4) can be worked in parallel.
