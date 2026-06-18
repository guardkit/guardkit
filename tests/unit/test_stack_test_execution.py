"""TASK-AB-NPDET01 — declarative non-Python stack test-execution registry.

Unit tests for ``guardkit/orchestrator/quality_gates/stack_test_execution.py``:
the per-stack ``StackTestProfile`` rows, ``detect_stack_profile`` (exactly-one
marker match, polyglot deferral), and the absence-of-failure-safe
``classify_absent_for_stack`` classifier (toolchain-missing, zero-test, and the
go exit-0 mixed-module guard).

Pure stdlib — runs on the main CI suite (no guardkitfactory).

Coverage target: >=90% of the module.
"""

from pathlib import Path

import pytest

from guardkit.orchestrator.quality_gates.stack_test_execution import (
    STACK_TEST_PROFILES,
    StackTestProfile,
    classify_absent_for_stack,
    detect_stack_profile,
)


def _profile(stack: str) -> StackTestProfile:
    return next(p for p in STACK_TEST_PROFILES if p.stack == stack)


# ============================================================================
# 1. Registry shape
# ============================================================================


class TestRegistryShape:
    def test_python_is_deliberately_excluded(self):
        """Python is NOT in the registry — the pytest deterministic path
        (TASK-AB-PERTASKFG01) is untouched by this module."""
        assert "python" not in {p.stack for p in STACK_TEST_PROFILES}

    def test_expected_stacks_present(self):
        assert {p.stack for p in STACK_TEST_PROFILES} == {"dotnet", "node", "go"}

    def test_commands_are_whole_suite(self):
        assert _profile("dotnet").whole_suite_command == "dotnet test"
        # plain ``npm test`` (NOT --silent, which can suppress the
        # missing-script / no-test-specified lines the classifier matches).
        assert _profile("node").whole_suite_command == "npm test"
        assert _profile("go").whole_suite_command == "go test ./..."

    def test_toolchain_missing_returncodes_are_absent_everywhere(self):
        for p in STACK_TEST_PROFILES:
            assert 127 in p.absent_returncodes
            assert 126 in p.absent_returncodes


# ============================================================================
# 2. detect_stack_profile — exactly-one match, depth-0, polyglot deferral
# ============================================================================


class TestDetectStackProfile:
    def test_detects_dotnet_via_csproj(self, tmp_path):
        (tmp_path / "App.csproj").write_text("<Project/>")
        assert detect_stack_profile(tmp_path).stack == "dotnet"

    def test_detects_dotnet_via_sln(self, tmp_path):
        (tmp_path / "App.sln").write_text("solution")
        assert detect_stack_profile(tmp_path).stack == "dotnet"

    def test_detects_node_via_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        assert detect_stack_profile(tmp_path).stack == "node"

    def test_detects_go_via_go_mod(self, tmp_path):
        (tmp_path / "go.mod").write_text("module x")
        assert detect_stack_profile(tmp_path).stack == "go"

    def test_python_only_worktree_returns_none(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "requirements.txt").write_text("pytest")
        assert detect_stack_profile(tmp_path) is None

    def test_empty_worktree_returns_none(self, tmp_path):
        assert detect_stack_profile(tmp_path) is None

    def test_polyglot_returns_none_not_a_guess(self, tmp_path):
        """A .NET solution that vendors a root package.json matches TWO stacks ->
        return None and defer to the LLM specialist rather than mis-detect."""
        (tmp_path / "App.csproj").write_text("<Project/>")
        (tmp_path / "package.json").write_text("{}")
        assert detect_stack_profile(tmp_path) is None

    def test_markers_are_depth_zero_only(self, tmp_path):
        """A package.json in a subdir (e.g. a frontend ClientApp) does NOT make
        the root a node project — detection is root-only (non-recursive)."""
        sub = tmp_path / "ClientApp"
        sub.mkdir()
        (sub / "package.json").write_text("{}")
        assert detect_stack_profile(tmp_path) is None


# ============================================================================
# 3. classify_absent_for_stack — absence-of-failure safety per stack
# ============================================================================


class TestToolchainMissing:
    @pytest.mark.parametrize("stack", ["dotnet", "node", "go"])
    def test_returncode_127_is_absent(self, stack):
        assert classify_absent_for_stack(_profile(stack), 127, "") is True

    @pytest.mark.parametrize("stack", ["dotnet", "node", "go"])
    def test_returncode_126_is_absent(self, stack):
        assert classify_absent_for_stack(_profile(stack), 126, "") is True

    def test_dash_not_found_substring_is_absent(self):
        """/bin/sh (dash) emits '<tool>: not found' and exits 127 — both signals
        flag absent (the substring is a backstop if the exit code differs)."""
        assert classify_absent_for_stack(
            _profile("dotnet"), 127, "/bin/sh: 1: dotnet: not found"
        ) is True

    def test_bash_command_not_found_substring_is_absent(self):
        assert classify_absent_for_stack(
            _profile("go"), 127, "bash: go: command not found"
        ) is True

    def test_partial_dotnet_sdk_is_absent(self):
        """A partial install emits 'No .NET SDKs were found' on a non-127 exit —
        must still be absent (false-red guard, must-fix #3)."""
        assert classify_absent_for_stack(
            _profile("dotnet"), 145, "No .NET SDKs were found."
        ) is True


class TestZeroTestUnambiguous:
    def test_dotnet_no_test_available_exit0_is_absent(self):
        """dotnet can exit 0 having discovered zero tests -> absent, not a pass
        (the exit-0 zero-test false-green guard)."""
        assert classify_absent_for_stack(
            _profile("dotnet"), 0, "No test is available in Foo.dll"
        ) is True

    def test_npm_no_test_specified_is_absent(self):
        """The ``npm init`` placeholder test script: 'Error: no test specified'."""
        assert classify_absent_for_stack(
            _profile("node"), 1, 'Error: no test specified'
        ) is True

    def test_npm_missing_script_is_absent(self):
        """No 'test' script at all: npm 'Missing script: \"test\"' (exit 1, NOT
        127 — so the substring, not the returncode, is load-bearing)."""
        assert classify_absent_for_stack(
            _profile("node"), 1, 'npm error Missing script: "test"'
        ) is True


class TestGoExitZeroMixedModuleGuard:
    def test_go_all_packages_testless_is_absent(self):
        """go test ./... over a module with NO test files exits 0 printing only
        '[no test files]' lines -> zero tests ran -> absent."""
        out = "?   ex/a\t[no test files]\n?   ex/b\t[no test files]\n"
        assert classify_absent_for_stack(_profile("go"), 0, out) is True

    def test_go_mixed_module_with_pass_line_is_NOT_absent(self):
        """The critical guard: '[no test files]' co-occurs with passing packages
        in a mixed module. With an 'ok' pass-line present, the run DID exercise
        tests -> NOT absent (would otherwise false-red a legitimate pass)."""
        out = "ok  \tex/a\t0.012s\n?   ex/b\t[no test files]\n"
        assert classify_absent_for_stack(_profile("go"), 0, out) is False

    def test_go_real_failure_is_not_absent(self):
        out = "--- FAIL: TestX (0.00s)\nFAIL\tex/a\t0.01s\n"
        assert classify_absent_for_stack(_profile("go"), 1, out) is False


class TestGenuineFailureNotAbsent:
    def test_dotnet_test_failure_is_not_absent(self):
        assert classify_absent_for_stack(
            _profile("dotnet"), 1, "Failed!  - Failed: 2, Passed: 3, Skipped: 0"
        ) is False

    def test_dotnet_compile_error_is_not_absent(self):
        """A compile error means the deliverable doesn't build — a real failure,
        not an absent toolchain."""
        assert classify_absent_for_stack(
            _profile("dotnet"), 1, "Program.cs(10,5): error CS1002: ; expected"
        ) is False

    def test_npm_test_failure_is_not_absent(self):
        assert classify_absent_for_stack(
            _profile("node"), 1, "Tests: 2 failed, 8 passed, 10 total"
        ) is False

    def test_go_build_error_is_not_absent(self):
        assert classify_absent_for_stack(
            _profile("go"), 2, "ex/a/main.go:5:2: undefined: Foo"
        ) is False


class TestPassingRunNotAbsent:
    def test_dotnet_pass_is_not_absent(self):
        assert classify_absent_for_stack(
            _profile("dotnet"), 0, "Passed!  - Failed: 0, Passed: 5"
        ) is False

    def test_npm_pass_is_not_absent(self):
        assert classify_absent_for_stack(
            _profile("node"), 0, "Tests: 5 passed, 5 total"
        ) is False

    def test_go_pass_is_not_absent(self):
        assert classify_absent_for_stack(
            _profile("go"), 0, "ok  \tex/a\t0.012s\nok  \tex/b\t0.004s\n"
        ) is False


class TestNodeExitZeroZeroTestGuard:
    """The reproduced false-green (review hole #1): a node test script that
    exits 0 having run ZERO tests must be ABSENT, never an approval. node has no
    fixed zero-test phrase, so the guard is a positive ran-marker precondition."""

    def test_jest_pass_with_no_tests_is_absent(self):
        out = "> jest --passWithNoTests\n\nNo tests found, exiting with code 0\n"
        assert classify_absent_for_stack(_profile("node"), 0, out) is True

    def test_vitest_pass_with_no_tests_is_absent(self):
        out = "No test files found, exiting with code 0\n"
        assert classify_absent_for_stack(_profile("node"), 0, out) is True

    def test_bare_echo_placeholder_is_absent(self):
        """A ``"test": "echo ...; exit 0"`` placeholder prints no recognisable
        ran-marker -> absent (only the positive precondition catches this; no
        substring can)."""
        out = '> echo "TODO: add tests"\n\nTODO: add tests\n'
        assert classify_absent_for_stack(_profile("node"), 0, out) is True

    def test_node_real_pass_has_ran_marker(self):
        """Counterpart guard: real runner passes must NOT be absent (else the
        precondition false-reds correct deliverables). One per mainstream runner."""
        for out in (
            "PASS src/foo.test.js\nTests:       3 passed, 3 total\n",  # jest
            "  3 passing (12ms)\n",  # mocha
            "Test Files  1 passed (1)\nTests  3 passed (3)\n",  # vitest
            "3 specs, 0 failures\n",  # jasmine
            "ok 1 - works\nok 2 - also\n# pass 2\n",  # tap / node:test
            "3 tests passed\n",  # ava
            "  ✓ does the thing (4ms)\n",  # reporter checkmark
        ):
            assert classify_absent_for_stack(_profile("node"), 0, out) is False, out

    def test_node_failure_branch_unaffected_by_precondition(self):
        """The precondition is success-only: a real exit-1 failure stays
        ran-and-failed (not absent)."""
        assert classify_absent_for_stack(
            _profile("node"), 1, "Tests: 2 failed, 8 passed, 10 total"
        ) is False


class TestIncidentalAbsentSubstringInPassingRun:
    """The reproduced false-red (review hole #2): a legitimately PASSING run whose
    output incidentally contains a toolchain-ish phrase must NOT be marked absent.
    The bare ': not found' substring was dropped to fix this; toolchain-missing is
    caught by returncode 127 instead (see TestToolchainMissing)."""

    def test_node_pass_with_http_404_not_found(self):
        out = "GET /missing -> 404: Not Found\n5 passing\n"
        assert classify_absent_for_stack(_profile("node"), 0, out) is False

    def test_node_pass_with_test_title_not_found(self):
        out = "  ✓ when id: not found returns 404\n3 passing\n"
        assert classify_absent_for_stack(_profile("node"), 0, out) is False

    def test_go_pass_with_incidental_not_found(self):
        out = "ok  \tex/a\t0.01s\n"  # a go pass; ': not found' no longer triggers
        assert classify_absent_for_stack(
            _profile("go"), 0, out + "// host: not found path covered\n"
        ) is False

    def test_dotnet_pass_with_incidental_not_found(self):
        out = "Passed!  - Failed: 0, Passed: 5  // 404: not found case\n"
        assert classify_absent_for_stack(_profile("dotnet"), 0, out) is False
