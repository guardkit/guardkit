---
id: TASK-SELFFIX-001
title: Durable shadow receipts
task_type: feature
parent_review: TASK-REV-SELFFIX
feature_id: FEAT-8AD1
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
---
# Durable shadow receipts

The per-turn shadow receipt must survive the orchestration process ending immediately after
a verdict. Receipts: FEAT-8737 lost SMOKE-001 t1 and SMOKE-003 t2 receipt FILES (the queue
rows survived) because `schedule_qav_shadow` spawns a daemon thread that dies with the
process. Seam: `guardkit/qa/qav_shadow.py` (`schedule_qav_shadow`, line ~917) and its caller
in `guardkit/orchestrator/autobuild.py` (~line 4022). Binding spec:
docs/factory-self-fix-scope-and-buildplan.md §2 Fix A + §3.

## Acceptance Criteria
- [ ] A hermetic test proves: with the flag ON and a slow (injected) seat call, scheduling a shadow and letting the scheduling scope end immediately still produces the per-turn receipt file (the thread is non-daemon with the existing 60s timeout as its bound, or an equivalent bounded-join — the smaller honest change)
- [ ] Flag-OFF remains a provable no-op: no thread, no probe, no seat call, no file (existing tests stay green byte-for-byte in behavior)
- [ ] The verdict path is never blocked or delayed beyond the bound: a hanging seat (injected) cannot extend process shutdown past the existing 60s timeout ceiling; never-raise preserved on every path
- [ ] All existing lane tests in tests/qa/test_qav_shadow.py pass unchanged plus the new tests
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes
- Do NOT redesign the lane: same receipt paths, same queue sink, same absent-not-fail reasons.
- If choosing non-daemon: verify no other caller relies on daemon semantics (grep spawn sites).
