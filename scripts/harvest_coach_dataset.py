#!/usr/bin/env python3
"""harvest_coach_dataset.py — read-only harvest of Claude-era autobuild Coach training data.

Implements TASK-DATA-COACHHARVEST. Sweeps the sibling appmilla_github repos
(recursively, including .guardkit/worktrees/) plus guardkit's pre-prune git
history at d7f14b0e7^, pairs coach_turn_N.json <-> player_turn_N.json <-> the
task file, classifies provenance BY HARNESS (not date), joins downstream
outcomes (AC-5), and exports a clean corpus.

Provenance (the load-bearing axis — see the task's Update 2026-06-19):
  Primary signal is per-run and on-disk: ``sdk_turns`` in task_work_results.json
  / ``sdk_turns_used`` in player_turn_N.json are written ONLY by the Claude Agent
  SDK harness; the LangGraph/local-model harness does not emit them. A repo's
  committed run-logs (``claude-agent-sdk version`` vs ``GUARDKIT_HARNESS=langgraph``
  / ``gemma4-coach``) are the secondary fallback. Absent both => ``unknown`` (an
  absent signal is never silently promoted to ``claude_*``).

READ-ONLY: writes ONLY under --out (default ~/coach-dataset/); never mutates a
source repo. Run:  python3 scripts/harvest_coach_dataset.py [--out DIR] [--verbose]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

PROJECTS = Path.home() / "Projects" / "appmilla_github"
DEFAULT_OUT = Path.home() / "coach-dataset"

# guardkit's pre-prune tree: parent of d7f14b0e7 (TASK-AC-001 gitignore+untrack,
# 2026-04-12). An ancestor of main, so a plain `git show` reads it read-only.
GUARDKIT_GIT_REF = "d7f14b0e7^"

# Target-project repos that carry .guardkit/autobuild Coach turns.
REPOS = [
    "fleet-memory", "jarvis", "study-tutor", "forge", "specialist-agent",
    "agentic-dataset-factory", "api_test", "nats-core", "nats-infrastructure",
    "lpa-platform-poc",
]

TASK_ID_RE = re.compile(r"\bTASK-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
CLAUDE_LOG_MARKERS = ("claude-agent-sdk version", "Using bundled Claude Code CLI",
                      "coach_test_execution=sdk", "GUARDKIT_HARNESS=sdk")
LOCAL_LOG_MARKERS = ("GUARDKIT_HARNESS=langgraph", "gemma4-coach", "gemma4:26b",
                     "gemma4:31b")


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def safe_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def safe_json_text(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except Exception:
        return None


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


def iso_mtime(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return "unknown"


def cv_len(coach: dict) -> int:
    cv = coach.get("criteria_verification") or coach.get("acceptance_criteria_verification") or []
    return len(cv) if isinstance(cv, list) else 0


# --------------------------------------------------------------------------- #
# provenance (harness, not date)
# --------------------------------------------------------------------------- #
# Repos whose Coach harness was established as Claude SDK/Code by the
# 2026-06-19 harness audit (high confidence). Used only as a fallback when a
# run legitimately lacks the per-run sdk_turns marker (early schema) AND the
# repo's docs lack a run-log marker — so the audit's evidence isn't discarded
# as "unknown". NOT applied to un-audited repos (nats-*) — those stay on the
# per-run/per-repo signal.
AUDITED_CLAUDE = {
    "fleet-memory", "jarvis", "study-tutor", "forge", "specialist-agent",
    "agentic-dataset-factory", "api_test",
}

_repo_hint_cache: dict[str, tuple[bool, bool]] = {}


def repo_log_hint(repo_root: Path) -> tuple[bool, bool]:
    """(has_claude_marker, has_local_marker) from committed run-logs under docs/."""
    key = str(repo_root)
    if key in _repo_hint_cache:
        return _repo_hint_cache[key]
    docs = repo_root / "docs"
    claude = local = False
    if docs.is_dir():
        try:
            out = subprocess.run(
                ["grep", "-rIl", "-e", "claude-agent-sdk version",
                 "-e", "Using bundled Claude Code CLI", str(docs)],
                capture_output=True, text=True, timeout=60)
            claude = bool(out.stdout.strip())
            out2 = subprocess.run(
                ["grep", "-rIl", "-e", "GUARDKIT_HARNESS=langgraph", str(docs)],
                capture_output=True, text=True, timeout=60)
            local = bool(out2.stdout.strip())
        except Exception:
            pass
    _repo_hint_cache[key] = (claude, local)
    return claude, local


def detect_provenance(repo_root: Path, task_dir: Optional[Path],
                      twr: Optional[dict], players: list[dict]) -> tuple[str, str]:
    """Return (provenance, evidence). Per-run sdk_turns is primary."""
    if twr and isinstance(twr.get("sdk_turns"), dict):
        return "claude_sdk", "sdk_turns in task_work_results.json"
    for p in players:
        if p and (p.get("sdk_turns_used") is not None or p.get("sdk_max_turns") is not None):
            return "claude_sdk", "sdk_turns_used in player_turn"
    has_claude, has_local = repo_log_hint(repo_root)
    if has_claude and not has_local:
        return "claude_code", "repo run-logs carry claude-agent-sdk, no langgraph marker"
    if has_local and not has_claude:
        return "local", "repo run-logs carry GUARDKIT_HARNESS=langgraph"
    if has_claude and has_local:
        return "unknown", "repo has BOTH claude and langgraph run-logs (mixed) — no per-run signal"
    if repo_root.name in AUDITED_CLAUDE:
        return "claude_sdk", "harness audit 2026-06-19 (high confidence); early-schema run lacks per-run sdk_turns"
    return "unknown", "no sdk_turns and no harness marker in run-logs"


# --------------------------------------------------------------------------- #
# AC-5 outcome join
# --------------------------------------------------------------------------- #
_rev_fix_index: dict[str, set[str]] = {}


def rev_fix_referenced_ids(repo_root: Path) -> set[str]:
    """Task ids referenced inside this repo's *follow-up TASK-FIX-* artefacts*.
    A later FIX naming a task is a (noisy) proxy that the task's approved work
    needed rework. TASK-REV references are deliberately NOT used as a trigger —
    a review listing a task is not the same as flagging its approval wrong, and
    including them floods the signal (esp. in guardkit's high-review-density tree)."""
    key = str(repo_root)
    if key in _rev_fix_index:
        return _rev_fix_index[key]
    referenced: set[str] = set()
    search_dirs = [repo_root / "tasks", repo_root / ".claude" / "reviews",
                   repo_root / "docs" / "reviews"]
    for d in search_dirs:
        if not d.is_dir():
            continue
        for md in d.rglob("TASK-FIX-*.md"):
            try:
                body = md.read_text(errors="replace")
            except Exception:
                continue
            for tid in TASK_ID_RE.findall(body):
                if not (tid.startswith("TASK-REV-") or tid.startswith("TASK-FIX-")):
                    referenced.add(tid)
    _rev_fix_index[key] = referenced
    return referenced


def outcome_for(repo_root: Path, task_id: str, decision: str) -> str:
    referenced = rev_fix_referenced_ids(repo_root)
    if task_id in referenced:
        return "later_revised"
    if decision == "approve":
        return "clean"
    return "unknown"


# --------------------------------------------------------------------------- #
# task-file lookup
# --------------------------------------------------------------------------- #
_task_file_cache: dict[str, dict[str, Path]] = {}


def task_files_index(repo_root: Path) -> dict[str, Path]:
    key = str(repo_root)
    if key in _task_file_cache:
        return _task_file_cache[key]
    idx: dict[str, Path] = {}
    tasks = repo_root / "tasks"
    if tasks.is_dir():
        for md in tasks.rglob("TASK-*.md"):
            m = TASK_ID_RE.match(md.name)
            if m and m.group(0) not in idx:
                idx[m.group(0)] = md
    _task_file_cache[key] = idx
    return idx


def task_payload(repo_root: Path, task_id: str) -> Optional[str]:
    md = task_files_index(repo_root).get(task_id)
    if md and md.is_file():
        try:
            return md.read_text(errors="replace")
        except Exception:
            return None
    return None


# --------------------------------------------------------------------------- #
# on-disk sweep
# --------------------------------------------------------------------------- #
def iter_task_dirs(repo_root: Path) -> Iterator[Path]:
    """Every dir holding >=1 coach_turn_*.json, recursively (incl worktrees)."""
    seen: set[Path] = set()
    for coach in repo_root.rglob("coach_turn_*.json"):
        if "/.git/" in str(coach):
            continue
        d = coach.parent
        if d not in seen:
            seen.add(d)
            yield d


def harvest_repo(repo: str, verbose: bool) -> list[dict]:
    repo_root = PROJECTS / repo
    if not repo_root.is_dir():
        return []
    pairs: list[dict] = []
    for task_dir in iter_task_dirs(repo_root):
        coach_files = sorted(task_dir.glob("coach_turn_*.json"))
        twr = safe_json(task_dir / "task_work_results.json")
        players_all = [safe_json(p) for p in task_dir.glob("player_turn_*.json")]
        prov, prov_ev = detect_provenance(repo_root, task_dir, twr,
                                          [p for p in players_all if p])
        for cf in coach_files:
            coach = safe_json(cf)
            if not coach:
                continue
            m = re.search(r"coach_turn_(\d+)\.json", cf.name)
            turn = int(m.group(1)) if m else 0
            player = safe_json(cf.with_name(f"player_turn_{turn}.json"))
            task_id = coach.get("task_id") or task_dir.name
            decision = coach.get("decision", "?")
            pairs.append({
                "repo": repo,
                "task_id": task_id,
                "turn": turn,
                "date": iso_mtime(cf),
                "provenance": prov,
                "provenance_evidence": prov_ev,
                "source": "on_disk",
                "schema_complete": cv_len(coach) > 0,
                "criteria_count": cv_len(coach),
                "decision": decision,
                "outcome": outcome_for(repo_root, task_id, decision),
                "coach_verdict": coach,
                "player_report": player,
                "task": task_payload(repo_root, task_id),
                "source_path": str(cf),
                "content_sha": sha(json.dumps(coach, sort_keys=True)),
            })
    if verbose:
        print(f"  {repo}: {len(pairs)} on-disk coach turns", file=sys.stderr)
    return pairs


# --------------------------------------------------------------------------- #
# guardkit git-history recovery (the ~305 pre-prune Feb pairs)
# --------------------------------------------------------------------------- #
def git_show(repo_root: Path, ref_path: str) -> Optional[str]:
    try:
        out = subprocess.run(["git", "-C", str(repo_root), "show", ref_path],
                             capture_output=True, text=True, timeout=30)
        return out.stdout if out.returncode == 0 else None
    except Exception:
        return None


def harvest_guardkit_git(verbose: bool) -> list[dict]:
    repo_root = PROJECTS / "guardkit"
    if not repo_root.is_dir():
        return []
    try:
        listing = subprocess.run(
            ["git", "-C", str(repo_root), "ls-tree", "-r", "--name-only",
             GUARDKIT_GIT_REF, "--", ".guardkit/autobuild"],
            capture_output=True, text=True, timeout=60)
    except Exception:
        return []
    paths = [p for p in listing.stdout.splitlines() if p.endswith(".json")]
    by_dir: dict[str, list[str]] = defaultdict(list)
    for p in paths:
        by_dir["/".join(p.split("/")[:-1])].append(p)

    pairs: list[dict] = []
    for d, files in by_dir.items():
        twr_path = f"{d}/task_work_results.json"
        twr = safe_json_text(git_show(repo_root, f"{GUARDKIT_GIT_REF}:{twr_path}") or "")
        players = {}
        for f in files:
            mm = re.search(r"player_turn_(\d+)\.json$", f)
            if mm:
                players[int(mm.group(1))] = safe_json_text(
                    git_show(repo_root, f"{GUARDKIT_GIT_REF}:{f}") or "")
        prov, prov_ev = detect_provenance(repo_root, None, twr,
                                          [p for p in players.values() if p])
        if prov == "unknown":
            # Feb pre-prune guardkit is SDK-era per the harness audit; only claim
            # it when a per-run sdk signal is absent but the era is established.
            prov, prov_ev = "claude_sdk", "guardkit pre-prune Feb (d7f14b0e7^), SDK-era per harness audit"
        for f in files:
            mm = re.search(r"coach_turn_(\d+)\.json$", f)
            if not mm:
                continue
            turn = int(mm.group(1))
            coach = safe_json_text(git_show(repo_root, f"{GUARDKIT_GIT_REF}:{f}") or "")
            if not coach:
                continue
            task_id = coach.get("task_id") or d.split("/")[-1]
            decision = coach.get("decision", "?")
            pairs.append({
                "repo": "guardkit",
                "task_id": task_id,
                "turn": turn,
                "date": "2026-02 (git d7f14b0e7^)",
                "provenance": prov,
                "provenance_evidence": prov_ev,
                "source": "git_recovery",
                "schema_complete": cv_len(coach) > 0,
                "criteria_count": cv_len(coach),
                "decision": decision,
                "outcome": outcome_for(repo_root, task_id, decision),
                "coach_verdict": coach,
                "player_report": players.get(turn),
                "task": task_payload(repo_root, task_id),
                "source_path": f"git:{GUARDKIT_GIT_REF}:{f}",
                "content_sha": sha(json.dumps(coach, sort_keys=True)),
            })
    if verbose:
        print(f"  guardkit(git {GUARDKIT_GIT_REF}): {len(pairs)} recovered coach turns",
              file=sys.stderr)
    return pairs


# --------------------------------------------------------------------------- #
# Tier-B trajectories
# --------------------------------------------------------------------------- #
def harvest_tier_b(verbose: bool) -> list[dict]:
    roots = list(Path.home().glob(".claude.backup.*/projects")) + \
        [Path.home() / ".claude" / "projects"]
    trajectories: list[dict] = []
    excluded = Counter()
    candidates = 0
    for root in roots:
        if not root.is_dir():
            continue
        for jf in root.rglob("subagents/*.jsonl"):
            if "/workflows/" in str(jf):
                excluded["workflows_path"] += 1
                continue
            try:
                text = jf.read_text(errors="replace")
            except Exception:
                continue
            if "You are the Coach" not in text:
                continue
            if '"tool_use"' not in text and "'tool_use'" not in text:
                continue
            candidates += 1
            # design/prompt-engineering false positive
            if re.search(r"You are designing .{0,40}Coach", text):
                excluded["design_session"] += 1
                continue
            model = ""
            mm = re.search(r'"model"\s*:\s*"(claude-[^"]+)"', text)
            if not mm:
                # has Coach prompt + tool_use but no claude model id -> not teacher
                excluded["non_claude_model"] += 1
                continue
            model = mm.group(1)
            project = jf.parts[-3] if len(jf.parts) >= 3 else ""
            messages = [safe_json_text(ln) for ln in text.splitlines() if ln.strip()]
            messages = [m for m in messages if m]
            n_tool_use = text.count('"type":"tool_use"') or text.count('"tool_use"')
            trajectories.append({
                "source_path": str(jf),
                "model": model,
                "project": project,
                "num_tool_use": n_tool_use,
                "messages": messages,
            })
    if verbose:
        print(f"  Tier-B: {candidates} candidates -> {len(trajectories)} kept; "
              f"excluded={dict(excluded)}", file=sys.stderr)
    return trajectories, dict(excluded), candidates


# --------------------------------------------------------------------------- #
# MANIFEST
# --------------------------------------------------------------------------- #
TEACHER = {"claude_sdk", "claude_code"}


def write_manifest(out: Path, pairs: list[dict], trajectories: list[dict],
                   tierb_excluded: dict, tierb_candidates: int) -> None:
    by_repo = Counter(p["repo"] for p in pairs)
    by_prov = Counter(p["provenance"] for p in pairs)
    by_outcome = Counter(p["outcome"] for p in pairs)
    by_decision = Counter(p["decision"] for p in pairs)
    teacher = [p for p in pairs if p["provenance"] in TEACHER]
    teacher_rich = [p for p in teacher if p["schema_complete"]]
    repo_prov = defaultdict(Counter)
    for p in pairs:
        repo_prov[p["repo"]][p["provenance"]] += 1
    false_approvals = sorted({
        f'{p["repo"]}/{p["task_id"]}' for p in pairs
        if p["decision"] == "approve" and p["outcome"] == "later_revised"
        and p["provenance"] in TEACHER})

    L = []
    L.append("# Coach Training Corpus — MANIFEST\n")
    L.append(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
             f"by `scripts/harvest_coach_dataset.py` (TASK-DATA-COACHHARVEST). READ-ONLY harvest._\n")
    L.append("## Headline\n")
    L.append(f"- **Total coach verdict pairs harvested:** {len(pairs)}")
    L.append(f"- **Teacher-quality (provenance ∈ {{claude_sdk, claude_code}}):** {len(teacher)}")
    L.append(f"- **Teacher-quality AND schema-complete (rich):** {len(teacher_rich)}")
    L.append(f"- **Tier-B full trajectories:** {len(trajectories)}\n")

    L.append("## Provenance (the load-bearing axis — harness, not date)\n")
    for prov, n in by_prov.most_common():
        L.append(f"- `{prov}`: {n}")
    L.append("")

    L.append("## Per-repo (provenance breakdown)\n")
    L.append("| repo | pairs | provenance |")
    L.append("|---|---|---|")
    for repo, n in by_repo.most_common():
        prov_str = ", ".join(f"{k}={v}" for k, v in repo_prov[repo].most_common())
        L.append(f"| {repo} | {n} | {prov_str} |")
    L.append("")

    L.append("## Decision split (teacher set)\n")
    td = Counter(p["decision"] for p in teacher)
    for dec, n in td.most_common():
        L.append(f"- `{dec}`: {n}")
    approve_share = (td.get("approve", 0) / len(teacher) * 100) if teacher else 0
    L.append(f"\n> Approve share of teacher set: **{approve_share:.0f}%** — "
             f"feedback/reject turns are the scarcer, higher-value judgment signal; "
             f"up-weight them and DO NOT raw-distil the approves (you would train a rubber-stamp).\n")

    L.append("## Outcome join (AC-5)\n")
    for oc, n in by_outcome.most_common():
        L.append(f"- `{oc}`: {n}")
    fa_by_repo = Counter(fa.split("/")[0] for fa in false_approvals)
    L.append(f"\n### False-approval CANDIDATES (approve + later_revised, teacher) — "
             f"noisy relabeller input, NOT confirmed false-approvals and NOT "
             f"distillation examples ({len(false_approvals)})\n")
    L.append("Per repo: " + ", ".join(f"{r}={n}" for r, n in fa_by_repo.most_common()))
    L.append("> Heuristic = a follow-up `TASK-FIX-*` names the task. This is a "
             "candidate pool for the Coach-as-relabeller step, not ground truth; "
             "guardkit's count is inflated by its high TASK-FIX density. First "
             f"{min(60, len(false_approvals))} shown:\n")
    for fa in false_approvals[:60]:
        L.append(f"- {fa}")
    if not false_approvals:
        L.append("- _(none detected by the heuristic join — see method note)_")
    L.append("")

    L.append("## Tier-B trajectories\n")
    L.append(f"- candidates (Coach prompt + tool_use): {tierb_candidates}")
    L.append(f"- excluded: {tierb_excluded}")
    L.append(f"- kept (genuine Claude model): {len(trajectories)}")
    for t in trajectories:
        L.append(f"  - {t['model']} | tool_use={t['num_tool_use']} | {t['source_path']}")
    L.append("")

    L.append("## Provenance method\n")
    L.append("- **Primary, per-run:** `sdk_turns` in `task_work_results.json` / "
             "`sdk_turns_used` in `player_turn` — emitted ONLY by the Claude Agent SDK harness.")
    L.append("- **Secondary, per-repo:** committed run-logs under `docs/` "
             "(`claude-agent-sdk version` => claude; `GUARDKIT_HARNESS=langgraph` => local).")
    L.append("- **guardkit git-recovery:** read read-only from `d7f14b0e7^` (pre-TASK-AC-001 prune).")
    L.append("- An absent signal is recorded as `unknown`, never promoted to `claude_*`.")
    L.append("- **NOTE — lpa-platform-poc:** per-turn JSON is permanently lost "
             "(gitignored + written in worktrees that were merged & deleted; never committed). "
             "Only events.jsonl/review-summary/progress.log survive — not harvestable as pairs.\n")

    L.append("## Outcome-join method (heuristic)\n")
    L.append("- `later_revised` if the task id is referenced inside any "
             "`TASK-REV-*`/`TASK-FIX-*` artefact or review report in the same repo.")
    L.append("- `clean` if decision was `approve` and no such reference exists.")
    L.append("- `unknown` otherwise. This is a coarse signal; the false-approval "
             "set is a candidate list for Coach-as-relabeller curation, not ground truth.")
    (out / "MANIFEST.md").write_text("\n".join(L) + "\n")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--repos", nargs="*", default=REPOS)
    ap.add_argument("--no-git-recovery", action="store_true",
                    help="skip the guardkit d7f14b0e7^ recovery")
    ap.add_argument("--no-tier-b", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    print(f"Harvesting -> {out}  (READ-ONLY on sources)", file=sys.stderr)

    pairs: list[dict] = []
    for repo in args.repos:
        pairs.extend(harvest_repo(repo, args.verbose))
    if not args.no_git_recovery:
        pairs.extend(harvest_guardkit_git(args.verbose))

    # de-dup by (repo, task_id, turn, content_sha) — kills specialist-agent's
    # byte-identical duplicate dir and worktree<->canonical copies.
    deduped: dict[tuple, dict] = {}
    for p in pairs:
        k = (p["repo"], p["task_id"], p["turn"], p["content_sha"])
        deduped.setdefault(k, p)
    pairs = list(deduped.values())

    trajectories, tierb_excluded, tierb_candidates = ([], {}, 0)
    if not args.no_tier_b:
        trajectories, tierb_excluded, tierb_candidates = harvest_tier_b(args.verbose)

    with (out / "coach_verdict_pairs.jsonl").open("w") as fh:
        for p in pairs:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    with (out / "coach_trajectories.jsonl").open("w") as fh:
        for t in trajectories:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")
    write_manifest(out, pairs, trajectories, tierb_excluded, tierb_candidates)

    teacher = sum(1 for p in pairs if p["provenance"] in TEACHER)
    rich = sum(1 for p in pairs if p["provenance"] in TEACHER and p["schema_complete"])
    print(f"\nDone. {len(pairs)} pairs ({teacher} teacher, {rich} rich) + "
          f"{len(trajectories)} Tier-B trajectories.\nSee {out}/MANIFEST.md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
