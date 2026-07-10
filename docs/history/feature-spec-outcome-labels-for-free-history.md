# /feature-spec — outcome-labels-for-free — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-spec outcome-labels-for-free — 2026-07-10T11:57:26Z

### Prompt

```
/feature-spec Outcome-label sidecar: when a TASK-REV / TASK-FIX / merge-review disposition lands, write a small structured label record (task/feature ids, verdict class — coach_correct | operator_caught | merge_review_caught | live_gate_caught, refs to the evidence dir it judges, timestamp) adjacent to the corresponding .guardkit/autobuild/{task_id}/ artifacts, so dataset harvests join labels by file read instead of retro archaeology. Node-local, append-only, no fleet infra. Consumer: QAV/coach harvest transforms (agentic-dataset-factory) and the WS4-S7 Chronicler; this is the "outcome labels for free" enabler from the 07-09 observability analysis (gap G6). RIDER (07-10, FEAT-OBSC merged): reconcile the sidecar's placement with the SHIPPED 80FE archive-before-prune seam (guardkit/worktrees/archive.py, hooked at WorktreeManager.cleanup) — a label written adjacent to live artifacts must survive the archive move (join by task_id in the archived copy too, or write to the archive home directly); labels also join the 9F43 run_id/attempt identity fields so Chronicler rows correlate. Consume the D-S10-1 trigger taxonomy: label class-coverage feeds the Coach v4 ≥10-per-DC-class floor (DC-03/05/08/14).
```

### Assistant response

I'll run the /feature-spec workflow for the outcome-label sidecar. Starting with Phase 1 context gathering — scanning the repo for the relevant seams (autobuild artifact layout, the 80FE archive seam, 9F43 identity fields, existing feature specs).
