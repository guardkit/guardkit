#!/usr/bin/env python3
"""finalize_coach_corrective.py — fold the relabel + hard-case corrective layer
into the final Coach training set.

Consumes the output of the `coach-corrective-layer` workflow (16 relabel verdicts
+ 8 authored hard-case pairs) plus the curated splits, and writes under
~/coach-dataset/curated/:

  relabelled.jsonl       genuine false-approvals, REAL player_report + CORRECTED
                         (feedback) verdict, source=relabelled, weight 2.0
  hard_cases.jsonl       8 authored symptom→ideal-catch pairs, source=synthetic_hardcase
  train_final.jsonl      train.jsonl  +  genuine relabelled  +  hard_cases
  CORRECTIVE.md          summary of what the corrective pass changed

Usage: finalize_coach_corrective.py --workflow-output /tmp/.../tasks/<id>.output
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CUR = Path.home() / "coach-dataset" / "curated"


def truncate(s, n):
    s = "" if s is None else str(s)
    return s if len(s) <= n else s[:n] + " …[truncated]"


def render_prompt(rec: dict) -> str:
    pr = rec.get("player_report") or {}
    lines = [
        "You are the Coach in an adversarial Player-Coach build loop. Verify the "
        "Player's work against EACH acceptance criterion and return a verdict: "
        "`approve` only when every criterion is genuinely met with real (not mocked, "
        "not absent, not zero-cardinality) evidence; otherwise `feedback` naming the "
        "specific gap.",
        f"\n## Task: {rec['task_id']}\n{truncate(rec.get('task_excerpt'), 2500)}",
        "\n## Player report",
        f"- files_modified: {truncate(pr.get('files_modified'), 600)}",
        f"- files_created: {truncate(pr.get('files_created'), 400)}",
        f"- tests_run: {pr.get('tests_run')} | tests_passed: {pr.get('tests_passed')} "
        f"({pr.get('tests_passed_count')})",
        f"- implementation_notes: {truncate(pr.get('implementation_notes'), 900)}",
        f"- concerns: {truncate(pr.get('concerns'), 400)}",
        f"- completion_promises: {truncate(pr.get('completion_promises'), 600)}",
        "\nReturn the verdict as a fenced ```json block with keys: decision, "
        "criteria_verification, issues, rationale.",
    ]
    return truncate("\n".join(lines), 7000)


def render_completion(verdict: dict) -> str:
    out = {
        "decision": verdict.get("decision"),
        "criteria_verification": verdict.get("criteria_verification") or [],
        "issues": verdict.get("issues") or [],
        "rationale": verdict.get("rationale"),
    }
    return "```json\n" + json.dumps(out, ensure_ascii=False, indent=2) + "\n```"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow-output", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=CUR)
    args = ap.parse_args()
    out = args.out.expanduser()

    wf = json.loads(Path(args.workflow_output).read_text())
    result = wf.get("result", wf)
    relabels = result.get("relabels", [])
    hardcases = result.get("hardcases", [])

    worklist = {json.loads(l)["task_id"]: json.loads(l)
                for l in (out / "relabel_worklist.jsonl").open()}

    relabelled_rows, skipped = [], []
    for r in relabels:
        if not r:
            continue
        tid = r.get("task_id")
        if not r.get("is_genuine_false_approval"):
            skipped.append({"task_id": tid, "reason": r.get("reasoning", "")[:300],
                            "confidence": r.get("confidence")})
            continue
        rec = worklist.get(tid)
        if not rec:
            continue
        relabelled_rows.append({
            "split": "train", "source": "relabelled", "weight": 2.0,
            "repo": rec["repo"], "task_id": tid, "turn": rec["turn"],
            "decision": "feedback", "rule_cited": r.get("rule_cited"),
            "confidence": r.get("confidence"),
            "prompt": render_prompt(rec),
            "completion": render_completion(r["corrected_verdict"]),
        })

    hardcase_rows = []
    for h in hardcases:
        if not h:
            continue
        hardcase_rows.append({
            "split": "train", "source": "synthetic_hardcase", "weight": 2.0,
            "rule": h.get("rule"), "task_title": h.get("task_title"),
            "decision": "feedback",
            "prompt": h.get("prompt"), "completion": h.get("completion"),
            "symptom_modelled": h.get("symptom_modelled"),
        })

    def dump(name, items):
        with (out / name).open("w") as fh:
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")

    dump("relabelled.jsonl", relabelled_rows)
    dump("hard_cases.jsonl", hardcase_rows)

    base_train = [json.loads(l) for l in (out / "train.jsonl").open()]
    for row in base_train:
        row.setdefault("source", "harvested")
    final = base_train + relabelled_rows + hardcase_rows
    dump("train_final.jsonl", final)

    src = Counter(r["source"] for r in final)
    dec = Counter(r.get("decision") for r in final)
    wsum = round(sum(r.get("weight", 1.0) for r in final), 1)
    L = [
        "# Coach Dataset — Corrective Layer",
        f"\n_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"by `scripts/finalize_coach_corrective.py`._\n",
        "## What the corrective pass added\n",
        f"- **relabelled.jsonl**: {len(relabelled_rows)} GENUINE false-approvals "
        f"(of 16 candidates) — real player_report + corrected `feedback` verdict, weight 2.0",
        f"- **skipped** (heuristic misfired, approve was correct): {len(skipped)} "
        f"— {[s['task_id'] for s in skipped]}",
        f"- **hard_cases.jsonl**: {len(hardcase_rows)} authored symptom→ideal-catch pairs (weight 2.0)\n",
        "## train_final.jsonl\n",
        f"- total rows: **{len(final)}** (weighted ≈ {wsum})",
        f"- by source: {dict(src)}",
        f"- by decision: {dict(dec)}",
        f"  - feedback share now: **{dec.get('feedback',0)/len(final)*100:.0f}%** "
        f"(was ~16% pre-corrective) — the blind-spot signal is up-weighted\n",
        "## Eval (unchanged, never trained)\n",
        "- `holdout_eval.jsonl` (76) + `tierb_holdout.jsonl` (6 Claude trajectories).",
        "- 'Beats base' = higher correct-verdict rate on hold-out + fewer false-approvals "
        "(test specifically on the relabelled + hard-case symptoms) vs base 26B-A4B MoE.\n",
        "## Provenance / honesty\n",
        "- relabelled = REAL input, verdict corrected by an independent judge keyed to the "
        "named failure-mode rule; only cases judged GENUINE were flipped (heuristic misfires kept as approve).",
        "- synthetic_hardcase = authored; tagged `source` so it can be filtered/down-weighted. "
        "Kept small + high-precision, anchored to eval.",
    ]
    (out / "CORRECTIVE.md").write_text("\n".join(L) + "\n")

    print(f"relabelled(genuine)={len(relabelled_rows)} skipped={len(skipped)} "
          f"hardcases={len(hardcase_rows)} train_final={len(final)}")
    print(f"See {out}/CORRECTIVE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
