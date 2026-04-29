---
id: TASK-RUN-D6F4
title: Fix DGX runbook v3 deployment gaps
status: completed
created: 2026-04-28T18:30:00Z
updated: 2026-04-28T19:30:00Z
completed: 2026-04-28T19:30:00Z
priority: medium
tags: [docs, runbook, dgx-spark, llama-swap, infrastructure]
complexity: 3
previous_state: in_review
completed_location: tasks/completed/2026-04/
test_results:
  status: passed
  coverage: n/a
  last_run: 2026-04-28T19:15:00Z
---

# Task: Fix DGX runbook v3 deployment gaps

## Description

Six gaps were discovered while executing `RUNBOOK-v3-production-deployment.md` end-to-end on the DGX Spark on 2026-04-28. The deployment succeeded after fixes were applied inline, but the runbook itself still contains the broken commands. This task folds the six fixes back into the runbook so the next clean-room execution works first time.

Source of truth: [`docs/research/dgx-spark/RESULTS-v3-production-deployment.md`](../../docs/research/dgx-spark/RESULTS-v3-production-deployment.md) — see "Runbook gaps discovered while executing".

## Gaps to fix

### Gap #1: llama-swap v208 swaps models by default
The runbook config sets `ttl: 0` per model but does not declare which models can run concurrently. By default v208 evicts the previously-loaded model when a request hits a different one — `ttl: 0` only governs idle eviction, not request-driven eviction. First execution produced a thrash loop where each polled endpoint loaded a model, was canceled, and the next poll evicted it.

**Fix:** add `matrix.sets` and `hooks.on_startup.preload` blocks to the config in Phase 5.2:
```yaml
matrix:
  vars:
    qg: qwen-graphiti
    ne: nomic-embed
    qw: qwen36-workhorse
    gt: gemma4-tutor
  sets:
    all: "qg & ne & qw & gt"

hooks:
  on_startup:
    preload:
      - qwen-graphiti
      - nomic-embed
      - qwen36-workhorse
      - gemma4-tutor
```
Also bump `healthCheckTimeout: 300` → `600` for cold-start headroom on the 21 GB workhorse and 19 GB tutor.

### Gap #2: Python `guardkit graphiti` client config not patched
Phase 7 only patches `scripts/graphiti-mcp-config.yaml` (the MCP container). The Python client used by `guardkit graphiti add-context` reads `.guardkit/graphiti.yaml`, which still pointed at vLLM ports 8000/8001 after Phase 7 ran. Phase 8 (E2E seed) failed with `Connection error` retries until this was patched.

**Fix:** add to Phase 7 a sed pass against `.guardkit/graphiti.yaml`:
```bash
sed -i 's|http://promaxgb10-41b1:8000/v1|http://promaxgb10-41b1:9000/v1|g' .guardkit/graphiti.yaml
sed -i 's|http://promaxgb10-41b1:8001/v1|http://promaxgb10-41b1:9000/v1|g' .guardkit/graphiti.yaml
```

### Gap #3: llama-swap CLI flag style
Runbook uses `--config` and `--listen`. v208 takes `-config` and `-listen` (single dash). Affects Phase 5.3 launch command and the systemd unit's `ExecStart` in Phase 10.2.

### Gap #4: Graphiti GGUF glob casing
Phase 0.1 globs `*Q8*` (capital Q). Actual files on disk are `qwen2.5-14b-instruct-q8_0-...gguf` (lowercase q). Use `find -iname` or `*[Qq]8*`.

### Gap #5: `pkill -f "llama-server"` self-kills
In Phase 4.2, `pkill -f "llama-server"` matches the bash script running it (because the script text contains the literal string `llama-server`) and kills the script before it does anything else. Replace with `pkill -x llama-server` (basename match).

### Gap #6: VRAM ~5 GB above runbook estimate
Actual production VRAM was 65 GB vs. runbook's ~60 GB estimate. Workhorse and tutor are ~3 GB each higher than expected, likely from KV-cache contribution at 64K and 32K context. Update Phase 5.5 expected total to ~65 GB.

## Acceptance Criteria

- [ ] Phase 5.2 config snippet in `RUNBOOK-v3-production-deployment.md` includes `matrix.sets` declaring all four models can coexist
- [ ] Phase 5.2 config snippet includes `hooks.on_startup.preload` with all four models listed
- [ ] Phase 5.2 `healthCheckTimeout` raised to `600`
- [ ] Phase 7.1 sed block also patches `.guardkit/graphiti.yaml` with the 8000→9000 and 8001→9000 substitutions
- [ ] All `--config` and `--listen` flags in the runbook (including Phase 10.2 systemd unit) are single-dash
- [ ] Phase 0.1 `find` invocation uses case-insensitive matching for the Graphiti GGUF
- [ ] Phase 4.2 uses `pkill -x llama-server`, not `pkill -f "llama-server"`
- [ ] Phase 5.5 "Expected" total updated from "~60 GB" to "~65 GB" with the per-model breakdown from RESULTS-v3
- [ ] Cross-link from runbook to RESULTS-v3 added so future readers see the gap analysis

## Test Requirements

- [ ] Verify by re-reading the runbook section by section against the RESULTS-v3 gap notes
- [ ] (Optional, ideal) Dry-run `bash -n` the embedded shell snippets to catch syntax errors

## Implementation Notes

This is a documentation-only task. No code changes, no tests required. The fixes are well-scoped and the diffs should land in a single edit per phase. The two backup config files (`scripts/graphiti-mcp-config.yaml.pre-llamacpp.bak` and `.guardkit/graphiti.yaml.pre-llamacpp.bak`) and the archived vLLM scripts in `scripts/archive-vllm/` are correct from the live deployment — leave those alone.

Two follow-ups noted in RESULTS-v3 are **out of scope** for this task and should become separate tasks if pursued:
- **Follow-up #1**: tutor template-token leak (`<|channel>thought<channel|>` and `<think>...</think>`). Try `--reasoning off` first; if it works, that becomes a separate config-tuning task.
- **Follow-up #2**: tutor Modelfile has TEMPLATE only, no SYSTEM. Decide whether the fallback prompt is canonical or whether the training pipeline should emit a SYSTEM block.

## Test Execution Log

Documentation-only task — micro-task mode (complexity 3, .md-only edits, no
code, no unit tests). All AC verified by direct grep + YAML parse + `bash -n`.

**2026-04-28T19:15:00Z — verification pass:**

- Phase 5.2 config heredoc extracted and parsed via PyYAML — valid YAML,
  `healthCheckTimeout: 600`, `matrix.vars` contains all four short keys,
  `matrix.sets.all == "qg & ne & qw & gt"`, `hooks.on_startup.preload`
  lists all four model names.
- All `bash` code fences in the runbook concatenated and run through
  `bash -n` — no syntax errors.
- `grep` for `(--config|--listen).*(llama-swap|/opt/llama-swap)` returns no
  matches — all double-dash llama-swap flags removed (Phase 5.3 + Phase
  10.2 systemd unit).
- `grep` for `pkill` confirms Phase 4.2 uses `pkill -x llama-server`. The
  remaining `pkill llama-swap` reference is in the Appendix rollback (kills
  the *llama-swap* process, not llama-server) — correct as-is.
- Phase 0.1 globs use `find ... -iname "*q8*.gguf"` (lowercase + .gguf
  anchor) instead of the original capital-Q variants.
- Phase 5.5 expected total updated to `~65 GB` with the per-model
  breakdown table from RESULTS-v3 Follow-up #3.
- Phase 7.1 now sed-patches `.guardkit/graphiti.yaml` (with backup to
  `.pre-llamacpp.bak`) in addition to `scripts/graphiti-mcp-config.yaml`.
- Cross-link to `RESULTS-v3-production-deployment.md` added to runbook
  header (line 7).

**Out of scope, deliberately not fixed:**

- Phase 3.1 still uses `*Q8*` (capital Q) in the shard-detection glob.
  Lines 186/189. Not in AC. Currently harmless because the file isn't
  sharded — the `SHARD_COUNT >1` branch is skipped and the single
  `$GRAPHITI_GGUF` (resolved correctly in Phase 0.1) is copied. Would
  surface as a real bug if/when a sharded Q8 release is used. Not folded
  in to keep the diff tight to AC; can be a separate task if it ever
  matters.

**Acceptance criteria status:** all 9 acceptance items met. See file
`docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md` for the
applied edits.
