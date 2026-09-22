"""Which memory does a build use, and why — every branch of the one answer.

The rule these tests pin (design pass 2026-09-21, item 2):

1. A name handed over on purpose wins, and only when it is really set.
2. Otherwise the project's own declaration, read from its own settings file in
   the folder being built, bounded and safe.
3. Otherwise NOTHING: memory is off, said out loud once with the line to add,
   and nothing is read or written under any name — least of all "guardkit",
   which is the name every project's records used to end up under.

Nothing here touches a real memory: no store, no database, no embedder, no
broker, no door. The writes and reads are watched by a stand-in object that
records what it was asked for.
"""

from __future__ import annotations

import json
import threading

import pytest

from guardkit.knowledge.memory_project import (
    FACTORY_LAUNCH_ENV,
    MEMORY_PROJECT_ENV,
    MAX_CONFIG_BYTES,
    resolve_memory_project,
)


def _declare(folder, text: str) -> None:
    """Write a settings file in a project folder (no language, no layout)."""
    settings_dir = folder / ".guardkit"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "config.yaml").write_text(text, encoding="utf-8")


# ===========================================================================
# The order of authority
# ===========================================================================


def test_a_name_handed_over_on_purpose_wins(tmp_path):
    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    answer = resolve_memory_project(tmp_path, env={MEMORY_PROJECT_ENV: "handed_over"})
    assert answer.project == "handed_over"
    assert answer.source == "handover"
    assert answer.is_on


def test_an_empty_handover_is_not_a_handover(tmp_path):
    """Set-but-blank is nobody handing anything over: the project's own word wins."""
    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    for blank in ("", "   ", "\t"):
        answer = resolve_memory_project(tmp_path, env={MEMORY_PROJECT_ENV: blank})
        assert answer.project == "widget_shop"
        assert answer.source == "declaration"


def test_a_factory_launch_never_takes_the_name_from_the_folder(tmp_path):
    """The fault a review found on 22 September 2026, and the fence for it.

    A factory reads the project's declaration itself, at the commit the work
    started from. The folder a leg is pointed at is a working copy, and it said
    something else: with ``changed_project`` in the worktree and
    ``recorded_project`` in the ledger, a call the factory made and handed no
    name to took the worktree's name. A launch that says a factory made it now
    runs with memory OFF instead.
    """
    _declare(tmp_path, "memory:\n  project: changed_project\n")

    answer = resolve_memory_project(tmp_path, env={FACTORY_LAUNCH_ENV: "1"})

    assert answer.project is None
    assert answer.source == "none"
    assert not answer.is_on
    assert "a factory launched this" in answer.message
    assert "changed_project" not in answer.message


def test_a_factory_launch_still_uses_the_name_it_was_handed(tmp_path):
    """The handover is the point: the name it hands over is the one used."""
    _declare(tmp_path, "memory:\n  project: changed_project\n")

    answer = resolve_memory_project(
        tmp_path,
        env={FACTORY_LAUNCH_ENV: "1", MEMORY_PROJECT_ENV: "recorded_project"},
    )

    assert answer.project == "recorded_project"
    assert answer.source == "handover"


def test_without_the_factory_setting_the_folder_still_answers(tmp_path):
    """GuardKit used by hand is untouched: its own folder still declares."""
    _declare(tmp_path, "memory:\n  project: widget_shop\n")

    for blank in ({}, {FACTORY_LAUNCH_ENV: ""}, {FACTORY_LAUNCH_ENV: "   "}):
        answer = resolve_memory_project(tmp_path, env=blank)
        assert answer.project == "widget_shop"
        assert answer.source == "declaration"


def test_the_project_declares_its_own_name(tmp_path):
    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    answer = resolve_memory_project(tmp_path, env={})
    assert answer.project == "widget_shop"
    assert answer.source == "declaration"
    assert str(tmp_path) in answer.message


def test_nothing_said_means_nothing_at_all(tmp_path):
    answer = resolve_memory_project(tmp_path, env={})
    assert answer.project is None
    assert answer.source == "none"
    assert not answer.is_on
    # The sentence says which line to add to which file, in plain words.
    assert "memory: OFF" in answer.message
    assert "memory:" in answer.message
    assert "project:" in answer.message
    assert str(tmp_path / ".guardkit" / "config.yaml") in answer.message
    # And it never suggests a name to fall back to (the settings folder is
    # called .guardkit, so look for the declaration, not the word).
    assert "project: guardkit" not in answer.message


def test_no_folder_at_all_is_not_an_error(tmp_path):
    answer = resolve_memory_project(None, env={})
    assert answer.project is None
    assert answer.source == "none"


def test_a_settings_file_with_no_memory_block_says_nothing(tmp_path):
    _declare(tmp_path, "something_else:\n  key: value\n")
    assert resolve_memory_project(tmp_path, env={}).source == "none"


def test_a_memory_block_with_other_settings_but_no_name_says_nothing(tmp_path):
    """The memory block has other owners; only `project:` is this answer's."""
    _declare(
        tmp_path,
        "memory:\n  fleet:\n    context_sources:\n"
        "      relevant_patterns:\n        document_tags: [a_tag]\n",
    )
    assert resolve_memory_project(tmp_path, env={}).source == "none"


# ===========================================================================
# A name that breaks the rule is refused, never rewritten
# ===========================================================================


@pytest.mark.parametrize(
    "bad",
    ["widget shop", "widget-shop", "widget.shop", "widget/shop", "widget:shop", "wi!dget"],
)
def test_a_declared_name_that_breaks_the_rule_is_refused(tmp_path, bad):
    _declare(tmp_path, f"memory:\n  project: {json.dumps(bad)}\n")
    answer = resolve_memory_project(tmp_path, env={})
    assert answer.project is None
    assert answer.source == "refused"
    assert "letters, digits and underscores" in answer.message
    # Never quietly rewritten into something acceptable.
    assert "widget_shop" not in (answer.project or "")


def test_a_handed_over_name_that_breaks_the_rule_is_refused(tmp_path):
    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    answer = resolve_memory_project(tmp_path, env={MEMORY_PROJECT_ENV: "not a name"})
    assert answer.project is None
    assert answer.source == "refused"
    # It does NOT fall through to the declaration: someone meant that name.
    assert "widget_shop" not in answer.message


def test_an_empty_declared_name_is_refused(tmp_path):
    _declare(tmp_path, 'memory:\n  project: ""\n')
    answer = resolve_memory_project(tmp_path, env={})
    assert answer.project is None
    assert answer.source == "refused"


def test_a_declared_name_that_is_not_text_is_refused(tmp_path):
    _declare(tmp_path, "memory:\n  project:\n    - a_list\n")
    answer = resolve_memory_project(tmp_path, env={})
    assert answer.project is None
    assert answer.source == "refused"


def test_an_enormous_declared_name_is_refused(tmp_path):
    _declare(tmp_path, f"memory:\n  project: {'a' * 500}\n")
    assert resolve_memory_project(tmp_path, env={}).source == "refused"


def test_surrounding_blanks_are_ignored_not_rewritten(tmp_path):
    _declare(tmp_path, 'memory:\n  project: "  widget_shop  "\n')
    assert resolve_memory_project(tmp_path, env={}).project == "widget_shop"


# ===========================================================================
# The reader is bounded and safe, and never raises
# ===========================================================================


def test_a_settings_file_that_is_a_symlink_is_ignored(tmp_path):
    real = tmp_path / "elsewhere.yaml"
    real.write_text("memory:\n  project: smuggled_in\n", encoding="utf-8")
    (tmp_path / ".guardkit").mkdir()
    (tmp_path / ".guardkit" / "config.yaml").symlink_to(real)
    answer = resolve_memory_project(tmp_path, env={})
    assert answer.project is None
    assert answer.source == "none"


def test_an_oversized_settings_file_is_ignored(tmp_path):
    _declare(
        tmp_path,
        "memory:\n  project: widget_shop\n" + ("# padding\n" * (MAX_CONFIG_BYTES // 5)),
    )
    answer = resolve_memory_project(tmp_path, env={})
    assert answer.project is None
    assert answer.source == "none"


def test_a_malformed_settings_file_is_ignored(tmp_path):
    _declare(tmp_path, "memory:\n  project: [unclosed\n   : :\n")
    answer = resolve_memory_project(tmp_path, env={})
    assert answer.project is None
    assert answer.source == "none"


def test_a_settings_file_that_is_not_settings_is_ignored(tmp_path):
    _declare(tmp_path, "just a line of prose\n")
    assert resolve_memory_project(tmp_path, env={}).source == "none"


def test_a_settings_folder_instead_of_a_file_is_ignored(tmp_path):
    (tmp_path / ".guardkit" / "config.yaml").mkdir(parents=True)
    assert resolve_memory_project(tmp_path, env={}).source == "none"


def test_an_unreadable_settings_file_is_ignored(tmp_path):
    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    path = tmp_path / ".guardkit" / "config.yaml"
    path.chmod(0o000)
    try:
        answer = resolve_memory_project(tmp_path, env={})
    finally:
        path.chmod(0o644)
    assert answer.project is None


def test_a_folder_that_does_not_exist_is_ignored(tmp_path):
    assert resolve_memory_project(tmp_path / "nowhere", env={}).source == "none"


# ===========================================================================
# What the rest of GuardKit does with the answer
# ===========================================================================


class _StandInStore:
    """Stands in for everything outside this process: records, connects nothing."""

    def __init__(self) -> None:
        self.reads: list[str] = []
        self.writes: list[str] = []


@pytest.fixture
def memory_module(monkeypatch, tmp_path):
    """The memory client module, with its settled answer reset around each test."""
    import guardkit.knowledge.fleet_memory_client as fmc

    monkeypatch.delenv(MEMORY_PROJECT_ENV, raising=False)
    fmc.reset_memory_project()
    yield fmc
    fmc.reset_memory_project()
    fmc._memory_client = None
    fmc._memory_factory = None
    fmc._backend_initialized = False


def test_the_settled_answer_reaches_the_shared_configuration(memory_module, tmp_path):
    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    answer = memory_module.configure_memory_project(tmp_path)
    assert answer.project == "widget_shop"
    assert memory_module._load_fleet_config_from_env().project == "widget_shop"


def test_the_settled_answer_is_said_out_loud_when_there_is_none(
    memory_module, tmp_path, caplog
):
    with caplog.at_level("WARNING"):
        answer = memory_module.configure_memory_project(tmp_path)
    assert answer.project is None
    assert "memory: OFF" in caplog.text
    assert str(tmp_path / ".guardkit" / "config.yaml") in caplog.text


def test_every_thread_gets_the_same_name(memory_module, tmp_path):
    """One answer for the build: the second thread cannot get a different name."""
    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    memory_module.configure_memory_project(tmp_path)
    config = memory_module.FleetMemoryConfig(
        enabled=True, project=memory_module._load_fleet_config_from_env().project
    )
    factory = memory_module.FleetMemoryClientFactory(config)

    seen: dict[str, object] = {}

    def in_another_thread() -> None:
        client = factory.get_thread_client()
        seen["project"] = client.config.project if client else None
        seen["client"] = client

    here = factory.get_thread_client()
    thread = threading.Thread(target=in_another_thread)
    thread.start()
    thread.join()

    assert here is not None and here.config.project == "widget_shop"
    assert seen["project"] == "widget_shop"
    # A distinct client per thread (the store is tied to the loop that opened it),
    # one shared name.
    assert seen["client"] is not here


def test_with_no_name_no_thread_gets_a_client(memory_module, tmp_path, caplog):
    config = memory_module.FleetMemoryConfig(enabled=True, project=None)
    factory = memory_module.FleetMemoryClientFactory(config)
    with caplog.at_level("WARNING"):
        assert factory.get_thread_client() is None
    assert "memory: OFF" in caplog.text


async def test_with_no_name_nothing_is_read(memory_module, monkeypatch):
    """The stand-in store sees NO call, and no name is invented for one."""
    store = _StandInStore()

    def refuse(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the read path was entered with no memory name")

    monkeypatch.setattr("fleet_memory.retrieval.search", refuse, raising=False)

    client = memory_module.FleetMemoryClient(
        memory_module.FleetMemoryConfig(enabled=True, project=None)
    )
    client._read_available = True
    client._store = store

    assert await client.search(query="anything") == []
    assert store.reads == []


async def test_with_no_name_nothing_is_written(memory_module, monkeypatch):
    """The stand-in publisher sees NO episode, under "guardkit" or anything else."""
    store = _StandInStore()

    async def refuse(episodes):  # pragma: no cover - must never run
        raise AssertionError("the write path was entered with no memory name")

    monkeypatch.setattr(
        "guardkit.memory.harvest_publisher.publish_episodes", refuse, raising=False
    )

    client = memory_module.FleetMemoryClient(
        memory_module.FleetMemoryConfig(enabled=True, project=None)
    )
    client._nats_available = True

    written = await client.add_episode(
        name="OUT: TASK-1",
        episode_body=json.dumps({"task_id": "TASK-1", "success": True}),
        group_id="task_outcomes",
    )
    assert written is None
    assert store.writes == []


async def test_with_no_name_the_store_is_never_opened(memory_module):
    client = memory_module.FleetMemoryClient(
        memory_module.FleetMemoryConfig(enabled=True, project=None)
    )
    client._read_available = True
    assert await client.initialize() is False
    assert client._store is None


async def test_the_declared_name_is_what_the_read_asks_for(memory_module, monkeypatch, tmp_path):
    """End of the read path: the name on the request is the project's own."""
    monkeypatch.chdir(tmp_path)  # the read log lands here, not in the repository
    asked: dict = {}

    async def stand_in_search(request, store):
        asked["project"] = request.project
        return []

    monkeypatch.setattr("fleet_memory.retrieval.search", stand_in_search, raising=False)

    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    memory_module.configure_memory_project(tmp_path)
    config = memory_module._load_fleet_config_from_env()
    config.enabled = True
    client = memory_module.FleetMemoryClient(config)
    client._read_available = True
    client._store = _StandInStore()

    await client.search(query="anything", group_ids=["task_outcomes"])
    assert asked["project"] == "widget_shop"


async def test_the_declared_name_is_what_the_write_carries(memory_module, monkeypatch, tmp_path):
    """End of the write path: the record's own name is the project's own."""
    pytest.importorskip("nats_core.events")
    published: list = []

    class _Summary:
        published = 1
        skipped_oversized = 0

    async def stand_in_publish(episodes):
        published.extend(episodes)
        return _Summary()

    monkeypatch.setattr(
        "guardkit.memory.harvest_publisher.publish_episodes", stand_in_publish
    )

    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    memory_module.configure_memory_project(tmp_path)
    config = memory_module._load_fleet_config_from_env()
    config.enabled = True
    client = memory_module.FleetMemoryClient(config)
    client._nats_available = True

    key = await client.add_episode(
        name="OUT: TASK-1",
        episode_body=json.dumps({"task_id": "TASK-1", "success": True}),
        group_id="task_outcomes",
    )
    assert key == "build_outcome:widget_shop:TASK_1"
    assert published[0].project_id == "widget_shop"


def test_used_by_hand_the_current_folder_answers(memory_module, monkeypatch, tmp_path):
    """Nobody handed a name over and nothing configured a build: read here."""
    _declare(tmp_path, "memory:\n  project: widget_shop\n")
    monkeypatch.chdir(tmp_path)
    assert memory_module.memory_project_resolution().project == "widget_shop"


def test_guardkits_own_repository_answers_by_declaration(memory_module):
    """GuardKit is not a special case: it declares its name like anyone else."""
    from pathlib import Path

    import guardkit

    repo_root = Path(guardkit.__file__).resolve().parent.parent
    answer = resolve_memory_project(repo_root, env={})
    assert answer.project == "guardkit"
    assert answer.source == "declaration"


class TestOneAnswerPerBuild:
    """Settling the name twice for the same folder is a restatement, not a reset.

    Every orchestrator in a parallel wave calls ``configure_memory_project`` on
    its way up, in its own thread, against the same folder. Discarding the shared
    client and factory on each of those calls only rebuilt them under the same
    name, and left a window where another thread could pick up a half-replaced
    one. A different answer still drops everything built under the old one.
    """

    def test_the_same_answer_again_keeps_what_was_built(self, memory_module, tmp_path):
        _declare(tmp_path, "memory:\n  project: widget_shop\n")
        memory_module.configure_memory_project(tmp_path)

        sentinel = object()
        memory_module._memory_client = sentinel
        memory_module._backend_initialized = True

        again = memory_module.configure_memory_project(tmp_path)

        assert again.project == "widget_shop"
        assert memory_module._memory_client is sentinel
        assert memory_module._backend_initialized is True

    def test_a_different_answer_drops_what_was_built(self, memory_module, tmp_path):
        first = tmp_path / "first"
        second = tmp_path / "second"
        _declare(first, "memory:\n  project: widget_shop\n")
        _declare(second, "memory:\n  project: other_shop\n")

        memory_module.configure_memory_project(first)
        memory_module._memory_client = object()
        memory_module._backend_initialized = True

        moved = memory_module.configure_memory_project(second)

        assert moved.project == "other_shop"
        assert memory_module._memory_client is None
        assert memory_module._memory_factory is None
        assert memory_module._backend_initialized is False

    def test_every_wave_thread_settles_the_same_answer_without_tearing(
        self, memory_module, tmp_path
    ):
        """Sixteen threads settle it at once, as a parallel wave does."""
        _declare(tmp_path, "memory:\n  project: widget_shop\n")

        answers: list = []
        barrier = threading.Barrier(16)

        def settle() -> None:
            barrier.wait()
            answers.append(memory_module.configure_memory_project(tmp_path))

        threads = [threading.Thread(target=settle) for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(answers) == 16
        assert {answer.project for answer in answers} == {"widget_shop"}
        assert memory_module.memory_project_resolution().project == "widget_shop"


class TestTheSettledAnswerDoesNotOutliveItsTest:
    """The suite must not depend on the order its files happen to run in.

    ``configure_memory_project`` keeps its answer in a module global, which is
    right for a process that is one build and wrong for a test run that is
    hundreds. ``tests/conftest.py`` forgets the answer around every test. These
    two run in file order: the first settles a name for a throwaway folder, the
    second proves it did not inherit it.
    """

    def test_a_settles_a_name_for_its_own_folder(self, tmp_path):
        import guardkit.knowledge.fleet_memory_client as fmc

        _declare(tmp_path, "memory:\n  project: leaky_shop\n")
        assert fmc.configure_memory_project(tmp_path).project == "leaky_shop"

    def test_b_starts_with_nothing_settled(self):
        import guardkit.knowledge.fleet_memory_client as fmc

        assert fmc._memory_project_resolution is None


# ===========================================================================
# A failure to settle the name must not keep the previous project's memory
# (Codex, 22 September 2026).
# ===========================================================================


def test_a_failed_resolution_discards_the_previous_projects_memory(
    memory_module, tmp_path, monkeypatch, caplog
):
    """Two projects in one process; the second's name cannot be settled.

    Before the fix, ``configure_memory_project`` raised before it reached the
    discard, so the client and factory built for the FIRST project survived,
    and the second project's reads and outcome writes went under the first's
    name. Now a failure is itself the answer "memory off", settled through the
    same path, and nothing built earlier survives it.
    """
    first = tmp_path / "first"
    second = tmp_path / "second"
    _declare(first, "memory:\n  project: first_project\n")
    _declare(second, "memory:\n  project: second_project\n")

    answer = memory_module.configure_memory_project(first)
    assert answer.project == "first_project"
    memory_module.init_memory_client(
        fleet_config=memory_module.FleetMemoryConfig(enabled=True, project="first_project")
    )
    assert memory_module._memory_client is not None
    assert memory_module._memory_client.config.project == "first_project"
    memory_module._memory_factory = object()  # anything cached for the first project

    def blow_up(*args, **kwargs):
        raise RecursionError("maximum recursion depth exceeded while parsing settings")

    monkeypatch.setattr(memory_module, "resolve_memory_project", blow_up)

    with caplog.at_level("WARNING"):
        answer = memory_module.configure_memory_project(second)

    assert answer.project is None
    assert answer.source == "failed"
    assert "memory: OFF" in caplog.text and "RecursionError" in caplog.text
    # Nothing of the first project survives: no client, no factory, and the
    # shared configuration now carries no name at all.
    assert memory_module._memory_client is None
    assert memory_module._memory_factory is None
    assert memory_module._backend_initialized is False
    assert memory_module.memory_project_resolution().project is None
    assert memory_module._load_fleet_config_from_env().project is None
    # And a client asked for now is refused, so neither a read nor an outcome
    # write can be filed under "first_project".
    assert memory_module.get_memory_client() is None
    factory = memory_module.get_memory_factory()
    assert factory is None or factory.get_thread_client() is None
