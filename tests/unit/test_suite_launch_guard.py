"""The suite's own guard: no test leaves this machine or starts ``claude``.

Since 19 October 2026 the frontier-model fence applies to factory launches
only, so the suite no longer leans on it to stop a real call. ``tests/conftest.py``
installs a guard for the whole session; these tests prove it refuses what it
must and lets through what it must. Each test that trips the guard on purpose
removes its own record afterwards, so it is not failed for doing so.

These tests must stay harmless even if the guard is broken or removed: the
``claude`` they try to start is a path that does not exist (a broken guard then
fails the test with FileNotFoundError, and nothing starts), and the connection
goes to a documentation-only address (TEST-NET-3) with a one-second timeout.
On 19 October 2026 an earlier draft started the real ``claude`` on PATH when
the guard was switched off in a mutation check; never again.
"""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys

import pytest

from tests import conftest as suite


@pytest.fixture
def forget_my_own_hits():
    with suite._LAUNCH_GUARD_LOCK:
        start = len(suite._LAUNCH_GUARD_HITS)
    yield
    with suite._LAUNCH_GUARD_LOCK:
        mine = suite._LAUNCH_GUARD_HITS[start:]
        del suite._LAUNCH_GUARD_HITS[start:]
    assert mine, "the guard recorded nothing for a refused attempt"


@pytest.mark.parametrize(
    "address, local",
    [
        (("127.0.0.1", 80), True),
        (("::1", 80, 0, 0), True),
        (("localhost", 80), True),
        (("0.0.0.0", 80), True),
        (("10.0.0.5", 80), False),
        (("192.168.1.10", 80), False),
        (("160.79.104.10", 443), False),
        (("api.anthropic.com", 443), False),
    ],
)
def test_only_this_machine_counts_as_local(address, local):
    assert suite._launch_guard_is_this_machine(address) is local


@pytest.mark.parametrize(
    "argv, refused",
    [
        # SHELL strings (os.system, shell=True, asyncio's shell) that contain
        # the claude word are ALWAYS refused (Codex review round 5).
        ("which\nclaude", True),
        ("claude\n--version", True),
        ("claude;/usr/bin/claude --version", True),
        ("claude --version", True),
        ("claude -v", True),
        ("which claude", True),
        ("command -v claude", True),
        ("/usr/local/bin/claude --version", True),
        ("claude -p hi", True),
        ("cd /tmp; claude -p x", True),
        ("echo hi | claude -p x", True),
        ("FOO=1 claude -p x", True),
        ("echo ready # comment\nclaude -p hello", True),
        ("echo ready\r\nclaude -p hello", True),
        ("{ claude -p x; }", True),
        ("if true; then claude -p x; fi", True),
        ("echo $(claude -p x)", True),
        ("echo `claude -p x`", True),
        ("CLAUDE -p x", True),
        ("echo 'claude'", True),
        ("FOO=claude", True),
        ("echo ok;claude -p x", True),
        ("echo claude", True),
        ("C:\\tools\\claude.exe -p x", True),
        # ARGUMENT lists: refused when they contain the word, unless they are,
        # element by element, one of four forms
        (["env", "sh", "-c", "claude -p hello"], True),
        (["sh", "-c", "claude --version"], True),
        (["bash", "-c", "which claude"], True),
        (["claude;/usr/bin/claude", "--version"], True),
        (["claude\n", "--version"], True),
        (["/usr/bin/claude;x", "--version"], True),
        (["/usr/bin/cla ude/claude", "--version"], True),
        (["relative/claude", "--version"], True),
        (["claude.exe", "--version"], True),
        (["CLAUDE", "--version"], True),
        (["claude", "--version", ""], True),
        (["claude", "--Version"], True),
        (["which", "/usr/bin/claude"], True),
        (["which", "claude", "&&", "claude"], True),
        (["claude", "-p", "hello"], True),
        (["/usr/local/bin/claude", "--output-format", "stream-json"], True),
        (["env", "-u", "UNUSED_VAR", "claude", "-p", "hi"], True),
        (["nice", "-n", "5", "claude", "-p", "x"], True),
        (["timeout", "5", "claude", "-p", "x"], True),
        (["nohup", "claude"], True),
        (["grep", "claude", "notes.txt"], True),
        (["env", "claude", "--version"], True),
        (["claude"], True),
        (["/x/claude", "-p", "y"], True),
        # the four argument-list forms, allowed
        (["claude", "--version"], False),
        (["claude", "-v"], False),
        (["/usr/local/bin/claude", "--version"], False),
        (["/home/someone/.local/bin/claude", "-v"], False),
        (["which", "claude"], False),
        (["command", "-v", "claude"], False),
        # no claude word at all
        (["echo", "claude_agent_sdk"], False),
        ("echo claude_agent_sdk", False),
        (["git", "add", ".claude/settings.json"], False),
        (["git", "diff", ":(exclude,glob)**/.claude/task-plans/**"], False),
        (["claude-agent", "x"], False),
        ("ls /tmp/claude-1000/x", False),
        (["cat", "claude.json"], False),
        (["git", "add", "config/claude/CLAUDE.md"], False),
        ("ls claude/", False),
        (["git", "status"], False),
        ("echo ok", False),
    ],
)
def test_starting_claude_is_refused_but_a_version_probe_is_not(argv, refused):
    assert suite._launch_guard_is_claude(argv) is refused


def test_a_connection_beyond_this_machine_is_refused(forget_my_own_hits):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        with pytest.raises(ConnectionRefusedError, match="test guard"):
            sock.connect(("203.0.113.7", 443))
    finally:
        sock.close()


def test_connect_ex_beyond_this_machine_is_refused(forget_my_own_hits):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        assert sock.connect_ex(("203.0.113.7", 443)) != 0
    finally:
        sock.close()


def _absent_claude(tmp_path):
    """A ``claude`` that does not exist: harmless if the guard ever fails."""
    path = tmp_path / "no-such-dir" / "claude"
    assert not path.exists()
    return str(path)


def test_starting_claude_through_popen_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.Popen([_absent_claude(tmp_path), "-p", "guard check"])


def test_starting_claude_through_asyncio_is_refused(forget_my_own_hits, tmp_path):
    claude = _absent_claude(tmp_path)

    async def start():
        await asyncio.create_subprocess_exec(claude, "-p", "guard check")

    with pytest.raises(PermissionError, match="test guard"):
        asyncio.run(start())


def test_a_shell_string_starting_claude_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.run(f"{_absent_claude(tmp_path)} -p 'guard check'", shell=True)


def test_sh_dash_c_starting_claude_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.run(["sh", "-c", f"{_absent_claude(tmp_path)} -p 'guard check'"])


def test_an_executable_named_claude_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.Popen(["harmless", "-p", "guard check"], executable=_absent_claude(tmp_path))


def test_os_system_starting_claude_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        os.system(f"{_absent_claude(tmp_path)} -p 'guard check'")


@pytest.mark.parametrize("name", ["posix_spawn", "posix_spawnp"])
def test_posix_spawn_starting_claude_is_refused(forget_my_own_hits, tmp_path, name):
    claude = _absent_claude(tmp_path)
    with pytest.raises(PermissionError, match="test guard"):
        getattr(os, name)(claude, [claude, "-p", "guard check"], dict(os.environ))


def test_asyncio_shell_starting_claude_is_refused(forget_my_own_hits, tmp_path):
    claude = _absent_claude(tmp_path)

    async def start():
        await asyncio.create_subprocess_shell(f"{claude} -p 'guard check'")

    with pytest.raises(PermissionError, match="test guard"):
        asyncio.run(start())


def _multiline(claude):
    return f"echo ready # a comment\n{claude} -p 'guard check'"


def test_a_multiline_os_system_command_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        os.system(_multiline(_absent_claude(tmp_path)))


def test_a_multiline_shell_true_command_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.run(_multiline(_absent_claude(tmp_path)), shell=True)


def test_a_multiline_sh_dash_c_command_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.run(["sh", "-c", _multiline(_absent_claude(tmp_path))])


def test_a_multiline_asyncio_shell_command_is_refused(forget_my_own_hits, tmp_path):
    command = _multiline(_absent_claude(tmp_path))

    async def start():
        await asyncio.create_subprocess_shell(command)

    with pytest.raises(PermissionError, match="test guard"):
        asyncio.run(start())


def test_a_shell_true_list_naming_claude_is_refused(forget_my_own_hits, tmp_path):
    """A list run with shell=True is a shell launch: no exceptions."""
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.run([f"{_absent_claude(tmp_path)} --version"], shell=True)


def test_a_shell_true_list_gets_no_list_exception(forget_my_own_hits, tmp_path):
    """Even a list that would be harmless as an argument list is refused when
    it runs through a shell."""
    claude = _absent_claude(tmp_path)
    assert suite._launch_guard_is_claude(["claude", "--version"], shell=True) is True
    assert suite._launch_guard_is_claude([claude, "--version"]) is False
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.run([claude, "--version"], shell=True)


def test_an_executable_override_is_judged_as_what_runs(tmp_path):
    """Popen runs ``executable`` in place of the first element."""
    claude = _absent_claude(tmp_path)
    assert suite._launch_guard_is_claude([claude, "--version"]) is False
    with pytest.raises(FileNotFoundError):  # allowed by the guard; the path is absent
        subprocess.Popen(["anything", "--version"], executable=claude)


# ---------------------------------------------------------------------------
# executable= is judged on every launch form (Codex review round 6)
# ---------------------------------------------------------------------------


def test_a_string_launch_with_a_claude_executable_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.Popen("placeholder", executable=_absent_claude(tmp_path))


def test_a_shell_launch_with_a_claude_executable_is_refused(forget_my_own_hits, tmp_path):
    """Judged as the program that runs the string, not only as the string."""
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.Popen("echo ok", shell=True, executable=_absent_claude(tmp_path))


def test_a_list_with_a_claude_executable_is_refused(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.Popen(["placeholder", "-p", "guard check"], executable=_absent_claude(tmp_path))


def test_a_claude_executable_named_in_bytes_or_upper_case_is_refused(forget_my_own_hits, tmp_path):
    claude = _absent_claude(tmp_path)
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.Popen("placeholder", executable=os.fsencode(claude))
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.Popen("placeholder", executable=claude[: -len("claude")] + "CLAUDE")


def test_a_harmless_executable_with_a_shell_string_is_still_judged(forget_my_own_hits, tmp_path):
    with pytest.raises(PermissionError, match="test guard"):
        subprocess.Popen(f"{_absent_claude(tmp_path)} -p x", shell=True, executable="/bin/sh")


# ---------------------------------------------------------------------------
# The second layer: a claude stand-in first on PATH (Codex review round 6)
# ---------------------------------------------------------------------------


def _clear_stub_marker():
    if os.path.exists(suite._CLAUDE_STUB_MARKER):
        os.remove(suite._CLAUDE_STUB_MARKER)


def test_the_stand_in_is_first_on_path():
    import shutil

    assert os.environ["PATH"].split(os.pathsep)[0] == suite._CLAUDE_STUB_DIR
    assert shutil.which("claude") == suite._CLAUDE_STUB


def test_the_stand_in_answers_a_version_probe_and_records_nothing():
    before = suite._claude_stub_runs()
    # Spelled so the first layer cannot see the word; PATH holds only the
    # stand-in's folder, so nothing else called claude can be found.
    out = subprocess.run(
        ["/bin/sh", "-c", "c=cla; ${c}ude --version"],
        capture_output=True, text=True, env={"PATH": suite._CLAUDE_STUB_DIR},
    )
    assert out.returncode == 0
    assert "test stand-in" in out.stdout
    assert suite._claude_stub_runs() == before


def test_a_launch_the_first_layer_misses_is_caught_by_the_stand_in():
    _clear_stub_marker()
    try:
        out = subprocess.run(
            ["/bin/sh", "-c", "c=cla; ${c}ude -p 'guard check'"],
            capture_output=True, text=True, env={"PATH": suite._CLAUDE_STUB_DIR},
        )
        assert out.returncode == 97
        assert suite._claude_stub_runs() == ["claude -p guard check"]
    finally:
        _clear_stub_marker()  # this test's own run must not fail the session


def test_the_session_fails_when_the_stand_in_ran(tmp_path):
    """The session hook reports the recorded runs and marks the run failed."""
    _clear_stub_marker()

    class _Reporter:
        lines: list = []

        def write_line(self, line):
            self.lines.append(line)

    class _Plugins:
        def get_plugin(self, name):
            return _Reporter()

    class _Config:
        pluginmanager = _Plugins()

    class _Session:
        config = _Config()
        exitstatus = 0

    stub_dir = suite._CLAUDE_STUB_DIR
    marker = suite._CLAUDE_STUB_MARKER
    fake_dir = tmp_path / "stub"
    fake_dir.mkdir()
    try:
        suite._CLAUDE_STUB_DIR = str(fake_dir)  # the hook removes this folder
        suite._CLAUDE_STUB_MARKER = str(fake_dir / "claude-was-run.log")
        (fake_dir / "claude-was-run.log").write_text("claude -p x\n")
        session = _Session()
        suite.pytest_sessionfinish(session, 0)
        assert session.exitstatus == pytest.ExitCode.TESTS_FAILED
        assert any("TEST SUITE FAILED" in line for line in _Reporter.lines)
        assert not fake_dir.exists()

        quiet = _Session()
        fake_dir.mkdir()
        suite.pytest_sessionfinish(quiet, 0)
        assert quiet.exitstatus == 0
    finally:
        suite._CLAUDE_STUB_DIR = stub_dir
        suite._CLAUDE_STUB_MARKER = marker


def test_other_shell_commands_still_run():
    assert os.system("true") == 0
    out = subprocess.run("echo ok", shell=True, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "ok"


def test_other_programs_still_start():
    out = subprocess.run(
        [sys.executable, "-c", "print('ok')"], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "ok"


def test_popen_keeps_its_signature():
    """Code that reads Popen's parameters (the launch-environment guard's
    static checks) must see the real ones, not the wrapper's."""
    import inspect

    assert "env" in inspect.signature(subprocess.Popen.__init__).parameters
