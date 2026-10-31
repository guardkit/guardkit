"""Pytest configuration and fixtures."""
import os
import re
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
    config.addinivalue_line(
        "markers",
        "real_project_scratch: this test checks what happens to a project "
        "command whose work folder is not a git checkout, so it opts out of "
        "the scratch folder the suite gives plain temporary folders.",
    )
    config.addinivalue_line(
        "markers",
        "security_scanners: this test lets the security check find Gitleaks on "
        "PATH (or its own stub); every other test does not.",
    )
    config.addinivalue_line(
        "markers",
        "personal_run: this test is a person's own run of GuardKit, not a "
        "factory launch, so GUARDKIT_FACTORY_LAUNCH is cleared for it (the "
        "sdk harness, the by-hand memory rule). Every other test runs as a "
        "factory launch. It never lifts the network and claude guard.",
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
# Tests run as a FACTORY launch, and never reach a hosted model (19 Oct 2026)
# ---------------------------------------------------------------------------
# The frontier-model fence (guardkit/orchestrator/m0_fence.py) applies to
# factory launches only since 19 October 2026: a person's own run is not
# fenced. A test process is not a factory launch, so without the fixture below
# every test that the fence used to stop would now go further — and could
# build a real hosted-model client. Two safeguards:
#
#   1. Every test runs as a factory launch (GUARDKIT_FACTORY_LAUNCH=1), the
#      strict rule. A test whose subject is a person's own run says so with
#      ``@pytest.mark.personal_run`` (greppable, never quiet).
#   2. A guard that stays on for the whole session: a connection to anything
#      but this machine, or a start of the ``claude`` program (other than a
#      ``--version`` probe), is refused where it happens and fails the test
#      that made it. Starts are checked in ``subprocess.Popen`` (argument lists,
#      ``shell=True`` strings and ``executable=``), ``asyncio``'s exec and
#      shell, ``os.system`` and ``os.posix_spawn``/``posix_spawnp``, all by
#      one decision: a SHELL launch that contains ``claude`` as a word of its
#      own (``.claude`` folders and ``claude_agent_sdk`` are not) is always
#      refused; an argument list that contains it is refused unless it is,
#      element by element, ``claude --version``, ``claude -v`` (``claude`` or
#      a plain absolute path ending in ``/claude``), ``which claude`` or
#      ``command -v claude``. Not covered: ``os.exec*``
#      (it would replace the test process) and the legacy ``os.spawn*``
#      family; nothing in the suite uses either. It does not rely on product
#      code letting the refusal
#      through, because never-raises chains swallow exceptions.

import asyncio as _guard_asyncio
import functools as _guard_functools
import ipaddress as _guard_ipaddress
import socket as _guard_socket
import subprocess as _guard_subprocess
import threading as _guard_threading

_LAUNCH_GUARD_HITS: list = []
_LAUNCH_GUARD_LOCK = _guard_threading.Lock()


def _launch_guard_hit(what: str) -> None:
    with _LAUNCH_GUARD_LOCK:
        _LAUNCH_GUARD_HITS.append(what)


def _launch_guard_is_this_machine(address) -> bool:
    host = address[0] if isinstance(address, tuple) else address
    if not isinstance(host, str):
        return True  # an abstract or bytes unix-socket address
    if host in ("localhost", ""):
        return True
    try:
        ip = _guard_ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False  # a host NAME: refused, it could be anywhere
    return ip.is_loopback or ip.is_unspecified


#: The ``claude`` word (Codex review rounds 4 and 5). It is bounded by the
#: start or end, whitespace, shell punctuation, a quote, ``=``, ``,``, ``#``
#: or, before it only, a path separator. ``.``, ``-`` and ``_`` do NOT bound
#: it, so the ``.claude`` folder (GuardKit's own git calls exclude
#: ``**/.claude/task-plans/**``), ``claude_agent_sdk``, ``claude-agent`` and a
#: ``/tmp/claude-1000`` folder are not ``claude``; nor is a FOLDER named
#: ``claude`` inside a path (an existing test keeps notes in
#: ``config/claude/``). ``/x/claude``, ``$(claude …)`` and ``echo ok;claude``
#: are.
_LAUNCH_GUARD_BOUND = r"""[\s;&|()`'"$<>{}=,!#]"""
_LAUNCH_GUARD_CLAUDE_WORD = re.compile(
    rf"(?:^|(?<={_LAUNCH_GUARD_BOUND})|(?<=[/\\]))claude(?:\.exe)?(?=$|{_LAUNCH_GUARD_BOUND})",
    re.IGNORECASE,
)
#: Characters that may not appear in an absolute ``claude`` path in an
#: allowed argument list.
_LAUNCH_GUARD_UNSAFE_PATH = re.compile(r"""[\s;&|`$<>()'"\\*?!{}#=,]""")


def _launch_guard_harmless_argv(words) -> bool:
    """The only argument lists that may name ``claude``, matched element by element."""
    if words in (["which", "claude"], ["command", "-v", "claude"]):
        return True
    if len(words) != 2 or words[1] not in ("--version", "-v"):
        return False
    program = words[0]
    if program == "claude":
        return True
    return (
        program.startswith("/")
        and not _LAUNCH_GUARD_UNSAFE_PATH.search(program)
        and program.rsplit("/", 1)[-1] == "claude"
    )


def _launch_guard_program_is_claude(program) -> bool:
    """Is this program (an ``executable=``, say) the ``claude`` program?"""
    name = os.path.basename(os.fsdecode(program)).lower()
    return name in ("claude", "claude.exe")


def _launch_guard_is_claude(launch, *, shell: bool = False) -> bool:
    """Could this launch start ``claude``? The one decision, for every entry point.

    * A SHELL launch — a string (``os.system``, ``shell=True``, asyncio's
      shell), or a list run with ``shell=True`` — is refused whenever it
      contains the ``claude`` word. No exceptions (Codex review round 5: an
      allowlist read through shell syntax let ``which\nclaude`` through).
    * An ARGUMENT LIST that contains the word (joined with spaces, so an
      ``sh -c`` script inside it counts) is refused unless it is, element by
      element, ``[claude, --version]``, ``[claude, -v]`` (``claude`` or a
      plain absolute path ending in ``/claude``), ``[which, claude]`` or
      ``[command, -v, claude]``.
    """
    if isinstance(launch, (str, bytes)):
        return bool(_LAUNCH_GUARD_CLAUDE_WORD.search(os.fsdecode(launch)))
    words = [os.fsdecode(part) if isinstance(part, (str, bytes)) else str(part) for part in launch]
    if not _LAUNCH_GUARD_CLAUDE_WORD.search(" ".join(words)):
        return False
    if shell:
        return True
    return not _launch_guard_harmless_argv(words)


def _install_launch_guard() -> None:
    socket_class = _guard_socket.socket
    original_connect = socket_class.connect
    original_connect_ex = socket_class.connect_ex

    @_guard_functools.wraps(original_connect)
    def connect(self, address):
        if self.family in (_guard_socket.AF_INET, _guard_socket.AF_INET6) and not (
            _launch_guard_is_this_machine(address)
        ):
            _launch_guard_hit(f"network connection to {address!r}")
            raise ConnectionRefusedError(
                f"test guard: a connection to {address!r} was refused"
            )
        return original_connect(self, address)

    @_guard_functools.wraps(original_connect_ex)
    def connect_ex(self, address):
        if self.family in (_guard_socket.AF_INET, _guard_socket.AF_INET6) and not (
            _launch_guard_is_this_machine(address)
        ):
            _launch_guard_hit(f"network connection to {address!r}")
            return 111  # ECONNREFUSED
        return original_connect_ex(self, address)

    socket_class.connect = connect
    socket_class.connect_ex = connect_ex

    popen_init = _guard_subprocess.Popen.__init__

    @_guard_functools.wraps(popen_init)
    def guarded_popen_init(self, args, *rest, **kwargs):
        executable = kwargs.get("executable")
        shell = bool(kwargs.get("shell"))
        if shell or isinstance(args, (str, bytes)):
            launch = [args] if isinstance(args, (str, bytes)) else list(args)
            # Judged as the shell string AND as the program that runs it
            # (Codex review round 6: ``Popen("x", executable=".../claude")``).
            refused = _launch_guard_is_claude(launch, shell=True) or (
                executable is not None and _launch_guard_program_is_claude(executable)
            )
        else:
            launch = list(args)
            if executable is not None:
                launch = [executable, *launch[1:]]  # what Popen actually runs
            refused = _launch_guard_is_claude(launch)
        if refused:
            _launch_guard_hit(f"start of claude: {args!r}"[:300])
            raise PermissionError("test guard: starting claude was refused")
        return popen_init(self, args, *rest, **kwargs)

    _guard_subprocess.Popen.__init__ = guarded_popen_init

    create_exec = _guard_asyncio.create_subprocess_exec

    @_guard_functools.wraps(create_exec)
    async def guarded_create_exec(program, *args, **kwargs):
        if _launch_guard_is_claude([program, *args]):
            _launch_guard_hit(f"start of claude: {[program, *args]!r}"[:300])
            raise PermissionError("test guard: starting claude was refused")
        return await create_exec(program, *args, **kwargs)

    _guard_asyncio.create_subprocess_exec = guarded_create_exec

    create_shell = _guard_asyncio.create_subprocess_shell

    @_guard_functools.wraps(create_shell)
    async def guarded_create_shell(cmd, *args, **kwargs):
        if _launch_guard_is_claude(cmd):
            _launch_guard_hit(f"start of claude: {cmd!r}"[:300])
            raise PermissionError("test guard: starting claude was refused")
        return await create_shell(cmd, *args, **kwargs)

    _guard_asyncio.create_subprocess_shell = guarded_create_shell

    os_system = os.system

    @_guard_functools.wraps(os_system)
    def guarded_system(command):
        if _launch_guard_is_claude(command):
            _launch_guard_hit(f"start of claude: {command!r}"[:300])
            raise PermissionError("test guard: starting claude was refused")
        return os_system(command)

    os.system = guarded_system

    for spawn_name in ("posix_spawn", "posix_spawnp"):
        original_spawn = getattr(os, spawn_name, None)
        if original_spawn is None:
            continue

        def make_guarded_spawn(original):
            @_guard_functools.wraps(original)
            def guarded_spawn(path, argv, *rest, **kwargs):
                if _launch_guard_is_claude([path, *list(argv)[1:]]):
                    _launch_guard_hit(f"start of claude: {path!r} {list(argv)!r}"[:300])
                    raise PermissionError("test guard: starting claude was refused")
                return original(path, argv, *rest, **kwargs)

            return guarded_spawn

        setattr(os, spawn_name, make_guarded_spawn(original_spawn))


_install_launch_guard()


# The second, independent layer (Codex review round 6): a ``claude`` stub first
# on PATH for the whole session. Anything that finds ``claude`` by PATH lookup,
# through an API or a wrapper the guard above does not see, runs the stub, not
# the real program. The stub answers a bare ``--version`` or ``-v`` (the
# presence probes the suite makes) and exits 0; anything else is recorded in a
# marker file and exits 97, and the session then fails with a plain message.
import shutil as _stub_shutil
import tempfile as _stub_tempfile

_CLAUDE_STUB_DIR = _stub_tempfile.mkdtemp(prefix="guardkit-tests-claude-stub-")
_CLAUDE_STUB_MARKER = os.path.join(_CLAUDE_STUB_DIR, "claude-was-run.log")
_CLAUDE_STUB = os.path.join(_CLAUDE_STUB_DIR, "claude")
with open(_CLAUDE_STUB, "w", encoding="utf-8") as _stub_file:
    _stub_file.write(
        "#!/bin/sh\n"
        "# GuardKit test-suite stand-in for the claude program (tests/conftest.py).\n"
        'if [ "$#" -eq 1 ] && { [ "$1" = "--version" ] || [ "$1" = "-v" ]; }; then\n'
        '  echo "0.0.0 (GuardKit test stand-in, not Claude Code)"\n'
        "  exit 0\n"
        "fi\n"
        f'printf "%s\\n" "claude $*" >> "{_CLAUDE_STUB_MARKER}"\n'
        "exit 97\n"
    )
os.chmod(_CLAUDE_STUB, 0o755)
os.environ["PATH"] = _CLAUDE_STUB_DIR + os.pathsep + os.environ.get("PATH", "")


def _claude_stub_runs() -> list:
    """Every call the stand-in recorded (empty when nothing reached it)."""
    try:
        with open(_CLAUDE_STUB_MARKER, encoding="utf-8") as marker:
            return [line.rstrip("\n") for line in marker if line.strip()]
    except FileNotFoundError:
        return []


def pytest_sessionfinish(session, exitstatus):
    """Fail the session if anything ran the claude stand-in for real work."""
    runs = _claude_stub_runs()
    _stub_shutil.rmtree(_CLAUDE_STUB_DIR, ignore_errors=True)
    if not runs:
        return
    message = (
        f"\nTEST SUITE FAILED: something started claude {len(runs)} time(s) by "
        "looking it up on PATH. The session's stand-in caught it, so the real "
        "program did not run, but the guard in tests/conftest.py missed it. "
        "First: " + "; ".join(runs[:3]) + "\n"
    )
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(message)
    else:
        sys.stderr.write(message)
    session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture(autouse=True)
def tests_run_as_a_factory_launch(monkeypatch, request):
    """Every test is a factory launch unless it is marked ``personal_run``."""
    from guardkit.orchestrator.m0_fence import FACTORY_LAUNCH_ENV

    if request.node.get_closest_marker("personal_run"):
        monkeypatch.delenv(FACTORY_LAUNCH_ENV, raising=False)
    else:
        monkeypatch.setenv(FACTORY_LAUNCH_ENV, "1")


@pytest.fixture(autouse=True)
def no_test_reaches_a_hosted_model():
    """Fail the test that tried to leave this machine or start ``claude``."""
    with _LAUNCH_GUARD_LOCK:
        start = len(_LAUNCH_GUARD_HITS)
    yield
    with _LAUNCH_GUARD_LOCK:
        hits = _LAUNCH_GUARD_HITS[start:]
    if hits:
        pytest.fail(
            "this test tried to reach beyond this machine or start claude "
            "(refused): " + "; ".join(hits[:5]),
            pytrace=False,
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
# One settled memory name per PROCESS is right; one per TEST RUN is not
# ---------------------------------------------------------------------------
# ``configure_memory_project`` settles which memory a build uses and keeps the
# answer in a module global, on purpose: in a real run the process is one build,
# and the builder thread and the reviewer thread must not end up under different
# names. A test run is not one build. Every ``AutoBuildOrchestrator(...)`` a test
# constructs settles the answer for whatever temporary folder that test made, and
# without this fixture the answer outlived the test: a later test that asked
# ``memory_project_resolution()`` — the CLI's search command, the config loader —
# got the previous test's folder, so the suite's result depended on the order the
# files happened to run in. Forgetting the answer between tests puts each test
# back on the same footing as the first one.


@pytest.fixture(autouse=True)
def forget_settled_memory_project():
    """Each test settles the memory name for itself, never inherits one."""
    from guardkit.knowledge import fleet_memory_client as _fmc

    _fmc.reset_memory_project()
    try:
        yield
    finally:
        _fmc.reset_memory_project()


# ---------------------------------------------------------------------------
# No test writes the memory query log into this repository (16 October 2026)
# ---------------------------------------------------------------------------
# ``query_logger.log_query`` appends to ``<current folder>/.guardkit/
# memory-query-log.jsonl`` unless it is given a folder. pytest runs from the
# repository root, so every test that drove ``FleetMemoryClient.search`` (or the
# feature-plan context) without patching the log path appended lines to the
# repository's own copy — four per full run, measured 16 October. Several test
# files already redirected it themselves; others did not, and the next one to
# forget would do it again. So the redirect lives here, for every test: a
# default log path that would land inside this repository goes to a temporary
# folder instead. A test that chooses a folder, or changes into a temporary
# folder first, keeps exactly the behaviour it asked for.

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def memory_query_log_stays_out_of_the_repository(monkeypatch, tmp_path_factory):
    """Send a default-located memory query log outside the repository."""
    from guardkit.knowledge import query_logger as _ql

    original = _ql._get_log_path

    def _get_log_path(base_dir=None):
        if base_dir is None:
            here = Path.cwd().resolve()
            if here == _REPO_ROOT or _REPO_ROOT in here.parents:
                base_dir = str(tmp_path_factory.getbasetemp() / "memory-query-log")
        return original(base_dir)

    monkeypatch.setattr(_ql, "_get_log_path", _get_log_path)


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


# ---------------------------------------------------------------------------
# The run-evidence Docker fence: no test reads a real daemon's events
# ---------------------------------------------------------------------------
# Every declared command GuardKit runs now records the container events of its
# own interval when a Docker command-line tool is on PATH (repair 7,
# ``guardkit.orchestrator.run_evidence``). On a developer machine or the
# factory host that would make every test that runs a check ask the real
# daemon. This switches the query off for every test (the record then says it
# was switched off, never "no events"). A test whose SUBJECT is the Docker
# capture injects its own fake probe, which this switch does not touch.


@pytest.fixture(autouse=True)
def run_evidence_never_reads_real_docker(monkeypatch):
    """No test asks a real Docker daemon for events.

    A test that blocks evidence I/O leaves the capture's worker thread
    behind (by design). After the test releases it, the worker finishes its
    phase; it is waited for HERE, before this test's patches and this switch
    are undone, so it can never run against the real environment afterwards.
    """
    from guardkit.orchestrator.run_evidence import DOCKER_SWITCH_ENV

    import threading

    monkeypatch.setenv(DOCKER_SWITCH_ENV, "0")
    already_running = set(threading.enumerate())
    yield
    settle_evidence_threads(exclude=already_running)


def settle_evidence_threads(timeout: float = 20.0, exclude=frozenset()) -> None:
    """Wait for the evidence worker threads a test left running to finish."""
    import threading
    import time

    give_up_at = time.monotonic() + timeout
    for thread in threading.enumerate():
        if thread in exclude or not thread.name.startswith("guardkit-evidence"):
            continue
        thread.join(timeout=max(0.0, give_up_at - time.monotonic()))


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


# ---------------------------------------------------------------------------
# A scratch folder for project commands run in plain temporary folders
# ---------------------------------------------------------------------------
# Since 13 October 2026 every project command GuardKit runs gets an
# environment built from nothing (``project_command_env``), with a private
# HOME and TMPDIR in the work folder's scratch folder, which lives in the
# work folder's own git directory. In a build the work folder is always a git
# worktree. Many tests here run a project command in a plain ``tmp_path`` that
# is not a git checkout; without help the command would not run at all. This
# fixture gives such a folder a scratch folder of its own OUTSIDE it (in the
# test's own temporary area), and only when the real lookup finds none, so a
# test in a real git checkout gets exactly the production behaviour. A test
# that checks the refusal itself is marked ``real_project_scratch``.


@pytest.fixture(autouse=True)
def project_scratch_for_plain_folders(monkeypatch, request, tmp_path_factory):
    if request.node.get_closest_marker("real_project_scratch"):
        return
    from guardkit.orchestrator import project_command_env

    real = project_command_env._scratch_folder
    holder = {}

    def _scratch(work_folder):
        found = real(work_folder)
        if found is not None:
            return found
        key = os.path.realpath(str(work_folder))
        if key not in holder:
            folder = tmp_path_factory.mktemp("project-scratch")
            os.chmod(folder, 0o700)
            holder[key] = folder
        return holder[key]

    monkeypatch.setattr(project_command_env, "_scratch_folder", _scratch)
    # The short per-worktree TMPDIR folders go under pytest's own base folder
    # (which pytest clears), not the real /tmp, so a run of the suite does not
    # leave one /tmp/gk-* folder per test. A test of the real place is marked
    # ``real_project_scratch``.
    monkeypatch.setattr(
        project_command_env,
        "SHORT_TMP_ROOT",
        str(tmp_path_factory.getbasetemp()),
    )


# ---------------------------------------------------------------------------
# Tests that stand in for subprocess.run still see project commands
# ---------------------------------------------------------------------------
# Since 13 October 2026 GuardKit runs a project's commands with
# ``process_group.run_project_command``: ``subprocess.run``'s arguments,
# results and exceptions, but in a process group of its own so a timeout ends
# everything the command started. Many tests here replace ``subprocess.run``
# with a fake to script a command's result; they test what GuardKit does with
# that result (its argv, env, classification), not how the process is
# started. While a test has replaced ``subprocess.run``, this fixture sends
# project commands to that replacement with exactly the arguments they had
# before. With ``subprocess.run`` untouched, the real group runner runs; the
# tests that check timeouts end every child use it.

_ORIGINAL_SUBPROCESS_RUN = __import__("subprocess").run


@pytest.fixture(autouse=True)
def project_commands_follow_a_replaced_subprocess_run(monkeypatch):
    import subprocess as _subprocess

    from guardkit.orchestrator import process_group

    real_runner = process_group.run_project_command

    def _runner(args, **kwargs):
        if _subprocess.run is not _ORIGINAL_SUBPROCESS_RUN:
            kwargs.pop("grace", None)
            return _subprocess.run(args, **kwargs)
        return real_runner(args, **kwargs)

    monkeypatch.setattr(process_group, "run_project_command", _runner)


# ---------------------------------------------------------------------------
# The per-change security check (17 October 2026)
# ---------------------------------------------------------------------------
# ``security_check.security_check_command`` adds the secrets check to every task
# whenever the switch is on and Gitleaks is on PATH. So the scanner is hidden from
# every test unless it carries the ``security_scanners`` marker.


@pytest.fixture(autouse=True)
def security_scanners_hidden_unless_asked(monkeypatch, request):
    if request.node.get_closest_marker("security_scanners"):
        # A test that asks for the scanners also gets the operator's switch, which
        # is off by default; the switch's own tests unset it themselves.
        monkeypatch.setenv("GUARDKIT_SECURITY_CHECK_BLOCKING", "1")
        return
    monkeypatch.delenv("GUARDKIT_SECURITY_CHECK_BLOCKING", raising=False)
    try:
        from guardkit.orchestrator import security_check
    except Exception:  # noqa: BLE001 -- a test without the package is unaffected
        return
    monkeypatch.setattr(security_check, "_find_tool", lambda _name: None)


# The task-start coverage check (19 October 2026)
_CHECKOUT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def checkout_isolated_python(tmp_path_factory) -> str:
    """An interpreter whose isolated (``-I``) import of ``guardkit`` is THIS checkout.

    The architecture and security checks run as ``<interpreter> -I -m ...``. ``-I``
    ignores PYTHONPATH and the current folder, so the command imports whichever
    guardkit the interpreter's own site-packages name. In a git worktree that is
    usually the MAIN checkout (an editable install), so a test would run the main
    checkout's code, or fail to find a module that exists only here. When that is
    the case, a small virtual environment is made whose site-packages name this
    checkout first, then the running interpreter's own site-packages (for the
    dependencies). Nothing outside the test's temporary folder is changed.
    """
    import site
    import subprocess
    import venv

    probe = subprocess.run(
        [sys.executable, "-I", "-c", "import guardkit; print(guardkit.__file__)"],
        capture_output=True, text=True, timeout=60)
    if probe.returncode == 0 and Path(probe.stdout.strip()).resolve().parents[1] == _CHECKOUT:
        return sys.executable
    root = tmp_path_factory.mktemp("checkout-python")
    venv.EnvBuilder(with_pip=False, symlinks=True).create(root)
    python = root / "bin" / "python"
    purelib = subprocess.run(
        [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        capture_output=True, text=True, check=True, timeout=60).stdout.strip()
    lines = [str(_CHECKOUT)]
    lines += [f"import site; site.addsitedir({p!r})" for p in site.getsitepackages()]
    Path(purelib, "zz_guardkit_checkout.pth").write_text("\n".join(lines) + "\n")
    check = subprocess.run(
        [str(python), "-I", "-c", "import guardkit; print(guardkit.__file__)"],
        capture_output=True, text=True, check=True, timeout=60)
    assert Path(check.stdout.strip()).resolve().parents[1] == _CHECKOUT, check.stdout
    return str(python)


@pytest.fixture
def checkout_python(monkeypatch, checkout_isolated_python) -> str:
    """Make the rule builders name the interpreter that imports this checkout."""
    monkeypatch.setattr(sys, "executable", checkout_isolated_python)
    return checkout_isolated_python
