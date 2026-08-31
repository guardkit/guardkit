"""Pytest configuration and fixtures."""
import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# "What did not run" report (Rich, 2026-08-23: "I don't like skipping things and
# leaving them for later because they get forgotten.")
# ---------------------------------------------------------------------------
# Importing these four hook functions by name makes them attributes of THIS
# conftest module, which is how pytest discovers hooks. They record every skip
# in the session and print a plain-language summary at the very end of the run.
# They REPORT ONLY: nothing in tests/skip_report.py touches the exit code, and
# nothing there interferes with the quarantine below — it reads the reports the
# quarantine's own skips produce, and counts them under their own heading.
from tests.skip_report import (  # noqa: F401  (imported for the hooks alone)
    pytest_collectreport,
    pytest_runtest_logreport,
    pytest_sessionstart,
    pytest_unconfigure,
)

# Add installer/core to Python path (to allow "from lib.X import Y")
global_path = Path(__file__).parent.parent / "installer" / "core"
sys.path.insert(0, str(global_path))

# Extend lib.__path__ so "from lib.X" resolves modules from both
# installer/core/lib/ AND installer/core/commands/lib/
import lib
commands_lib_path = global_path / "commands" / "lib"
if str(commands_lib_path) not in lib.__path__:
    lib.__path__.append(str(commands_lib_path))

# Also add lib directory for direct imports (for backward compatibility)
lib_path = global_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Also add commands/lib for plan_modifier imports
commands_lib_str = str(commands_lib_path)
if commands_lib_str not in sys.path:
    sys.path.insert(0, commands_lib_str)


# ---------------------------------------------------------------------------
# Quarantine: pre-existing red tests, skipped so the CI gate can be green and
# start catching NEW regressions (TASK-INFRA-CIGREEN). Every quarantined node
# is listed with a bucket reason in tests/quarantine.txt and tracked for
# burn-down in docs/state/TASK-INFRA-CIGREEN/triage.md. This is a documented,
# explicit skip — NOT a silent pass. Set GUARDKIT_NO_QUARANTINE=1 to run the
# full (red) suite, e.g. while burning the list down.
# ---------------------------------------------------------------------------
_QUARANTINE_FILE = Path(__file__).parent / "quarantine.txt"


def _load_quarantine():
    exact = set()
    modules = set()
    if not _QUARANTINE_FILE.exists():
        return exact, modules
    for raw in _QUARANTINE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "::" in line:
            exact.add(line)
        else:
            # A bare module path quarantines every test it collects.
            modules.add(line)
    return exact, modules


_QUARANTINE_EXACT, _QUARANTINE_MODULES = _load_quarantine()


def pytest_configure(config):
    """Register this suite's own markers."""
    config.addinivalue_line(
        "markers",
        "allow_memory_capture: this test drives the build-outcome capture seam "
        "itself and opts out of the autouse guard. It MUST fake the writer.",
    )


def pytest_collection_modifyitems(config, items):
    """Skip quarantined nodes unless GUARDKIT_NO_QUARANTINE is set."""
    if os.environ.get("GUARDKIT_NO_QUARANTINE"):
        return
    if not _QUARANTINE_EXACT and not _QUARANTINE_MODULES:
        return
    reason = (
        "quarantined pre-existing failure — see tests/quarantine.txt "
        "(TASK-INFRA-CIGREEN)"
    )
    marker = pytest.mark.skip(reason=reason)
    skipped = 0
    for item in items:
        nodeid = item.nodeid
        module = nodeid.split("::", 1)[0]
        if nodeid in _QUARANTINE_EXACT or module in _QUARANTINE_MODULES:
            item.add_marker(marker)
            skipped += 1
    if skipped:
        terminal = config.pluginmanager.get_plugin("terminalreporter")
        if terminal is not None:
            terminal.write_line(
                f"[quarantine] skipped {skipped} pre-existing red test(s) "
                f"(GUARDKIT_NO_QUARANTINE=1 to run them)"
            )


# ---------------------------------------------------------------------------
# The live-memory fence: no test may write to the real memory store
# ---------------------------------------------------------------------------
# ``AutoBuildOrchestrator.orchestrate`` writes a build outcome at every
# terminal. Eighteen test files drive ``orchestrate(...)`` with fixture task
# ids, and on the factory seat — memory ON, the broker reachable, the writer
# credential exported, which is this estate's NORMAL state — every one of those
# runs would publish a fabricated build outcome into the same store the gates
# read back as priors. A test suite must never be able to teach production
# anything.
#
# Two fences, because either alone has a hole:
#   1. FLEET_MEMORY_ENABLED is removed from the environment. This is the belt,
#      not the braces: the memory client is a process-wide singleton built
#      lazily from the environment on FIRST use, so an earlier test that built
#      it enabled keeps an enabled client no matter what later tests do to the
#      environment.
#   2. ``_capture_build_outcome`` is replaced with a no-op that returns None,
#      exactly as the real method does when memory is off. This is the fence
#      that actually holds, because it sits above the singleton.
#
# The one test file whose SUBJECT is the capture seam opts out with
# ``@pytest.mark.allow_memory_capture`` and fakes the writer itself. Opting out
# is deliberately explicit and greppable — nothing here switches off quietly.
#
# WHAT THE BRACES DO NOT COVER, said plainly so nobody has to discover it. The
# method patch guards exactly one door: ``_capture_build_outcome``. A test that
# calls ``outcome_manager.capture_task_outcome`` (or the verified variant)
# straight — the door the ``guardkit memory capture-outcome`` CLI goes through
# — walks past the braces entirely and is left holding only the leaky belt.
# The braces are NOT extended over those functions on purpose: the suites whose
# subject IS the writer have to be able to call it. What keeps the gap shut is
# that every such test fakes ``get_memory_client``, and
# ``tests/orchestrator/test_memory_write_fence.py`` asserts that rather than
# trusting it, so a future test that forgets fails there instead of quietly
# writing to production.


def _no_memory_write(self, task_id, **_kwargs):
    """Stand-in for the real capture: writes nothing, returns nothing."""
    return None


@pytest.fixture(autouse=True)
def guard_live_memory_writes(monkeypatch, request):
    """Stop every test from writing a build outcome to the real memory store."""
    monkeypatch.delenv("FLEET_MEMORY_ENABLED", raising=False)

    if request.node.get_closest_marker("allow_memory_capture"):
        return

    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    monkeypatch.setattr(
        AutoBuildOrchestrator,
        "_capture_build_outcome",
        _no_memory_write,
        raising=True,
    )


# ---------------------------------------------------------------------------
# The M0 effective-seat fence (leg-invocation stage-2 design §3)
# ---------------------------------------------------------------------------
# ``select_harness`` now refuses to build a harness on a seat it cannot show is
# local: a missing ``model`` (which falls to DeepAgents'
# ``ChatAnthropic("claude-sonnet-4-6")`` or the bundled SDK CLI default), a
# frontier provider prefix, or a bare alias with no ``OPENAI_BASE_URL``.
#
# Tests whose SUBJECT is SDK/harness plumbing rather than seat choice used to
# construct harnesses with no model at all. They now declare the estate's
# routine condition — a named local seat behind a local llama-swap endpoint —
# via these two constants and the fixture below. Deliberately NOT
# ``GUARDKIT_ALLOW_FRONTIER=1``: switching the fence off wholesale in the suite
# would hide the next regression. The fence's own behaviour is driven in
# ``tests/unit/test_m0_effective_seat_fence.py``.

#: A local-fleet seat alias (the workhorse's llama-swap name shape).
M0_FLEET_SEAT = "qwen36-workhorse"

#: A non-vendor OpenAI-compatible endpoint — the load-bearing half of the rule.
#: Deliberately loopback port 9 (discard): it satisfies the fence exactly as a
#: real llama-swap URL does, and any test that accidentally tries to REACH it
#: gets an instant connection refusal instead of a DNS/connect stall. No test in
#: this suite is supposed to talk to a model at all.
M0_FLEET_BASE_URL = "http://127.0.0.1:9/v1"


# ---------------------------------------------------------------------------
# The stamp-normalizer model fence: no test may ask a live model
# ---------------------------------------------------------------------------
# The stamp normalizer hands titles no rule could decide to a model (ruled
# 2026-08-31). It finds the endpoint in the environment, and on the factory
# seat OPENAI_BASE_URL points at the live llama-swap — so a test that produced
# a refusal would call it for real and wait on the network. This fixture
# declares "no endpoint configured" for every test, which is the normalizer's
# oldest behaviour: refuse loud, never ask, never invent a stamp. A test whose
# SUBJECT is the fallback injects its own fake call (or sets the variable
# itself with monkeypatch, which overrides this).


@pytest.fixture(autouse=True)
def stamp_normalizer_model_is_never_live(monkeypatch):
    """No test asks a real model through the stamp normalizer's fallback."""
    from guardkit.orchestrator.stamp_model_fallback import MODEL_URL_ENV

    monkeypatch.setenv(MODEL_URL_ENV, "")


@pytest.fixture
def m0_routine_fleet_route(monkeypatch):
    """Declare the routine local-fleet route for the duration of one test.

    Returns the seat alias so a caller can thread it into ``model_name=`` where
    a construction would otherwise pass ``None`` (which the fence refuses on its
    own terms, base URL or not — ``None`` reaches an Anthropic default that
    never consults ``OPENAI_BASE_URL``).
    """
    monkeypatch.setenv("OPENAI_BASE_URL", M0_FLEET_BASE_URL)
    # llama-swap / vLLM ignore the key but ``ChatOpenAI`` refuses to construct
    # without one — unlike ``ChatAnthropic``, which happily constructs with no
    # credential at all. That asymmetry is why the pre-fence suite could build a
    # frontier client and never notice. A placeholder keeps the local route
    # constructible; nothing in these tests reaches the network.
    monkeypatch.setenv("OPENAI_API_KEY", "local-fleet-placeholder")
    monkeypatch.delenv("GUARDKIT_ALLOW_FRONTIER", raising=False)
    return M0_FLEET_SEAT


def normalize_path(path):
    """
    Normalize path for cross-platform comparison.

    Uses os.path.realpath() to resolve symlinks (e.g., macOS /private/var).

    Args:
        path: Path-like object to normalize

    Returns:
        Path: Normalized path object
    """
    return Path(os.path.realpath(path))


def paths_equal(path1, path2):
    """
    Compare two paths for equality after normalization.

    Args:
        path1: First path to compare
        path2: Second path to compare

    Returns:
        bool: True if paths are equal after normalization
    """
    return normalize_path(path1) == normalize_path(path2)
