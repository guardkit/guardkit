#!/usr/bin/env python3
"""curate_coach_dataset.py — turn the raw harvest into LoRA-ready splits.

Reads ~/coach-dataset/coach_verdict_pairs.jsonl (from harvest_coach_dataset.py)
and produces, under ~/coach-dataset/curated/:

  train.jsonl            SFT set (rich teacher pairs, rendered prompt/completion,
                         per-row `weight`: feedback up-weighted, false-approvals
                         EXCLUDED so we never distil a rubber-stamp).
  holdout_eval.jsonl     ~15% stratified hold-out (never trained on).
  tierb_holdout.jsonl    all 6 Tier-B trajectories — eval / few-shot only.
  relabel_worklist.jsonl false-approval candidates: real player_report kept,
                         original (wrong) verdict + suggested failure-mode rules,
                         `corrected_verdict: null` for the Coach-as-relabeller step.
  hard_case_seeds.jsonl  one authoring skeleton per .claude/rules failure mode
                         (the symptom excerpt + an ideal-verdict template).
  CURATION.md            counts, weight scheme, method.

Addresses the corpus's two weaknesses (72% approve-skew + the old Coach's blind
spots) per the task's AC-5 / fine-tune guardrails. READ-ONLY on sources; writes
only under --out.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CORPUS = Path.home() / "coach-dataset"
RULES_DIR = Path.home() / "Projects" / "appmilla_github" / "guardkit" / ".claude" / "rules"
TEACHER = {"claude_sdk", "claude_code"}
HOLDOUT_PCT = 15  # deterministic, by content hash

# Failure-mode rules -> keyword cues that suggest a blind-spot approval belongs
# to that rule. Used ONLY to annotate the relabel worklist (suggestions, noisy
# by design — the relabeller decides).
RULES: list[dict] = [
    {"file": "absence-of-failure-is-not-success.md",
     "title": "Absence of failure is not success",
     "kw": ['tests_run": 0', "0 tests", "no tests ran", "zero attempts",
            "scenarios_run", "0 scenarios", "no oracle", "tests=0", "did not run"]},
    {"file": "per-task-green-is-not-feature-green.md",
     "title": "Per-task-green is not feature-green (mocked seam / ctor arity)",
     "kw": ["mock", "mocked", "asyncmock", "magicmock", "create_autospec", "spec=",
            "patch(", "composition root", "wiring", "arity", "constructor", "main.py"]},
    {"file": "path-string-mismatch-is-not-dishonesty.md",
     "title": "Path-string mismatch is not dishonesty",
     "kw": ["does not exist", "file_existence", "ghost path", "was moved",
            "rename", "shutil.move"]},
    {"file": "evidence-boundary-narrower-than-write-surface.md",
     "title": "Evidence boundary narrower than write surface",
     "kw": ["sibling repo", "evidence_repos", "0 files modified",
            "no implementation provided", "guardkitfactory", "symlink"]},
    {"file": "smoke-gate-is-feedback-not-terminator.md",
     "title": "Smoke gate is feedback, not terminator / runtime parity",
     "kw": ["smoke", "standalone", "modulenotfounderror", "runtime parity",
            "import error", "sys.path", "python <module>"]},
    {"file": "namespace-hygiene.md",
     "title": "Namespace hygiene (sys.path shadowing)",
     "kw": ["sys.path.insert", "shadow", "pypi", "importerror", "not available",
            "sdk not available"]},
    {"file": "harness-cancellation-contract.md",
     "title": "Harness cancellation contract",
     "kw": ["cancel", "timeout", "langgraph", "sigterm", "late approval"]},
    {"file": "stack-plugin-architecture.md",
     "title": "Stack-agnostic by default; plugin only for execution",
     "kw": ["ast.parse", "stack-agnostic", "tree-sitter", "python-only",
            "stack-blind", "stack assumption"]},
]


# --------------------------------------------------------------------------- #
def hash_bucket(content_sha: str) -> int:
    try:
        return int(content_sha[:8], 16) % 100
    except Exception:
        return 0


def truncate(s, n: int) -> str:
    s = "" if s is None else str(s)
    return s if len(s) <= n else s[:n] + " …[truncated]"


def extract_title(task_md: Optional[str], fallback: str) -> str:
    if not task_md:
        return fallback
    m = re.search(r"^#\s*(?:Task:\s*)?(.+)$", task_md, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"^title:\s*(.+)$", task_md, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def extract_acceptance(task_md: Optional[str]) -> str:
    if not task_md:
        return "(no task file recovered)"
    m = re.search(r"##\s*Acceptance[^\n]*\n(.+?)(?:\n##\s|\Z)", task_md,
                  re.DOTALL | re.IGNORECASE)
    if m:
        return truncate(m.group(1).strip(), 2500)
    crit = re.findall(r"^\s*-\s*\[[ x]\]\s*(.+)$", task_md, re.MULTILINE)
    if crit:
        return "\n".join(f"- {c}" for c in crit[:30])
    return truncate(task_md, 1500)


def render_prompt(pair: dict) -> str:
    task_md = pair.get("task")
    title = extract_title(task_md, pair["task_id"])
    acs = extract_acceptance(task_md)
    pr = pair.get("player_report") or {}
    lines = [
        "You are the Coach in an adversarial Player-Coach build loop. Verify the "
        "Player's work against EACH acceptance criterion and return a verdict: "
        "`approve` only when every criterion is genuinely met with real (not mocked, "
        "not absent, not zero-cardinality) evidence; otherwise `feedback` naming the "
        "specific gap.",
        f"\n## Task: {title}\n{acs}",
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


def render_completion(pair: dict) -> str:
    cv = pair["coach_verdict"]
    out = {
        "decision": cv.get("decision"),
        "criteria_verification": cv.get("criteria_verification")
        or cv.get("acceptance_criteria_verification") or [],
        "issues": cv.get("issues") or [],
        "rationale": cv.get("rationale"),
    }
    return "```json\n" + json.dumps(out, ensure_ascii=False, indent=2) + "\n```"


def has_issues(pair: dict) -> bool:
    return bool(pair["coach_verdict"].get("issues"))


def weight_for(pair: dict) -> float:
    if pair["decision"] == "feedback":
        return 2.0           # scarce, high-value judgment signal
    if has_issues(pair):
        return 1.5           # approve that still flagged concerns
    return 1.0               # plain clean approve


def suggest_rules(pair: dict) -> list[dict]:
    cv = pair["coach_verdict"]
    text = " ".join([
        str(cv.get("rationale") or ""),
        json.dumps(cv.get("issues") or []),
        extract_acceptance(pair.get("task")),
        str((pair.get("player_report") or {}).get("implementation_notes") or ""),
    ]).lower()
    scored = []
    for r in RULES:
        hits = sum(1 for kw in r["kw"] if kw in text)
        if hits:
            scored.append({"rule": r["file"], "title": r["title"], "hits": hits})
    return sorted(scored, key=lambda x: -x["hits"])[:3]


def rule_symptom_seed(rule: dict) -> dict:
    path = RULES_DIR / rule["file"]
    symptom = "(symptom section not found)"
    if path.is_file():
        body = path.read_text(errors="replace")
        m = re.search(r"##\s*Symptom\s*\n(.+?)(?:\n##\s)", body, re.DOTALL)
        if not m:
            m = re.search(r"##\s*The rule\s*\n(.+?)(?:\n##\s)", body, re.DOTALL)
        if m:
            symptom = truncate(m.group(1).strip(), 900)
    return {
        "rule": rule["file"],
        "title": rule["title"],
        "symptom_excerpt": symptom,
        "ideal_decision": "feedback",
        "authoring_template": {
            "prompt": "You are the Coach ... ## Task: <task that triggers this failure mode> "
                      "## Player report: <a report exhibiting the symptom above>",
            "completion": "```json\n{\"decision\": \"feedback\", "
                          "\"criteria_verification\": [<per-AC, the unmet one flagged>], "
                          "\"issues\": [\"<the specific catch this rule prescribes>\"], "
                          "\"rationale\": \"<why this is NOT approvable — cite the rule>\"}\n```",
        },
    }


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--include-thin", action="store_true",
                    help="include non-schema-complete teacher pairs in train (default: rich only)")
    args = ap.parse_args()

    corpus = args.corpus.expanduser()
    out = (args.out or (corpus / "curated")).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(l) for l in (corpus / "coach_verdict_pairs.jsonl").open()]
    trajectories = []
    tb = corpus / "coach_trajectories.jsonl"
    if tb.exists():
        trajectories = [json.loads(l) for l in tb.open()]

    train, holdout, relabel = [], [], []
    excluded = Counter()

    for p in rows:
        if p["provenance"] not in TEACHER:
            excluded["non_teacher"] += 1
            continue
        # false-approval candidates -> relabel worklist, never train
        if p["decision"] == "approve" and p["outcome"] == "later_revised":
            relabel.append({
                "repo": p["repo"], "task_id": p["task_id"], "turn": p["turn"],
                "original_decision": p["decision"],
                "original_verdict": p["coach_verdict"],
                "player_report": p["player_report"],
                "task_excerpt": extract_acceptance(p.get("task")),
                "suggested_rules": suggest_rules(p),
                "corrected_verdict": None,
                "note": "real input, wrong label — relabel the verdict (likely feedback) "
                        "per the suggested rule(s); reserve as hard negative, not raw approve.",
            })
            continue
        if not args.include_thin and not p["schema_complete"]:
            excluded["thin_excluded"] += 1
            continue

        row = {
            "repo": p["repo"], "task_id": p["task_id"], "turn": p["turn"],
            "provenance": p["provenance"], "decision": p["decision"],
            "has_issues": has_issues(p), "weight": weight_for(p),
            "prompt": render_prompt(p), "completion": render_completion(p),
        }
        if hash_bucket(p["content_sha"]) < HOLDOUT_PCT:
            row["split"] = "holdout"
            holdout.append(row)
        else:
            row["split"] = "train"
            train.append(row)

    seeds = [rule_symptom_seed(r) for r in RULES]

    def dump(name, items):
        with (out / name).open("w") as fh:
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")

    dump("train.jsonl", train)
    dump("holdout_eval.jsonl", holdout)
    dump("tierb_holdout.jsonl", trajectories)
    dump("relabel_worklist.jsonl", relabel)
    dump("hard_case_seeds.jsonl", seeds)

    # ---- CURATION.md ----
    def wsum(items):
        return round(sum(i["weight"] for i in items), 1)
    tr_dec = Counter(i["decision"] for i in train)
    L = [
        "# Coach Dataset — Curation",
        f"\n_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"by `scripts/curate_coach_dataset.py`. Input: {corpus}/coach_verdict_pairs.jsonl._\n",
        "## Splits\n",
        f"- **train.jsonl**: {len(train)} pairs (rich teacher, false-approvals excluded) — "
        f"effective weighted size ≈ {wsum(train)}",
        f"    - by decision: {dict(tr_dec)}  (feedback ×2.0, approve+issues ×1.5, plain approve ×1.0)",
        f"- **holdout_eval.jsonl**: {len(holdout)} pairs (~{HOLDOUT_PCT}% deterministic by content hash — never trained)",
        f"- **tierb_holdout.jsonl**: {len(trajectories)} full Claude trajectories (eval / few-shot only)",
        f"- **relabel_worklist.jsonl**: {len(relabel)} false-approval candidates "
        f"(real input + wrong label → corrected_verdict:null for the relabeller)",
        f"- **hard_case_seeds.jsonl**: {len(seeds)} authoring skeletons, one per failure-mode rule",
        f"- excluded: {dict(excluded)}\n",
        "## How to use\n",
        "1. **Relabel** `relabel_worklist.jsonl`: for each, write `corrected_verdict` "
        "(usually `feedback` citing the suggested rule). Use Claude or the named rule/retro "
        "as the oracle. Fold the corrected pairs back into train at weight ≈ 2.0 as hard negatives.",
        "2. **Author** a few pairs per `hard_case_seeds.jsonl` skeleton (symptom → ideal catch). "
        "Keep this set SMALL + high-precision; use mostly for eval anchoring + up-weighting, "
        "not bulk (templated phrasing overfits).",
        "3. **Format** `prompt`/`completion` are already rendered toward the COACHSPLIT "
        "toolless+grammar contract; adjust the system preamble / fence to your serving format.",
        "4. **Train** the LoRA on `train.jsonl` (honour `weight`); **eval** on "
        "`holdout_eval.jsonl` + `tierb_holdout.jsonl`. 'Beats base' = higher correct-verdict "
        "rate on hold-out + fewer false-approvals + tighter reasoning, vs the base 26B-A4B MoE.\n",
        "## Guardrails honoured\n",
        "- Approve-skew countered by weighting + false-approval exclusion (no rubber-stamp).",
        "- False-approvals are RELABELLED (real input, corrected verdict), never distilled as approve.",
        "- Tier-B + a 15% hold-out are reserved for eval, never trained.",
        "- Provenance gate: only `claude_sdk`/`claude_code` pairs are used.",
    ]
    (out / "CURATION.md").write_text("\n".join(L) + "\n")

    print(f"train={len(train)} holdout={len(holdout)} relabel={len(relabel)} "
          f"tierb={len(trajectories)} seeds={len(seeds)}\nSee {out}/CURATION.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
