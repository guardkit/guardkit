"""One independent review of the whole finished feature (12 November 2026).

Rich, 12 November 2026, on the head-to-head test of 9 November (docs/designs/
per-task-review-head-to-head-2026-11-09.md in ai-transition): "yes agreed please proceed". Feature
builds no longer have a model review each task. Each task's own tests and declared checks still run
and still send a turn back when they fail. When every task has completed, this review looks at the
finished feature once: it starts fresh, is given the whole request, the plan and the whole change,
and a throwaway copy of the code it may build and run with stub endpoints, and reports only concrete
faults, each with a file, a line and how to trigger it. The builder gets up to two repair rounds
through the same re-entry the failed-task retry uses (``FeatureOrchestrator._execute_wave`` with
``seed_feedback``). Then the whole-feature check runs on the repaired code, and the build finishes
as before. The review itself never fails a build: an error is recorded and the build goes on.

This is the code that was measured in the head-to-head (its arm 2), with its switches replaced:

- **The way back.** ``GUARDKIT_PER_TASK_REVIEW=1`` (or ``true``, ``yes``, ``on``) brings the
  per-task reviewer back and turns this review off.
- **The request** is found in the build's own history: the commit ``planning: feature plan
  <feature id> for <correlation id>`` names it, and the request is
  ``feature_spec_inputs/<correlation id>.md`` at HEAD. Without one, the feature file's name and
  description and its ``.feature`` files are used instead. The record says which.
- **The record** is kept in ``.guardkit/autobuild/<feature id>/end_review/`` under the repository
  the build runs from: ``end_review.json`` (written after every step, so a resumed build carries
  on from it with the same two-round budget), ``pre_commit.txt`` (the commit before the review),
  ``review-N-answer.txt`` and ``repair-N-feedback.txt``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

#: The way back: set to one of :data:`_SWITCH_ON`, the per-task reviewer runs and this review does not.
PER_TASK_REVIEW_ENV = "GUARDKIT_PER_TASK_REVIEW"
_SWITCH_ON = frozenset({"1", "true", "yes", "on"})

#: The builder gets at most this many repair rounds, each after one review.
REPAIR_ROUNDS = 2
#: Attempts offset for the repair re-entries, past the failed-task retry's numbering.
REPAIR_ATTEMPT = 200
#: A review's tool work may take this long; its written answer gets a grace on top.
DEFAULT_REVIEW_SECONDS = 3600
ANSWER_GRACE_SECONDS = 300
#: The review may read, write scratch files and run commands, in its throwaway copy only.
REVIEW_TOOLS = ("Read", "Write", "Edit", "Bash", "Grep", "Glob")

#: Where the request is, when Forge planned the feature.
REQUEST_FOLDER = "feature_spec_inputs"

_FAULT_LINE = re.compile(r"^\W*FAULT\s+(\S+?):(\d+)\s*::\s*(.+?)\s*::\s*(.+?)\s*$", re.IGNORECASE)


def per_task_review_on(env: Optional[Dict[str, str]] = None) -> bool:
    """Has the per-task reviewer been brought back? Absent or unrecognised is no."""
    source = os.environ if env is None else env
    return str(source.get(PER_TASK_REVIEW_ENV, "")).strip().lower() in _SWITCH_ON


def enabled(env: Optional[Dict[str, str]] = None) -> bool:
    """Does a feature build run the end review? Yes, unless the per-task reviewer is back."""
    return not per_task_review_on(env)


def record_dir(repo_root: Path, feature_id: str) -> Path:
    """The feature's end review record folder."""
    return Path(repo_root) / ".guardkit" / "autobuild" / feature_id / "end_review"


def parse_faults(answer: Optional[str]) -> List[Dict[str, Any]]:
    """The answer's concrete faults: file, line, what, how to trigger. Others are dropped."""
    seen: set = set()
    faults: List[Dict[str, Any]] = []
    for raw in (answer or "").splitlines():
        match = _FAULT_LINE.match(raw.strip())
        if not match:
            continue
        key = (match.group(1), match.group(2), match.group(3).lower())
        if key in seen:
            continue
        seen.add(key)
        faults.append({"file": match.group(1), "line": int(match.group(2)), "what": match.group(3), "trigger": match.group(4)})
    return faults


def repair_feedback(faults: List[Dict[str, Any]]) -> str:
    """The builder's instructions for a repair round: every fault, as the review wrote it."""
    lines = [
        "The finished feature was reviewed as a whole, and the review found these faults by reading "
        "and running it. Fix every one of them. Each entry gives the place and how to trigger the "
        "fault; make it stop happening and keep everything else working, then run the project's check.",
        "",
    ]
    lines.extend(f"- {f['file']}:{f['line']}: {f['what']} (how to trigger it: {f['trigger']})" for f in faults)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The request
# ---------------------------------------------------------------------------


def _git(worktree: Path, *args: str) -> Optional[str]:
    """``git`` in ``worktree``, through ``project_git``; its output, or ``None`` when it failed."""
    from guardkit.lib.project_git import run_git

    try:
        done = run_git(["-C", str(worktree), *args])
    except (OSError, ValueError):
        return None
    return done.stdout if done.returncode == 0 else None


def _request_from_history(worktree: Path, feature_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """The request Forge's planning committed for this feature, or ``None``."""
    log = _git(worktree, "log", "--format=%H%x00%s", "HEAD")
    if not log:
        return None
    subject = re.compile(rf"^planning: feature plan {re.escape(feature_id)} for ([^\s()]+)")
    for line in log.splitlines():
        commit, _, title = line.partition("\x00")
        match = subject.match(title)
        if not match:
            continue
        correlation_id = match.group(1)
        path = f"{REQUEST_FOLDER}/{correlation_id}.md"
        text = _git(worktree, "show", f"HEAD:{path}")
        if text and text.strip():
            return text, {"source": "planning commit", "commit": commit, "correlation_id": correlation_id,
                          "path": path}
        # The newest planning commit names the request; an older one is an earlier plan.
        logger.info("The planning commit %s names %s, which is not in the code at HEAD.", commit[:12], path)
        return None
    return None


def _request_from_feature(feature: Any, worktree: Path) -> Tuple[str, Dict[str, Any]]:
    """The feature file's name and description and its ``.feature`` files, as the request."""
    name = str(getattr(feature, "name", "") or "").strip()
    description = str(getattr(feature, "description", "") or "").strip()
    parts = [f"# {name or getattr(feature, 'id', '')}", ""]
    if description:
        parts += [description, ""]
    read: List[str] = []
    missing: List[str] = []
    for spec in getattr(feature, "feature_files", None) or []:
        try:
            text = (Path(worktree) / str(spec)).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            missing.append(str(spec))
            continue
        read.append(str(spec))
        parts += [f"## The feature's specification ({spec})", "", text.strip(), ""]
    source: Dict[str, Any] = {"source": "feature file", "feature_files": read}
    if missing:
        source["feature_files_missing"] = missing
    return "\n".join(parts).strip() + "\n", source


def find_request(feature: Any, worktree: Path) -> Tuple[str, Dict[str, Any]]:
    """The whole request and where it came from. Never raises."""
    try:
        found = _request_from_history(Path(worktree), str(getattr(feature, "id", "")))
    except Exception as exc:  # noqa: BLE001 - the fallback still gives a request
        logger.warning("The request could not be looked up in the build's history: %s", exc)
        found = None
    if found is not None:
        return found
    return _request_from_feature(feature, Path(worktree))


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------


def _plan_section(feature: Any) -> str:
    lines = ["## The plan", "",
             "The plan documents are in this checkout under `.guardkit/features/` and the task files listed below. Read them.", ""]
    guide = getattr(feature, "file_path", None)
    if guide:
        lines.append(f"Feature file: {guide}")
    for task in getattr(feature, "tasks", None) or []:
        lines.append(f"- {task.id}: {task.name} ({getattr(task, 'file_path', '')})")
    return "\n".join(lines)


def build_prompt(feature: Any, request: str, change_section: str, round_number: int) -> str:
    """The end review's prompt. It says everything the review needs; it is not the last look."""
    again = (
        "\nAn earlier review found faults and the builder has made repairs since. Check the repairs "
        "as well, and report whatever is still wrong in the finished code as it is now.\n"
        if round_number > 1
        else ""
    )
    return f"""You are the independent reviewer of one finished software feature, built by another agent. \
You did not build it and you start fresh. Your job is to find out whether the feature really does what \
was asked. You have a shell and full file access in a throwaway copy of the finished code at the current \
folder; nothing you change here is kept, and nobody reads your scratch work.
{again}
## The whole request

{request.strip()}

{_plan_section(feature)}

{change_section}

## What to do

Build the feature in this copy and run it. Use the project's own commands: `.guardkit/config.yaml` \
declares its check (`toolchain.test`, `toolchain.parts`, and any `install`). Run the feature's main \
behaviour for real, through its actual entry point or client, not only through its tests. Where the \
feature needs a model or another service, start a small stub endpoint on 127.0.0.1 yourself, or use a \
closed local port for a failing dependency; never call a real model, a hosted endpoint or any address \
outside this machine, except to install the project's declared dependencies. Write your stubs and \
scratch scripts outside the code, for example under `/tmp`.

Ask three questions, in this order, and answer each by running things where you can:

1. For each thing the request says should happen, does it really happen on the real path?
2. What happens when an input is bad or a dependency fails (a closed port, a name that does not \
resolve, a timeout, an error status)? Compare what happens with what the request says should happen.
3. Does anything fall between the tasks, such as a part another part needs that nothing actually wires up?

## What to report

Only concrete faults: things that are actually wrong in the code as it is now, that you saw happen, or \
that you found by following the code to a specific line. Do not report style, naming, missing tests by \
themselves, wording, or anything the request does not ask for.

Your final answer is plain text: either the single line `NO FAULTS`, or one line per fault in exactly \
this form, with the path relative to the checkout:

FAULT path/to/file.ext:LINE :: what goes wrong :: how to trigger it

Name the line where the fault is. A fault with no file and line, or no way to trigger it, is not a \
finding: do not write it. Do not write any other lines after the list.
"""


# ---------------------------------------------------------------------------
# One review, and the rounds
# ---------------------------------------------------------------------------


def _head(worktree: Path) -> str:
    from guardkit.lib.project_git import run_git

    return run_git(["-C", str(worktree), "rev-parse", "HEAD"], check=True).stdout.strip()


def _copy_of(worktree: Path, copy: Path) -> Path:
    """A separate repository at ``copy/code`` holding the worktree's last commit and its history.

    Through ``project_git``, which refuses ``git clone``: the history goes over as a bundle file,
    is unpacked into a new repository, and the copy is checked out at the same commit on a
    branch of the same name. Nothing in it is linked to the build's repository.
    """
    from guardkit.lib.project_git import run_git

    head = _head(worktree)
    branch = run_git(["-C", str(worktree), "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if not branch or branch == "HEAD":
        branch = "end-review"
    bundle, code = copy / "history.bundle", copy / "code"
    run_git(["-C", str(worktree), "bundle", "create", str(bundle), "HEAD"], check=True)
    run_git(["init", "-q", f"--initial-branch={branch}", str(code)], cwd=copy, check=True)
    run_git(["-C", str(code), "bundle", "unbundle", str(bundle)], check=True)
    run_git(["-C", str(code), "reset", "-q", "--hard", head], check=True)
    bundle.unlink(missing_ok=True)
    return code


def _review_once(orchestrator: Any, feature: Any, worktree: Any, base: Optional[str], request: str,
                 round_number: int, seconds: int) -> Dict[str, Any]:
    """One end review in a throwaway copy of the worktree's last commit."""
    from guardkit.orchestrator import build_review
    from guardkit.orchestrator.agent_invoker import AgentInvoker
    from guardkit.orchestrator.feature_orchestrator import DEFAULT_SDK_TIMEOUT

    started = time.time()
    copy = Path(tempfile.mkdtemp(prefix="guardkit-end-review-"))
    try:
        code = _copy_of(Path(worktree.path), copy)
        change = build_review.write_change(feature.id, round_number, code, base)
        section = build_review._change_section(change, "feature")
        prompt = build_prompt(feature, request, section, round_number)
        invoker = AgentInvoker(
            worktree_path=code,
            sdk_timeout_seconds=orchestrator.sdk_timeout or DEFAULT_SDK_TIMEOUT,
            sdk_timeout_is_override=orchestrator.sdk_timeout is not None,
            timeout_multiplier=orchestrator.timeout_multiplier,
            model_name=orchestrator.model,
            coach_model_name=orchestrator.coach_model,
            emitter=orchestrator._emitter,
        )
        answer = asyncio.run(asyncio.wait_for(
            invoker.invoke_end_review(feature.id, round_number, prompt, seconds, ANSWER_GRACE_SECONDS),
            seconds + ANSWER_GRACE_SECONDS + 120,
        ))
        return {"answer": answer, "seconds": round(time.time() - started, 1), "prompt_chars": len(prompt)}
    finally:
        shutil.rmtree(copy, ignore_errors=True)


def _save(out: Path, record: Dict[str, Any]) -> None:
    (out / "end_review.json").write_text(json.dumps(record, indent=1, default=str) + "\n", encoding="utf-8")


def _earlier_record(out: Path, orchestrator: Any, feature_id: str, worktree_path: Path) -> Optional[Dict[str, Any]]:
    """This build's record from before it was resumed, or ``None`` when there is none to carry on.

    Carried on only when the build was resumed (``--resume``, or a yes to the resume question), the
    record is this feature's, and the code it last saw is still in the worktree's history. A fresh
    build, or a new worktree, starts a new record.
    """
    if not getattr(orchestrator, "resume", False) or getattr(orchestrator, "fresh", False):
        return None
    try:
        record = json.loads((out / "end_review.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or record.get("feature") != feature_id or not isinstance(record.get("rounds"), list):
        return None
    last_seen = record.get("last_commit") or record.get("pre_commit")
    if not last_seen or _git(worktree_path, "merge-base", "--is-ancestor", str(last_seen), "HEAD") is None:
        return None
    return record


def run_end_review(orchestrator: Any, feature: Any, worktree: Any, wave_results: List[Any]) -> None:
    """The end review and its repair rounds, between the wave phase and the whole-feature check.

    Never raises. Its record is written after every step.
    """
    out: Optional[Path] = None
    record: Dict[str, Any] = {"feature": getattr(feature, "id", None), "rounds": []}
    try:
        out = record_dir(Path(orchestrator.repo_root), feature.id)
        out.mkdir(parents=True, exist_ok=True)
        worktree_path = Path(worktree.path)
        earlier = _earlier_record(out, orchestrator, feature.id, worktree_path)
        if earlier is not None:
            record = earlier
            record["resumed"] = int(record.get("resumed") or 0) + 1
        else:
            for stale in list(out.glob("review-*-answer.txt")) + list(out.glob("repair-*-feedback.txt")):
                stale.unlink(missing_ok=True)
        _run(orchestrator, feature, worktree, wave_results, out, record)
    except Exception as exc:  # noqa: BLE001 - recorded; the build goes on
        logger.exception("The end review stopped: %s", exc)
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["status"] = "stopped by an error"
    finally:
        try:
            if out is not None:
                _save(out, record)
        except Exception as exc:  # noqa: BLE001 - a record never fails a build
            logger.warning("The end review record could not be written: %s", exc)


def _run(orchestrator: Any, feature: Any, worktree: Any, wave_results: List[Any], out: Path,
         record: Dict[str, Any]) -> None:
    from guardkit.orchestrator.seam_checks import resolve_feature_base

    worktree_path = Path(worktree.path)
    if record.get("status") == "finished":
        logger.info("The end review of %s already finished before this build was resumed.", feature.id)
        return
    if not record.get("pre_commit"):
        pre_commit = _head(worktree_path)
        (out / "pre_commit.txt").write_text(pre_commit + "\n", encoding="utf-8")
        record["pre_commit"] = pre_commit
    tasks = getattr(feature, "tasks", None) or []
    if not tasks or any(task.status != "completed" for task in tasks):
        record["status"] = "skipped: not every task completed, so there is no finished feature to review"
        logger.info("The end review is skipped: %s", record["status"])
        return
    groups = feature.orchestration.parallel_groups
    wave, repair_task = len(groups), groups[-1][-1]
    base = resolve_feature_base(worktree_path, feature.id)
    if "request" not in record:
        request, source = find_request(feature, worktree_path)
        record["request"] = source
        record["request_text"] = request
    request = record["request_text"]
    record["status"] = "running"
    record["last_commit"] = _head(worktree_path)
    _save(out, record)

    rounds: List[Dict[str, Any]] = record["rounds"]
    round_number = len(rounds) if rounds and "repair" not in rounds[-1] and not rounds[-1].get("error") else len(rounds) + 1
    while round_number <= REPAIR_ROUNDS:
        if round_number > len(rounds):
            rounds.append({"round": round_number})
        entry = rounds[round_number - 1]
        if not entry.get("reviewed"):
            logger.info("End review %s of feature %s", round_number, feature.id)
            try:
                reviewed = _review_once(orchestrator, feature, worktree, base, request, round_number,
                                        DEFAULT_REVIEW_SECONDS)
            except Exception as exc:  # noqa: BLE001 - a failed review repairs nothing
                logger.warning("End review %s failed: %s", round_number, exc)
                entry["error"] = f"{type(exc).__name__}: {exc}"
                break
            answer = reviewed.pop("answer")
            (out / f"review-{round_number}-answer.txt").write_text(str(answer or ""), encoding="utf-8")
            entry.update(reviewed)
            entry["faults"] = parse_faults(answer)
            entry["answered"] = bool(answer)
            entry["reviewed"] = True
            _save(out, record)
        faults = entry.get("faults") or []
        if not faults:
            break
        feedback = repair_feedback(faults)
        (out / f"repair-{round_number}-feedback.txt").write_text(feedback, encoding="utf-8")
        logger.info("End review %s found %s fault(s); repair round %s on %s", round_number, len(faults), round_number, repair_task)
        started = time.time()
        # Through the failed-task re-entry, not the "re-open" one: that is the whole-feature-check repair, whose guard
        # refuses any file the task document does not name, and each refused turn is another builder turn.
        next(task for task in tasks if task.id == repair_task).status = "failed"
        wave_result = orchestrator._execute_wave(wave, [repair_task], feature, worktree, seed_feedback=feedback,
                                                  attempt=REPAIR_ATTEMPT + round_number)
        wave_results.append(wave_result)
        entry["repair"] = {
            "task": repair_task, "seconds": round(time.time() - started, 1),
            "succeeded": bool(wave_result.all_succeeded),
            "after_commit": _head(worktree_path),
        }
        record["last_commit"] = entry["repair"]["after_commit"]
        _save(out, record)
        round_number += 1
    record["status"] = "finished"
