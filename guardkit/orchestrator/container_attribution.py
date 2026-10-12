"""Who removed a container? Only an actor-bound teardown receipt can say.

Repair 7 (12 October 2026) keeps raw container events beside every declared
command GuardKit runs, and deliberately attributes none of them: daemon events
do not name their cause, and the factory itself removes containers outside any
declared command (Forge's fixture cleanup when a build ends, the Coach's own
infrastructure teardown). An event that happened while one build's suite was
the only RECORDED command may still have been caused by somebody else.

This module is the analysis the post-trial investigation uses, on a fixture
that labels what it creates. It reports a removal as caused by a build only
when:

* the removed container is matched to its creation by CONTAINER ID, and its
  creator is read from the owner label the fixture set
  (``guardkit.fixture.owner`` = the creating build's ``GUARDKIT_RUN_OWNER``);
* exactly ONE teardown receipt — a separately recorded teardown command that
  names its acting build, with start and end times — LISTS that container ID
  among the ones it removed (the fixture's containers present before the
  teardown and gone after it), and its interval covers the moment of
  removal. A receipt that merely overlapped the moment, without listing the
  container, names nobody: being there at the time is not removing it.

Only container removals are analysed; network removals are not.

Everything else is **unknown**: no teardown receipt covering the moment (a
suite's own run record is not a teardown receipt and never counts as one), two
or more teardowns overlapping it, or no creation label. A removal of an
unlabelled resource stays unattributed unless an actor-bound receipt exists.

Nothing here is a claim that a collision happened in the trial.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from guardkit.orchestrator.docker_fixtures import OWNER_LABEL, RUN_OWNER_ENV
from guardkit.orchestrator.run_evidence import HelperRun, Runner, _default_runner, within_bound

UNKNOWN = "unknown"
TEARDOWN_KIND = "teardown"

#: The Docker actions that mean "this container came into being" and "this
#: container is gone".
CREATION_ACTIONS = frozenset({"create"})
REMOVAL_ACTIONS = frozenset({"destroy"})


def _utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# =========================================================================
# The teardown receipt
# =========================================================================


@dataclass(frozen=True)
class TeardownReceipt:
    """A teardown command run as its own recorded command, naming its actor."""

    acting_build: str
    started_unix: float
    ended_unix: float
    command: str = ""
    #: Container IDs present before the teardown and gone after it; ``None``
    #: when they were not listed, in which case the receipt binds nothing.
    removed_ids: Optional[frozenset] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Optional["TeardownReceipt"]:
        """A receipt from a dict, or ``None`` when it is not an actor-bound
        teardown receipt (any other run record, or one naming no build)."""
        if not isinstance(data, Mapping) or data.get("kind") != TEARDOWN_KIND:
            return None
        actor = str(data.get("acting_build") or "").strip()
        try:
            started = float(data["started_unix"])
            ended = float(data["ended_unix"])
        except (KeyError, TypeError, ValueError):
            return None
        if not actor or ended < started:
            return None
        removed = data.get("removed_ids")
        removed_ids = (
            frozenset(str(x) for x in removed) if isinstance(removed, (list, tuple)) else None
        )
        return cls(actor, started, ended, str(data.get("command") or ""), removed_ids)


#: The label Compose puts on every container of a project.
COMPOSE_PROJECT_LABEL = "com.docker.compose.project"


def _list_project_containers(
    project: str, runner: Runner, timeout: float
) -> Optional[List[str]]:
    """IDs of the project's containers, running or not; ``None`` if unknown."""
    try:
        run = runner(
            [
                "docker", "ps", "-a", "-q", "--no-trunc",
                "--filter", f"label={COMPOSE_PROJECT_LABEL}={project}",
            ],
            cwd=None,
            env=None,
            timeout=timeout,
        )
    except Exception:  # noqa: BLE001 — the receipt says it could not list
        return None
    if run.timed_out or run.returncode != 0:
        return None
    return sorted(
        line.strip()
        for line in run.stdout.decode("utf-8", errors="replace").splitlines()
        if line.strip()
    )


def record_teardown(
    command: Sequence[str],
    *,
    acting_build: str,
    compose_project: Optional[str] = None,
    runner: Optional[Runner] = None,
    clock: Callable[[], float] = time.time,
    cwd: Optional[Path] = None,
    timeout: float = 300.0,
    list_timeout: float = 15.0,
) -> Dict[str, Any]:
    """Run a teardown command and return its receipt, naming the acting build.

    The receipt is RESOURCE-BOUND: with ``compose_project`` it lists the
    project's container IDs just before and just after the teardown (one
    bounded ``docker ps`` each) and keeps those that went, as
    ``removed_ids``. Its interval covers both listings and the command, so a
    removal event can be matched to it by container ID and time. A container
    another actor removed between the two listings would also be listed: the
    receipt says what went during this teardown, and it is a receipt of THIS
    teardown only. Without a project, or when a listing fails,
    ``removed_ids`` is ``None`` and the receipt binds no container.
    """
    runner = runner or _default_runner
    started = clock()
    before = (
        _list_project_containers(compose_project, runner, list_timeout)
        if compose_project
        else None
    )
    try:
        run = runner(list(command), cwd=cwd, env=None, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — the receipt says what happened
        run = HelperRun(None, b"", f"{type(exc).__name__}: {exc}".encode())
    after = (
        _list_project_containers(compose_project, runner, list_timeout)
        if compose_project
        else None
    )
    ended = clock()
    removed = (
        sorted(set(before) - set(after))
        if before is not None and after is not None
        else None
    )
    return {
        "kind": TEARDOWN_KIND,
        "acting_build": acting_build,
        "command": " ".join(command),
        "compose_project": compose_project,
        "ids_before": before,
        "ids_after": after,
        "removed_ids": removed,
        "started_unix": started,
        "ended_unix": ended,
        "started_at": _utc(started),
        "ended_at": _utc(ended),
        "exit_code": run.returncode,
        "timed_out": run.timed_out,
        "stderr_head": run.stderr[:2000].decode("utf-8", errors="replace"),
    }


# =========================================================================
# The analysis
# =========================================================================


@dataclass(frozen=True)
class RemovalFinding:
    """What can honestly be said about one container removal."""

    container_id: str
    name: Optional[str]
    removed_at_unix: float
    created_by: str
    removed_during: str
    statement: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _event_id(event: Mapping[str, Any]) -> str:
    actor = event.get("Actor") if isinstance(event.get("Actor"), Mapping) else {}
    return str(actor.get("ID") or event.get("id") or "")


def _attributes(event: Mapping[str, Any]) -> Mapping[str, Any]:
    actor = event.get("Actor") if isinstance(event.get("Actor"), Mapping) else {}
    attrs = actor.get("Attributes")
    return attrs if isinstance(attrs, Mapping) else {}


def _event_seconds(event: Mapping[str, Any]) -> Optional[float]:
    nano = event.get("timeNano")
    if isinstance(nano, (int, float)) and nano > 0:
        return nano / 1_000_000_000
    secs = event.get("time")
    if isinstance(secs, (int, float)) and secs > 0:
        return float(secs)
    return None


def events_from_run_evidence(records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Every container event kept by a set of run records, once each."""
    seen = set()
    events: List[Dict[str, Any]] = []
    for record in records:
        block = record.get("container_events") if isinstance(record, Mapping) else None
        for event in (block or {}).get("events") or []:
            if not isinstance(event, Mapping):
                continue
            key = (_event_id(event), event.get("Action"), event.get("timeNano") or event.get("time"))
            if key in seen:
                continue
            seen.add(key)
            events.append(dict(event))
    return events


def attribute_removals(
    events: Iterable[Mapping[str, Any]],
    receipts: Iterable[Mapping[str, Any]],
) -> List[RemovalFinding]:
    """One finding per container removal in ``events``, in time order.

    ``receipts`` may hold any run records; only actor-bound teardown receipts
    (``kind == "teardown"`` with an ``acting_build``) are used. A suite's own
    run record is never evidence of who removed a container.
    """
    teardowns = [
        r for r in (TeardownReceipt.from_dict(d) for d in receipts) if r is not None
    ]
    events = [e for e in events if isinstance(e, Mapping) and e.get("Type") == "container"]

    creator: Dict[str, str] = {}
    created: set = set()
    for event in events:
        cid = _event_id(event)
        if not cid:
            continue
        owner = str(_attributes(event).get(OWNER_LABEL) or "").strip()
        if event.get("Action") in CREATION_ACTIONS:
            created.add(cid)
        if owner and cid not in creator:
            creator[cid] = owner

    findings: List[RemovalFinding] = []
    for event in events:
        if event.get("Action") not in REMOVAL_ACTIONS:
            continue
        cid = _event_id(event)
        at = _event_seconds(event)
        if not cid or at is None:
            continue
        created_by = creator.get(cid, UNKNOWN)
        covering = [t for t in teardowns if t.started_unix <= at <= t.ended_unix]
        listing = [t for t in teardowns if t.removed_ids is not None and cid in t.removed_ids]
        bound = [t for t in listing if t in covering]
        overlapped = (
            f" (teardowns overlapping the moment: "
            f"{', '.join(sorted(t.acting_build for t in covering))})"
            if covering
            else ""
        )
        if len(bound) == 1 and len(listing) == 1:
            removed_during = bound[0].acting_build
            reason = (
                f"exactly one teardown receipt ({removed_during}'s) lists this "
                "container as removed and covers the moment of removal"
            )
        elif len(listing) > 1:
            removed_during = UNKNOWN
            reason = (
                f"{len(listing)} teardown receipts list this container as removed "
                f"({', '.join(sorted(t.acting_build for t in listing))}), so no "
                "one of them can be named"
            )
        elif listing:
            removed_during = UNKNOWN
            reason = (
                f"{listing[0].acting_build}'s teardown lists this container as "
                "removed, but its interval does not cover the moment of removal"
            )
        else:
            removed_during = UNKNOWN
            reason = (
                "no teardown receipt lists this container among the ones it "
                f"removed{overlapped}; being there at the time is not evidence "
                "of who removed it"
            )
        if created_by == UNKNOWN:
            reason += (
                "; the container's creator is unknown (no owner label"
                + ("" if cid in created else ", and its creation was not observed")
                + ")"
            )
        elif cid not in created:
            reason += "; creation not observed; creator read from the label"
        if removed_during == UNKNOWN:
            statement = UNKNOWN
        else:
            statement = f"created by {created_by}, removed during {removed_during}'s teardown"
        findings.append(
            RemovalFinding(
                container_id=cid,
                name=str(_attributes(event).get("name") or "") or None,
                removed_at_unix=at,
                created_by=created_by,
                removed_during=removed_during,
                statement=statement,
                reason=reason,
            )
        )
    findings.sort(key=lambda f: f.removed_at_unix)
    return findings


# =========================================================================
# Command line: record a teardown receipt (used by the fixture repository)
# =========================================================================


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m guardkit.orchestrator.container_attribution",
        description=(
            "Run a teardown command as its own recorded command and write a "
            "receipt naming the acting build (GUARDKIT_RUN_OWNER)."
        ),
    )
    sub = parser.add_subparsers(dest="action", required=True)
    td = sub.add_parser("record-teardown")
    td.add_argument("--receipt", required=True, type=Path)
    td.add_argument(
        "--compose-project",
        help="the fixture's Compose project; its containers are listed before "
        "and after so the receipt names the ones this teardown removed",
    )
    td.add_argument("teardown", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    command = [c for c in args.teardown if c != "--"]
    if not command:
        parser.error("give the teardown command after --")
    actor = (os.environ.get(RUN_OWNER_ENV) or "").strip()
    if not actor:
        parser.error(f"{RUN_OWNER_ENV} must name the acting build")
    receipt = record_teardown(
        command, acting_build=actor, compose_project=args.compose_project
    )

    def _write() -> bool:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return True

    # The receipt is evidence: written behind the shared evidence boundary.
    written = within_bound(
        _write, 10.0, what="writing the teardown receipt", on_failure=lambda _exc: False
    )
    if not written:
        print(f"the teardown receipt could not be written to {args.receipt}", file=sys.stderr)
        return 2
    return 0 if receipt["exit_code"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
