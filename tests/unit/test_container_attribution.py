"""Repair 7: who removed a container — only an actor-bound receipt can say.

Pure tests on synthetic event lists (no Docker). The analysis matches a
removal to its creation by container ID, reads the creator from the owner
label the fixture sets, and names the remover only when exactly one teardown
receipt that names its acting build covers the moment of removal. Everything
else is "unknown" — including the negative control, where another build's
factory-style cleanup removes a container while one build's suite is the only
recorded command.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from guardkit.orchestrator.container_attribution import (
    UNKNOWN,
    attribute_removals,
    events_from_run_evidence,
    record_teardown,
)
from guardkit.orchestrator.docker_fixtures import OWNER_LABEL
from guardkit.orchestrator.run_evidence import HelperRun

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "docker_collision_fixture"


def _ev(action: str, at: float, cid: str, owner: str | None = None, kind: str = "container") -> dict:
    attrs = {"name": f"guardkit-collision-fixture-probe-{cid}"}
    if owner:
        attrs[OWNER_LABEL] = owner
    return {
        "Type": kind,
        "Action": action,
        "Actor": {"ID": cid, "Attributes": attrs},
        "time": int(at),
        "timeNano": int(at * 1_000_000_000),
    }


def _teardown(build: str, start: float, end: float) -> dict:
    return {"kind": "teardown", "acting_build": build, "started_unix": start, "ended_unix": end}


def _suite(build: str, start: float, end: float) -> dict:
    """A suite's own run record: NOT a teardown receipt."""
    return {
        "command_kind": "independent suite (worktree)",
        "observer": {"build": build},
        "interval": {"started_unix": start, "ended_unix": end},
    }


def test_one_teardown_names_creator_and_remover():
    events = [
        _ev("create", 10.0, "c1", owner="build-A"),
        _ev("start", 10.1, "c1", owner="build-A"),
        _ev("destroy", 21.0, "c1", owner="build-A"),
    ]
    [finding] = attribute_removals(events, [_suite("build-A", 9.0, 30.0), _teardown("build-B", 20.0, 22.0)])

    assert finding.container_id == "c1"
    assert finding.created_by == "build-A"
    assert finding.removed_during == "build-B"
    assert finding.statement == "created by build-A, removed during build-B's teardown"


def test_overlapping_teardowns_are_unknown():
    events = [_ev("create", 10.0, "c1", owner="build-A"), _ev("destroy", 21.0, "c1")]
    [finding] = attribute_removals(
        events, [_teardown("build-A", 20.0, 22.0), _teardown("build-B", 20.5, 23.0)]
    )
    assert finding.removed_during == UNKNOWN
    assert finding.statement == UNKNOWN
    assert "2 teardowns overlap" in finding.reason
    assert finding.created_by == "build-A"


def test_no_actor_bound_receipt_is_unknown():
    events = [_ev("create", 10.0, "c1", owner="build-A"), _ev("destroy", 21.0, "c1")]
    [finding] = attribute_removals(events, [])
    assert finding.statement == UNKNOWN
    assert "no actor-bound teardown receipt" in finding.reason


def test_negative_control_other_builds_cleanup_during_a_sole_recorded_suite_is_unknown():
    """Build A's suite is the ONLY recorded command. Build C's factory-style
    cleanup (Forge removing fixtures when a build ends) removes A's container
    in the middle of it, and leaves no teardown receipt. That removal must not
    be pinned on A's suite — or on anyone."""
    events = [
        _ev("create", 100.0, "c-a", owner="build-A"),
        _ev("kill", 104.9, "c-a", owner="build-A"),
        _ev("destroy", 105.0, "c-a", owner="build-A"),
    ]
    findings = attribute_removals(events, [_suite("build-A", 99.0, 110.0)])

    assert [f.statement for f in findings] == [UNKNOWN]
    assert findings[0].removed_during == UNKNOWN
    assert "build-A" not in findings[0].removed_during


def test_a_teardown_outside_the_moment_is_not_used():
    events = [_ev("create", 10.0, "c1", owner="build-A"), _ev("destroy", 30.0, "c1")]
    [finding] = attribute_removals(events, [_teardown("build-B", 20.0, 22.0)])
    assert finding.statement == UNKNOWN


def test_correlation_is_by_container_id_and_unlabelled_creators_are_unknown():
    events = [
        _ev("create", 10.0, "c1", owner="build-A"),
        _ev("create", 11.0, "c2"),  # an unlabelled resource
        _ev("destroy", 21.0, "c2"),
        _ev("destroy", 21.5, "c1"),
        _ev("destroy", 21.6, "net", kind="network"),
    ]
    findings = attribute_removals(events, [_teardown("build-B", 20.0, 22.0)])

    by_id = {f.container_id: f for f in findings}
    assert set(by_id) == {"c1", "c2"}
    assert by_id["c1"].statement == "created by build-A, removed during build-B's teardown"
    assert by_id["c2"].created_by == UNKNOWN
    assert by_id["c2"].statement == "created by unknown, removed during build-B's teardown"
    assert "no owner label" in by_id["c2"].reason


def test_receipts_without_an_acting_build_are_ignored():
    events = [_ev("create", 10.0, "c1", owner="build-A"), _ev("destroy", 21.0, "c1")]
    bad = {"kind": "teardown", "acting_build": "", "started_unix": 20.0, "ended_unix": 22.0}
    [finding] = attribute_removals(events, [bad])
    assert finding.statement == UNKNOWN


def test_events_are_read_once_from_run_records():
    destroy = _ev("destroy", 21.0, "c1")
    records = [
        {"container_events": {"events": [destroy]}},
        {"container_events": {"events": [destroy, _ev("create", 10.0, "c1", owner="A")]}},
        {"container_events": {"status": "not available"}},
    ]
    events = events_from_run_evidence(records)
    assert len(events) == 2


def test_record_teardown_names_the_acting_build_and_its_interval():
    times = iter([50.0, 52.5])
    calls = []

    def _runner(argv, **kwargs):
        calls.append(argv)
        return HelperRun(0, b"", b"")

    receipt = record_teardown(
        ["docker", "compose", "down"], acting_build="build-B", runner=_runner, clock=lambda: next(times)
    )
    assert calls == [["docker", "compose", "down"]]
    assert receipt["kind"] == "teardown"
    assert receipt["acting_build"] == "build-B"
    assert (receipt["started_unix"], receipt["ended_unix"]) == (50.0, 52.5)
    assert receipt["exit_code"] == 0


def test_the_fixture_labels_every_resource_with_the_creating_build():
    compose = yaml.safe_load((FIXTURE / "compose.yaml").read_text())
    assert compose["name"] == "guardkit-collision-fixture"  # fixed on purpose
    for service in compose["services"].values():
        assert "GUARDKIT_RUN_OWNER" in service["labels"][OWNER_LABEL]
    for network in compose["networks"].values():
        assert "GUARDKIT_RUN_OWNER" in network["labels"][OWNER_LABEL]
    teardown = (FIXTURE / "teardown.sh").read_text()
    assert "record-teardown" in teardown and "--receipt" in teardown


def test_an_unobserved_creation_says_the_creator_came_from_the_label():
    [finding] = attribute_removals(
        [_ev("destroy", 21.0, "c1", owner="build-A")], [_teardown("build-B", 20.0, 22.0)]
    )
    assert finding.created_by == "build-A"
    assert "creation not observed; creator read from the label" in finding.reason


def test_the_teardown_cli_writes_its_receipt(tmp_path, monkeypatch):
    from guardkit.orchestrator import container_attribution as ca

    monkeypatch.setenv("GUARDKIT_RUN_OWNER", "build-B")
    receipt = tmp_path / "out" / "teardown.json"
    assert ca.main(["record-teardown", "--receipt", str(receipt), "--", "true"]) == 0
    import json

    assert json.loads(receipt.read_text())["acting_build"] == "build-B"
