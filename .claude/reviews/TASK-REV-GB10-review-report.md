# Review Report: TASK-REV-GB10

**Mode**: Debugging (deep)
**Task**: Analyse vLLM local autobuild failures on GB10 ProMax
**Source log**: `docs/reviews/gb10_local_autobuild/api_feature_1.md`
**Reviewed**: 2026-02-23

---

## Executive Summary

Five issues were identified. Two are confirmed **GuardKit code bugs** with clear fixes.
Three are environment or infrastructure issues.

| # | Issue | Severity | Type | Status |
|---|-------|----------|------|--------|
| 1 | `SDK agent error: unknown` — stream truncated | Critical | Infrastructure | Root cause identified |
| 2 | `ValueError: 'partial' is not a valid CriterionStatus` | High | **GuardKit Bug** | **Confirmed + fix proposed** |
| 3 | `python` not found in PATH — test detection fallback broken | Medium | **GuardKit Bug** | **Confirmed + fix proposed** |
| 4 | `task_work_results.json` not written after SDK error | Low | Consequence of #1 | No independent fix needed |
| 5 | Graphiti not available | Info | Environment | No action needed |

---

## Issue 1 — `SDK agent error: unknown` (Critical) — **ROOT CAUSE CONFIRMED**

### Evidence

Every Player invocation in the feature run terminates after 270–480 seconds:

```
INFO: [TASK-70ED] task-work implementation in progress... (480s elapsed)
ERROR: [TASK-70ED] SDK API error in stream: unknown
  ✗ Player failed: SDK agent error: unknown
```

### Root Cause — CONFIRMED via Docker logs

`docker logs vllm-qwen3-coder` reveals the exact error happening in live requests:

```
ValueError: 'max_tokens' or 'max_completion_tokens' is too large: 32000.
This model's maximum context length is 65536 tokens and your request has
34006 input tokens (32000 > 65536 - 34006).
HTTP 400 Bad Request
```

The failure arithmetic:

| Parameter | Value | Source |
|-----------|-------|--------|
| `max_model_len` | **65,536** | `vllm-serve.sh` default → running container |
| `max_tokens` in every SDK request | **32,000** | Claude Code CLI hardcoded default |
| Input token threshold for failure | **33,536** | `65536 - 32000` |
| Actual input token count at failure | **~33,774–34,006** | Docker logs |

After 270–480 seconds of tool activity, the accumulated conversation history crosses ~33.5K input tokens. The next SDK request asks for `max_tokens=32000`, vLLM computes `32000 + 34006 = 66006 > 65536` and returns **HTTP 400**. The Claude Code CLI receives a 400 it cannot map to a named error type and sets `message.error = "unknown"`. GuardKit logs `SDK agent error: unknown`.

The `anyio` cancel scope error is a **secondary artifact** — it occurs when the SDK's `async_generator_athrow` cleanup runs in a different asyncio task context after the subprocess exits unexpectedly.

**Critically: the KV cache usage at the failure point is only ~4%.** The hardware has enormous headroom. The 65,536 cap is purely artificial.

### Fix Applied

**`scripts/vllm-serve.sh` — default `MAX_LEN` increased from 65536 → 131072.**

```diff
-MAX_LEN="${VLLM_MAX_LEN:-65536}"
+MAX_LEN="${VLLM_MAX_LEN:-131072}"
```

Applied to the global default (line 21), the `next`/`next-nvfp4` presets (lines 34, 48). The `30b` preset remains at 32768 (appropriate for that smaller model).

With 131072 context:
- Input token threshold before failure: `131072 - 32000 = 99,072` tokens
- This is ~3× the old threshold, meaning a full 50-turn session would need to accumulate >99K tokens to hit the limit — effectively never under normal use

### Restart Required

```bash
./scripts/vllm-serve.sh       # Restarts with max-model-len=131072
# Wait 3-5 min for 80B model to load
curl http://localhost:8000/health
```

### Model Consideration

Qwen3-Coder-Next FP8 (80B MoE) natively supports much larger contexts than 65K. The `131072` limit should be well within the model's capability. If 131K still proves insufficient for very long sessions, `VLLM_MAX_LEN=262144` can be tried as an env var override.

---

## Issue 2 — `ValueError: 'partial' is not a valid CriterionStatus` (GuardKit Bug — HIGH)

### Evidence

Crash traceback from `api_feature_1.md` line 341:

```
ValueError: 'partial' is not a valid CriterionStatus
  File "guardkit/orchestrator/autobuild.py", line 3083, in _display_criteria_progress
    promises = [CompletionPromise.from_dict(p) for p in promises_data]
  File "guardkit/orchestrator/schemas.py", line 149, in from_dict
    status=CriterionStatus(data.get("status", "incomplete")),
```

### Root Cause — Confirmed

**`synthetic_report.py` emits `"partial"` status, but `CriterionStatus` enum only has `"complete"` and `"incomplete"`.**

`guardkit/orchestrator/schemas.py:44–56`:
```python
class CriterionStatus(str, Enum):
    """Simplified from 3 states to 2 per YAGNI principle."""
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    # NO "partial" value
```

`guardkit/orchestrator/synthetic_report.py:218–256` (disk-check path):
```python
# Disk check for file patterns when worktree_path is provided
if worktree_path is not None:
    disk_found: List[str] = []
    for pattern in all_patterns:
        candidate = worktree_path / pattern
        if candidate.exists():
            disk_found.append(pattern)

    if disk_found:
        promises.append({
            "criterion_id": criterion_id,
            "criterion_text": criterion_text,
            "status": "partial",     # ← BUG: not in CriterionStatus enum
            ...
        })
```

The same `"partial"` status is emitted at lines 230 and 252 (directory reference check).

The `synthetic_report.py` function docstring explicitly documents this 3-state output (`"complete" | "partial" | "incomplete"`), but the enum was "simplified to 2 states" separately without updating the synthetic report generator.

### Why TASK-70ED Turn 1 Did Not Crash

TASK-70ED turn 1 used `git_only` state recovery, which does not include a `worktree_path` argument to the file-existence promise generator. Without `worktree_path`, the disk-check branch is never reached, so `"partial"` is never emitted. The 8 file-existence promises for the scaffolding task matched directly from the git `created_set`, yielding `"complete"` status.

TASK-C086 turn 1 used `git_test_detection` recovery. The `worktree_path` was provided, the disk-check branch fired for criteria that referenced files not in the git detection lists, emitting `"partial"` → crash.

### Fix

**Option A (recommended):** Add `PARTIAL = "partial"` to `CriterionStatus` and handle it in `_display_criteria_progress`.

```python
# schemas.py
class CriterionStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"      # add this
    INCOMPLETE = "incomplete"
```

**Option B (defensive, additional):** Sanitise unknown status values in `CompletionPromise.from_dict()`:

```python
# schemas.py — from_dict
raw_status = data.get("status", "incomplete")
try:
    status = CriterionStatus(raw_status)
except ValueError:
    status = CriterionStatus.INCOMPLETE  # fallback
```

**Option C (YAGNI-compliant alternative):** Change `synthetic_report.py` to emit `"incomplete"` instead of `"partial"` for disk-found files, since the enum was intentionally simplified to 2 states. This requires changing lines 230 and 252.

**Recommended:** Apply **Option A** (add PARTIAL to enum) **and Option B** (defensive sanitisation). Option C would lose the semantic distinction between "not found anywhere" vs "found on disk but not in git changes".

### Files to Change

- [guardkit/orchestrator/schemas.py](guardkit/orchestrator/schemas.py) — add `PARTIAL` to `CriterionStatus`
- [guardkit/orchestrator/autobuild.py](guardkit/orchestrator/autobuild.py) — handle `PARTIAL` in `_display_criteria_progress` display logic (lines 3128–3137)

---

## Issue 3 — `python` not found in PATH (GuardKit Bug — MEDIUM)

### Evidence

```
WARNING:guardkit.orchestrator.coach_verification:pytest not found, trying python -m pytest
ERROR:guardkit.orchestrator.coach_verification:Failed to run tests: [Errno 2] No such file or directory: 'python'
INFO:guardkit.orchestrator.state_detection:Test detection (TASK-70ED turn 1): 0 tests, failed
```

### Root Cause — Confirmed

`guardkit/orchestrator/coach_verification.py:279`:
```python
fallback_cmd = ["python", "-m", "pytest", "--tb=no", "-q"]
```

On Ubuntu/Debian (including the GB10), `python` is not in PATH by default — only `python3`. The `python` binary requires `python-is-python3` package to be installed, or explicit symlinking.

### Impact

- Primary `pytest` call fails (no `pytest` binary)
- Fallback `python -m pytest` also fails (`python` not found)
- Result: `0 tests, failed` even when test files exist
- State recovery falls back to git-only detection, losing test information
- TASK-70ED turn 1 shows 0 tests despite the scaffolding task having produced test files

### Fix

```python
# coach_verification.py:279 — change:
fallback_cmd = ["python", "-m", "pytest", "--tb=no", "-q"]
# to:
fallback_cmd = ["python3", "-m", "pytest", "--tb=no", "-q"]
```

Or more robustly, try multiple fallbacks:

```python
for python_cmd in ["python3", "python"]:
    try:
        fallback_cmd = [python_cmd, "-m", "pytest", "--tb=no", "-q"]
        ...
        break
    except FileNotFoundError:
        continue
```

### File to Change

- [guardkit/orchestrator/coach_verification.py](guardkit/orchestrator/coach_verification.py) — line 279

---

## Issue 4 — `task_work_results.json` not written (Consequence of Issue 1)

This is a direct consequence of Issue 1. When the SDK stream terminates with an error, `TaskWorkResult(success=False, ...)` is returned before any JSON is written to disk. The Coach then warns:

```
WARNING: task_work_results.json not found for TASK-XXX
```

**No independent fix needed.** The state recovery path (synthetic report generation) handles this. The quality of that recovery is improved by fixing Issue 2.

**Hardening recommendation (lower priority):** When the Coach operates from a synthetic report rather than `task_work_results.json`, it should be more conservative — e.g., require at least some test evidence before approving a feature task (not just a scaffolding task).

---

## Issue 5 — Graphiti not available (Informational)

```
INFO: Graphiti factory not available or disabled, disabling context loading
```

No action needed for autobuild to function. Configure `.guardkit/graphiti.yaml` if knowledge context is desired.

---

## Additional Finding: False Positive Approval of TASK-70ED

TASK-70ED was approved on turn 2 with `8/8 criteria verified (100%)` despite both turns failing with SDK errors. The approval path:

1. Turn 2 Player writes `player_turn_2.json` before crashing (state recovery type: `player_report`)
2. Coach AI runs against the player report (which has `"complete"/"incomplete"` status — no crash here)
3. Coach marks all 8 criteria verified via LLM text-matching on the synthetic file-existence report
4. Quality gate profile: scaffolding task → `tests_required=False` → passes without test evidence

**Is this a real false positive?** For a pure scaffolding task (create project directory structure), file existence IS the acceptance criterion. The Coach AI evaluating "files were created" against "create these files" acceptance criteria and approving is likely correct.

However, this means the autobuild system can approve work that was never fully executed by the Player LLM. The recovery → synthetic report → Coach AI approval chain should be logged more prominently as a synthetic approval to distinguish it from a genuine Player execution.

---

## Summary of Recommended Fixes

### Fix 1: `CriterionStatus.PARTIAL` (Bug — blocks TASK-C086 and all feature tasks on vLLM)

```python
# guardkit/orchestrator/schemas.py:44–56
class CriterionStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"      # ADD THIS
    INCOMPLETE = "incomplete"
```

Plus defensive sanitisation in `from_dict()` and handling of `PARTIAL` in `_display_criteria_progress`.

### Fix 2: `python3` fallback in test detection (Bug — breaks test detection on GB10/Ubuntu)

```python
# guardkit/orchestrator/coach_verification.py:279
fallback_cmd = ["python3", "-m", "pytest", "--tb=no", "-q"]  # was "python"
```

### Configuration: vLLM local inference

- Verify `max_model_len` covers full protocol + output context
- Check vLLM server logs for context-length errors at the 270–480s mark
- Pass explicit `max_tokens` in API requests
- Use `--skip-pre-loop` / `--max-turns 2` for initial local testing

---

## Review Results

```yaml
review_results:
  mode: debugging
  depth: deep
  findings_count: 5
  bugs_confirmed: 2
  recommendations_count: 4
  report_path: .claude/reviews/TASK-REV-GB10-review-report.md
  completed_at: 2026-02-23
```
