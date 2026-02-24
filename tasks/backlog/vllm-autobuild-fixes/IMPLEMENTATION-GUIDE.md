# Implementation Guide: vLLM Autobuild Fixes

**Feature ID**: FEAT-7a2e
**Parent Review**: TASK-REV-ED10
**Priority**: Wave 1 tasks are critical — they unblock GB10 local autobuild

---

## Background

Two autobuild feature runs on the GB10 machine (FEAT-EC3C) failed due to a chain of infrastructure
issues. TASK-REV-AB3D fixed the first (Player model name mismatch in `vllm-serve.sh`). TASK-REV-ED10
analysed the remaining failures in the second run and produced 7 recommendations (R1–R7). This
feature implements those recommendations.

The most critical fix (R1) is a **1-line change**: remove `model="claude-haiku-4-5-20251001"` from
the Coach Validator's `ClaudeAgentOptions`. This change alone unblocks GB10 local autobuild.

---

## Wave 1 — Critical (run in parallel, unblocks GB10)

These two tasks can be executed in parallel as they modify different files.

### TASK-FIX-f1a2 — Coach SDK model fix + base URL bypass

**Why first**: This is the root cause of UNRECOVERABLE_STALL on GB10. Without this fix, every
Coach turn fails with `invalid_request` because vLLM doesn't know the Haiku model ID.

**Files**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Effort**: ~15 lines (remove 1 line + add ~10 lines for the base URL bypass helper)
**Risk**: Low. No-model Player path is already proven to work against vLLM.

### TASK-FIX-b3c4 — Bootstrap virtualenv fallback

**Why first**: The bootstrap failure (0/6 installs) is an independent issue that will affect any
Debian/Ubuntu host. While it wasn't the proximate stall cause in FEAT-EC3C, it will block any
test execution path that relies on the bootstrapped packages.

**Files**: `guardkit/orchestrator/environment_bootstrap.py`
**Effort**: ~40-60 lines (new PEP 668 detection + venv creation + state persistence)
**Risk**: Low. Fallback only activates on PEP 668 failure; existing paths unchanged.

---

## Wave 2 — Secondary improvements (run in parallel after Wave 1)

These tasks improve observability and code hygiene. They both touch `coach_validator.py` in
different sections — review for conflicts if running truly in parallel.

### TASK-FIX-d5e6 — Failure classification + stall message

**Files**: `guardkit/orchestrator/quality_gates/coach_validator.py`,
           `guardkit/orchestrator/autobuild.py`
**Effort**: ~20 lines
**Dependency**: TASK-FIX-f1a2 merged first (to avoid conflicting changes in coach_validator.py)

### TASK-FIX-g7h8 — Align model fields + env var support

**Files**: `guardkit/orchestrator/agent_invoker.py`,
           `guardkit/orchestrator/quality_gates/coach_validator.py`
**Effort**: ~20 lines (remove fields + add env var helper)
**Dependency**: TASK-FIX-f1a2 merged first

---

## Wave 3 — Documentation and maintenance (run in parallel, minimal risk)

### TASK-DOC-i1j2 — vLLM serve docs

**Files**: `scripts/vllm-serve.sh`, `docs/guides/simple-local-autobuild.md`
**Effort**: ~20 lines of comments/docs
**Dependency**: None — can run any time

### TASK-FIX-k3l4 — asyncio cancel scope noise

**Files**: `guardkit/orchestrator/agent_invoker.py`, `pyproject.toml`
**Effort**: ~15 lines (check SDK version first; if no upstream fix, add targeted handler)
**Dependency**: None — fully independent

---

## Execution Strategy

```
Wave 1 (parallel):  TASK-FIX-f1a2   TASK-FIX-b3c4
                          ↓                ↓
Wave 2 (parallel):  TASK-FIX-d5e6   TASK-FIX-g7h8
                          ↓                ↓
Wave 3 (parallel):  TASK-DOC-i1j2   TASK-FIX-k3l4
```

To unblock GB10 immediately, implement only TASK-FIX-f1a2. Then run:

```bash
ANTHROPIC_BASE_URL=http://localhost:8000 ANTHROPIC_API_KEY=vllm-local \
  guardkit autobuild task TASK-GLI-004 --verbose
```

The Coach should no longer stall after Wave 1.

---

## Verification

After TASK-FIX-f1a2 is deployed, verify with a full autobuild run. The following should no longer
appear in the logs:

```
SDK API error: invalid_request
Feedback stall: identical feedback (sig=...) for 3 turns with 0 criteria passing
UNRECOVERABLE_STALL
```

Instead you should see the Coach run pytest successfully via subprocess (when
`ANTHROPIC_BASE_URL=http://localhost:8000` is set) and return actual test results.
