"""``guardkit memory seed`` (project initialisation design, 4 October 2026, Part 5).

Design: ai-transition ``docs/source-material/project-initialisation-2026-10-04/design.md``
Part 5 and dispositions R4, R5 and R6.

No live service is touched. Each test builds a real git repository in a
temporary folder. Publishing goes through the real ``FleetMemoryClient.add_episode``
with the bus replaced by a fake broker that keeps JetStream's duplicate window
(a message id seen once is dropped) and hands each episode to fleet-memory's
REAL payload registry and ``DeterministicWriter`` over an in-memory store. The
client's ``read_record`` reads that same store. So "stored", "one record",
"new version" and "supersedes" are fleet-memory's own behaviour, not a mock's.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import pytest
from click.testing import CliRunner

pytest.importorskip("nats_core")
pytest.importorskip("fleet_memory.writer.core")
store_memory = pytest.importorskip("langgraph.store.memory")

from fleet_memory.payloads.registry import get_model_for_type  # noqa: E402
from fleet_memory.writer.core import DeterministicWriter  # noqa: E402
from fleet_memory.writer.identity import record_identity  # noqa: E402

import guardkit.knowledge.fleet_memory_client as fmc  # noqa: E402
from guardkit.cli.memory import memory as memory_cli  # noqa: E402
from guardkit.knowledge.fleet_memory_client import (  # noqa: E402
    FleetMemoryClient,
    FleetMemoryConfig,
)
from guardkit.knowledge.fleet_memory_mapping import resolve  # noqa: E402
from guardkit.knowledge.fleet_memory_payloads import build_memory_episode  # noqa: E402
from guardkit.memory.harvest_publisher import PublishSummary  # noqa: E402
from guardkit.memory.seed import (  # noqa: E402
    SeedRefused,
    plan_seed,
    publish_and_confirm,
)


# ---------------------------------------------------------------------------
# A repository, a broker, a relay and a store — all local
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Seed Test",
         "-c", "user.email=seed@example.invalid", *args],
        check=True, capture_output=True, text=True,
    ).stdout


def _repo(tmp_path: Path, files: dict[str, str], *, project: Optional[str] = "alpha") -> Path:
    repo = tmp_path / "project"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if ".guardkit/config.yaml" not in files:
        config = repo / ".guardkit" / "config.yaml"
        config.parent.mkdir(parents=True, exist_ok=True)
        memory = f"memory:\n  project: {project}\n" if project else ""
        declared = "".join(
            f"      - {rel}\n" for rel in files if not rel.startswith(".guardkit")
        )
        config.write_text(
            memory + "autobuild:\n  player:\n    required_documents:\n" + declared,
            encoding="utf-8",
        )
    _commit(repo, "initial")
    return repo


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


class Memory:
    """The broker's duplicate window, the relay's typed path, and the store."""

    def __init__(self) -> None:
        self.store = store_memory.InMemoryStore()
        self.writer = DeterministicWriter(self.store, None)
        self.seen_message_ids: set[str] = set()
        self.published: list[Any] = []
        self.dropped: list[str] = []
        self.dark = False  # the relay does not write (bus accepted, store untouched)

    async def publish_episodes(self, episodes, client=None):
        for episode in episodes:
            self.published.append(episode)
            if episode.episode_id in self.seen_message_ids:
                self.dropped.append(episode.episode_id)  # JetStream duplicate window
                continue
            self.seen_message_ids.add(episode.episode_id)
            if self.dark:
                continue
            model = get_model_for_type(episode.payload_type)
            await self.writer.write(model(**json.loads(episode.body)))
        return PublishSummary(published=len(episodes), skipped_oversized=0, counts_per_type={})

    def client(self, project: str, *, enabled: bool = True) -> FleetMemoryClient:
        client = FleetMemoryClient(FleetMemoryConfig(enabled=enabled, project=project))
        client._store = self.store
        client._nats_available = True
        return client

    async def get(self, project: str, payload_type: str, identifier: str) -> Optional[dict]:
        key = f"{payload_type}:{project}:{identifier}"
        item = await self.store.aget(("fleet_memory", project, payload_type), str(record_identity(key)))
        return item.value if item else None

    async def count(self, project: str, payload_type: str) -> int:
        return len(await self.store.asearch(("fleet_memory", project, payload_type), limit=100))


@pytest.fixture
def memory(monkeypatch: pytest.MonkeyPatch) -> Memory:
    fake = Memory()
    monkeypatch.setattr(
        "guardkit.memory.harvest_publisher.publish_episodes", fake.publish_episodes
    )
    return fake


@pytest.fixture(autouse=True)
def _settled_name_is_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("GUARDKIT_MEMORY_PROJECT", "GUARDKIT_FACTORY_LAUNCH"):
        monkeypatch.delenv(name, raising=False)
    for attribute in ("_memory_project_resolution", "_memory_client", "_memory_factory"):
        monkeypatch.setattr(fmc, attribute, None)
    monkeypatch.setattr(fmc, "_backend_initialized", False)


async def _no_sleep(_: float) -> None:
    return None


def _seed(repo: Path, project: str, client: Any):
    plan = plan_seed(repo, project)
    assert plan.refusals == []
    results = asyncio.run(
        publish_and_confirm(plan, client, attempts=2, delay_seconds=0, sleep=_no_sleep)
    )
    return plan, results


def _stored(value: dict) -> dict:
    return json.loads(value["content"])


MISSION = "Status: accepted (2026-10-04, Rich)\n\n# Mission\n\nCount users per day.\n"
ADR_001 = """# ADR-ARCH-001: Use a modular monolith

**Status:** Accepted
**Date:** 2026-10-04

## Context

One machine, one process.

## Decision

Use the modular monolith pattern.

## Alternatives Considered

- Microservices
- Event-driven architecture

## Consequences

- (+) Simple deployment
- (-) Single machine
"""
ADR_002 = """# ADR-ARCH-002: Split the reporting module

> Status: **Proposed**

Supersedes: ADR-ARCH-001

## Context

Reporting grew.

## Decision

Split reporting into its own module.
"""
DECISIONS = "docs/architecture/decisions"


# ---------------------------------------------------------------------------
# Identity, provenance and kinds
# ---------------------------------------------------------------------------


class TestPlan:
    def test_documents_and_decisions_get_their_keys(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "docs/constitution/mission.md": MISSION,
            f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md": ADR_001,
        })
        plan = plan_seed(repo, "alpha")
        by_path = {item.path: item for item in plan.items}
        mission = by_path["docs/constitution/mission.md"]
        assert mission.natural_key == "document:alpha:docs_constitution_mission_md"
        assert mission.payload["content"] == MISSION
        assert mission.payload["domain_tags"] == ["architecture", "project_document"]
        decision = by_path[f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md"]
        # The key /system-arch already writes (memory-preamble.md: ADR_ARCH_NNN).
        assert decision.natural_key == "adr:alpha:ADR_ARCH_001"
        payload = decision.payload
        assert payload["title"] == "Use a modular monolith"
        assert payload["status"] == "Accepted"
        assert payload["context"] == "One machine, one process."
        assert payload["decision"] == "Use the modular monolith pattern."
        assert payload["alternatives"] == ["Microservices", "Event-driven architecture"]
        assert payload["consequences"].startswith("- (+) Simple deployment")
        assert payload["domain_tags"] == ["architecture"]
        # The payload validates against fleet-memory's own model.
        get_model_for_type("adr")(**payload)
        get_model_for_type("document")(**mission.payload)

    def test_source_ref_names_path_last_commit_and_content_hash(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION, "docs/other.md": "x\n"})
        first = _git(repo, "rev-parse", "HEAD").strip()
        (repo / "docs" / "other.md").write_text("y\n")
        _commit(repo, "other only")
        item = next(i for i in plan_seed(repo, "alpha").items if i.path == "docs/mission.md")
        import hashlib

        digest = hashlib.sha256(MISSION.encode()).hexdigest()[:16]
        assert item.source_ref == f"docs/mission.md@{first}#sha256:{digest}"
        assert item.payload["source_ref"] == item.source_ref

    def test_decision_keeps_status_and_supersedes_link(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md": ADR_001,
            f"{DECISIONS}/ADR-ARCH-002-split-reporting.md": ADR_002,
        })
        item = next(i for i in plan_seed(repo, "alpha").items if i.decision_id == "ADR-ARCH-002")
        assert item.payload["status"] == "Proposed"
        assert item.payload["supersedes"] == ["adr:alpha:ADR_ARCH_001"]

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("Supersedes: ADR-ARCH-001 (see also DDR-007)", ["ADR_ARCH_001"]),
            ("**Supersedes:** ADR-ARCH-001, ADR-SP-002 and DDR-003; see ADR-ARCH-009",
             ["ADR_ARCH_001", "ADR_SP_002", "DDR_003"]),
            ("> Supersedes: `ADR-ARCH-001`", ["ADR_ARCH_001"]),
            ("Supersedes: ADR-ARCH-001-modular-monolith.md", ["ADR_ARCH_001"]),
            ("Supersedes: nothing yet, but compare ADR-ARCH-001", []),
        ],
    )
    def test_supersedes_line_takes_only_the_leading_ids(
        self, line: str, expected: list[str]
    ) -> None:
        from guardkit.memory.seed import decision_fields

        text = f"# ADR-ARCH-005: Later\n\nStatus: accepted\n{line}\n\n## Decision\n\nD.\n"
        fields = decision_fields("ADR-ARCH-005", text, "alpha")
        assert fields.get("supersedes", []) == [f"adr:alpha:{i}" for i in expected]

    def test_supersedes_heading_reads_first_line_and_list_items_only(self) -> None:
        from guardkit.memory.seed import decision_fields

        text = (
            "# DDR-010: Later\n\n> Status: Accepted\n\n## Supersedes\n\n"
            "DDR-001 (the first draft)\n"
            "Unlike DDR-008, this keeps the queue.\n"
            "- DDR-002 and DDR-003, both retired\n"
            "- related: DDR-009\n\n## Decision\n\nD.\n"
        )
        fields = decision_fields("DDR-010", text, "alpha")
        assert fields["supersedes"] == [
            "adr:alpha:DDR_001", "adr:alpha:DDR_002", "adr:alpha:DDR_003",
        ]

    def test_ddr_and_files_without_a_status_line(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            "docs/design/decisions/DDR-001.md": "# DDR-001: Strict validation\n\n> Status: Accepted\n\n## Decision\n\nValidate at start.\n",
            "docs/ADR-ARCH-009-notes.md": "# Notes with no status line\n",
        })
        items = {i.path: i for i in plan_seed(repo, "alpha").items}
        assert items["docs/design/decisions/DDR-001.md"].natural_key == "adr:alpha:DDR_001"
        assert items["docs/design/decisions/DDR-001.md"].payload["domain_tags"] == ["architecture", "design"]
        # A decision-like name without a status line is an ordinary document.
        assert items["docs/ADR-ARCH-009-notes.md"].payload_type == "document"

    def test_seed_documents_patterns_over_committed_files(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            ".guardkit/config.yaml": (
                "memory:\n  project: alpha\n  seed_documents:\n"
                f"    - docs/mission.md\n    - {DECISIONS}/*.md\n"
                "autobuild:\n  player:\n    required_documents:\n      - docs/mission.md\n"
            ),
            "docs/mission.md": MISSION,
            f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md": ADR_001,
            f"{DECISIONS}/ADR-ARCH-002-split-reporting.md": ADR_002,
            "docs/unlisted.md": "not declared\n",
        })
        (repo / DECISIONS / "ADR-ARCH-003-untracked.md").write_text(ADR_001)
        plan = plan_seed(repo, "alpha")
        assert plan.declared_from == "memory.seed_documents"
        assert [i.path for i in plan.items] == [
            "docs/mission.md",
            f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md",
            f"{DECISIONS}/ADR-ARCH-002-split-reporting.md",
        ]

    def test_two_projects_stay_separate(self, tmp_path: Path, memory: Memory) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        _seed(repo, "alpha", memory.client("alpha"))
        _seed(repo, "beta", memory.client("beta"))
        assert asyncio.run(memory.get("alpha", "document", "docs_mission_md"))["project"] == "alpha"
        assert asyncio.run(memory.get("beta", "document", "docs_mission_md"))["project"] == "beta"
        assert asyncio.run(memory.count("alpha", "document")) == 1
        assert asyncio.run(memory.count("beta", "document")) == 1


# ---------------------------------------------------------------------------
# Refusals — the whole run, before anything is published
# ---------------------------------------------------------------------------


class TestRefusals:
    def test_two_paths_that_sanitise_alike(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"docs/a-b.md": "one\n", "docs/a_b.md": "two\n"})
        plan = plan_seed(repo, "alpha")
        assert any("docs/a-b.md and docs/a_b.md" in r for r in plan.refusals)

    def test_two_files_with_one_decision_id(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {
            f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md": ADR_001,
            "docs/old/ADR-ARCH-001-first-draft.md": ADR_001,
        })
        plan = plan_seed(repo, "alpha")
        assert any("adr:alpha:ADR_ARCH_001" in r and "first-draft" in r for r in plan.refusals)

    def test_uncommitted_change_refused(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        (repo / "docs" / "mission.md").write_text(MISSION + "edited\n")
        plan = plan_seed(repo, "alpha")
        assert any("docs/mission.md: has uncommitted changes" in r for r in plan.refusals)

    def test_staged_but_uncommitted_change_refused(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        (repo / "docs" / "mission.md").write_text(MISSION + "edited\n")
        _git(repo, "add", "docs/mission.md")
        assert plan_seed(repo, "alpha").refusals

    def test_declared_but_never_committed(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        (repo / "docs" / "mission.md").unlink()
        _commit(repo, "delete the mission")
        plan = plan_seed(repo, "alpha")
        assert any("docs/mission.md: declared, but not committed" in r for r in plan.refusals)

    def test_uncommitted_declaration_refused(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        with (repo / ".guardkit" / "config.yaml").open("a") as handle:
            handle.write("      - docs/extra.md\n")
        with pytest.raises(SeedRefused, match="uncommitted"):
            plan_seed(repo, "alpha")

    def test_symbolic_link_refused(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"docs/real.md": MISSION})
        (repo / "docs" / "linked.md").symlink_to("real.md")
        (repo / ".guardkit" / "config.yaml").write_text(
            "memory:\n  project: alpha\nautobuild:\n  player:\n    required_documents:\n"
            "      - docs/linked.md\n"
        )
        _commit(repo, "link")
        plan = plan_seed(repo, "alpha")
        assert any("docs/linked.md: is a symbolic link" in r for r in plan.refusals)


# ---------------------------------------------------------------------------
# Writing, the duplicate window, versions and read-back
# ---------------------------------------------------------------------------


class TestWriting:
    def test_stored_only_after_read_back(self, tmp_path: Path, memory: Memory) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        plan, results = _seed(repo, "alpha", memory.client("alpha"))
        assert [(r.status, r.version) for r in results] == [("stored", 1)]
        assert results[0].line().endswith("stored (version 1)")
        stored = asyncio.run(memory.get("alpha", "document", "docs_mission_md"))
        assert _stored(stored)["source_ref"] == plan.items[0].source_ref

    def test_dark_relay_is_published_not_confirmed(self, tmp_path: Path, memory: Memory) -> None:
        memory.dark = True
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        _, results = _seed(repo, "alpha", memory.client("alpha"))
        assert results[0].status == "published, not confirmed"
        assert "no record was found" in results[0].detail

    def test_no_read_route_says_so(self, tmp_path: Path, memory: Memory) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        _, results = _seed(repo, "alpha", memory.client("alpha", enabled=False))
        assert results[0].status == "published, not confirmed"
        assert "switched off" in results[0].detail

    def test_not_published(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})

        class Refusing:
            async def add_episode(self, **_: Any) -> None:
                return None

        _, results = _seed(repo, "alpha", Refusing())
        assert results[0].status == "not published"

    def test_unchanged_reseed_is_identical_and_keeps_one_version(
        self, tmp_path: Path, memory: Memory
    ) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        client = memory.client("alpha")
        first, _ = _seed(repo, "alpha", client)
        second, results = _seed(repo, "alpha", client)
        assert second.items[0].payload == first.items[0].payload
        assert second.items[0].dedup_token == first.items[0].dedup_token
        # The same token inside the window: the broker drops the re-send.
        assert memory.dropped == [f"document:alpha:docs_mission_md.{first.items[0].dedup_token}"]
        assert [(r.status, r.version) for r in results] == [("stored", 1)]

    def test_changed_file_inside_the_window_gets_a_new_version(
        self, tmp_path: Path, memory: Memory
    ) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        client = memory.client("alpha")
        first, _ = _seed(repo, "alpha", client)
        (repo / "docs" / "mission.md").write_text(MISSION + "Second success measure.\n")
        _commit(repo, "mission grows")
        second, results = _seed(repo, "alpha", client)
        assert second.items[0].dedup_token != first.items[0].dedup_token
        assert memory.dropped == []  # never mistaken for a duplicate
        assert [(r.status, r.version) for r in results] == [("stored", 2)]
        assert asyncio.run(memory.count("alpha", "document")) == 1

    def test_supersedes_reaches_the_store(self, tmp_path: Path, memory: Memory) -> None:
        repo = _repo(tmp_path, {
            f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md": ADR_001,
            f"{DECISIONS}/ADR-ARCH-002-split-reporting.md": ADR_002,
        })
        _seed(repo, "alpha", memory.client("alpha"))
        old = asyncio.run(memory.get("alpha", "adr", "ADR_ARCH_001"))
        new = asyncio.run(memory.get("alpha", "adr", "ADR_ARCH_002"))
        assert old["superseded_by"] == "adr:alpha:ADR_ARCH_002"
        assert _stored(new)["status"] == "Proposed"
        assert _stored(new)["supersedes"] == ["adr:alpha:ADR_ARCH_001"]


class TestCommandWrittenDecision:
    """R4 and R6: seeding after /system-arch wrote the decision."""

    def _command_writes(self, memory: Memory, **override: Any) -> None:
        # What /system-arch writes through memory_write_payload (system-arch.md).
        fields = dict(
            project="alpha", identifier="ADR_ARCH_001", decision="Use the modular monolith pattern.",
            status="accepted", title="Use a modular monolith", context="One machine, one process.",
            consequences="Simple deployment; single machine.",
            alternatives=["Microservices"], domain_tags=["architecture"],
            source_ref=f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md",
        )
        fields.update(override)
        asyncio.run(memory.writer.write(get_model_for_type("adr")(**fields)))

    def test_one_record_under_the_commands_key(self, tmp_path: Path, memory: Memory) -> None:
        self._command_writes(memory)
        repo = _repo(tmp_path, {f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md": ADR_001})
        _, results = _seed(repo, "alpha", memory.client("alpha"))
        assert [(r.natural_key, r.status, r.version) for r in results] == [
            ("adr:alpha:ADR_ARCH_001", "stored", 2)
        ]
        assert asyncio.run(memory.count("alpha", "adr")) == 1
        stored = _stored(asyncio.run(memory.get("alpha", "adr", "ADR_ARCH_001")))
        for key in ("title", "context", "consequences", "alternatives"):
            assert stored[key], key  # the reasoning is kept, not reduced

    def test_changing_only_context_gives_a_new_version_with_it(
        self, tmp_path: Path, memory: Memory
    ) -> None:
        repo = _repo(tmp_path, {f"{DECISIONS}/ADR-ARCH-001-modular-monolith.md": ADR_001})
        client = memory.client("alpha")
        _seed(repo, "alpha", client)
        path = repo / DECISIONS / "ADR-ARCH-001-modular-monolith.md"
        path.write_text(ADR_001.replace("One machine, one process.", "One machine, two processes."))
        _commit(repo, "context only")
        plan, results = _seed(repo, "alpha", client)
        emitted = json.loads(memory.published[-1].body)  # the payload add_episode emitted
        assert emitted["context"] == "One machine, two processes."
        assert emitted["title"] == "Use a modular monolith"
        assert emitted["alternatives"] == ["Microservices", "Event-driven architecture"]
        assert [(r.status, r.version) for r in results] == [("stored", 2)]


# ---------------------------------------------------------------------------
# Existing callers are untouched (R6)
# ---------------------------------------------------------------------------


class TestExistingCallersUnchanged:
    def test_adr_service_body_payload_is_byte_identical(self) -> None:
        from guardkit.knowledge.adr import ADREntity

        entity = ADREntity(
            id="ADR-0007", title="Use Postgres", context="We need a store.",
            decision="Use Postgres.", consequences=["one", "two"], supersedes="ADR-0001",
            alternatives_considered=["SQLite"],
        )
        body = asdict(entity)
        body["status"] = body["status"].value
        body["trigger"] = body["trigger"].value
        episode = build_memory_episode(
            resolve("adrs"), name="adr_ADR-0007", episode_body=json.dumps(body, default=str),
            project="alpha",
        )
        # Exactly the payload this caller produced before the change.
        assert episode.body == json.dumps({
            "project": "alpha",
            "identifier": "ADR_0007",
            "source_ref": "ADR-0007",
            "domain_tags": ["decision"],
            "decision": "Use Postgres.",
            "status": "accepted",
        })

    def test_minimal_adr_body_unchanged(self) -> None:
        episode = build_memory_episode(
            resolve("architecture_decisions"), name="ADR-0002",
            episode_body=json.dumps({"id": "ADR-0002", "title": "T", "source_task_id": "TASK-1"}),
            project="alpha",
        )
        assert episode.body == json.dumps({
            "project": "alpha", "identifier": "ADR_0002", "source_ref": "TASK-1",
            "domain_tags": ["system"], "decision": "T", "status": "accepted",
        })

    def test_document_without_provenance_keeps_the_prose_path(self) -> None:
        episode = build_memory_episode(
            resolve("project_architecture"), name="arch",
            episode_body=json.dumps({"content": "prose"}), project="alpha",
        )
        assert episode.content_format == "markdown"
        assert episode.payload_type is None
        assert episode.body == "prose"


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------


class TestCommand:
    def test_memory_off_refused(self, tmp_path: Path) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION}, project=None)
        result = CliRunner().invoke(memory_cli, ["seed", "--repo", str(repo)])
        assert result.exit_code == 1
        assert "no memory to seed into" in result.output

    def test_dry_run_prints_the_plan_and_writes_nothing(
        self, tmp_path: Path, memory: Memory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        monkeypatch.setattr(
            "guardkit.cli.memory.get_memory_client",
            lambda: pytest.fail("dry run must not open a client"),
        )
        result = CliRunner().invoke(memory_cli, ["seed", "--repo", str(repo), "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "docs/mission.md → document:alpha:docs_mission_md" in result.output
        assert "Dry run: nothing was written." in result.output
        assert memory.published == []

    def test_refusal_exits_non_zero_and_writes_nothing(
        self, tmp_path: Path, memory: Memory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = _repo(tmp_path, {"docs/a-b.md": "one\n", "docs/a_b.md": "two\n"})
        monkeypatch.setattr("guardkit.cli.memory.get_memory_client", lambda: memory.client("alpha"))
        result = CliRunner().invoke(memory_cli, ["seed", "--repo", str(repo)])
        assert result.exit_code == 1
        assert "Nothing was written." in result.output
        assert memory.published == []

    def test_run_reports_each_file_and_exit_code(
        self, tmp_path: Path, memory: Memory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = _repo(tmp_path, {"docs/mission.md": MISSION})
        monkeypatch.setattr("guardkit.cli.memory.get_memory_client", lambda: memory.client("alpha"))
        result = CliRunner().invoke(memory_cli, ["seed", "--repo", str(repo)])
        assert result.exit_code == 0, result.output
        assert "docs/mission.md → document:alpha:docs_mission_md: stored (version 1)" in result.output

        memory.dark = True
        (repo / "docs" / "mission.md").write_text(MISSION + "more\n")
        _commit(repo, "more")
        monkeypatch.setattr("guardkit.memory.seed.READ_BACK_DELAY_SECONDS", 0)
        result = CliRunner().invoke(memory_cli, ["seed", "--repo", str(repo)])
        assert result.exit_code == 1
        assert "published, not confirmed" in result.output
