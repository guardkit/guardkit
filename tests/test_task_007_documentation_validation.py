"""TASK-007 documentation checks: the 100% test pass requirement.

Restored on 1 November 2026 as real pytest tests. The original file (deleted
in 8e3adf22) was a script: every check recorded a result in a list and never
asserted, it read the files from a foreign machine's absolute path, and it
looked for the wording where it lived in 2025. The requirement it checked is
still in the repository, now in these places:

- installer/core/commands/task-work.md: Step 6 routing table. The Python
  ``determine_next_state`` pseudo-code it used to contain was rewritten as
  prose and a table in 9b2b6d33 (April 2026), on purpose.
- installer/core/commands/task-work-phases-build-ext.md: Phase 4 and Phase
  4.5, split out of task-work.md in 51da6c6e (July 2026).
- installer/core/agents/test-orchestrator.md: the quality gate thresholds.
- installer/core/agents/test-orchestrator-ext.md: Mandatory Rule #1, build
  before test, and the stack-specific build commands.

Checks dropped, with the reason: the four MAUI test-orchestrator checks and
the MAUI cross-reference check (the MAUI templates were removed in ff9483723,
TASK-065); the "ABSOLUTE REQUIREMENT" / "ZERO TOLERANCE" words inside Phase
4.5 of task-work and the emphatic-word count of 15 or more (that wording was
removed from task-work.md in 9b2b6d33, and a third of the count came from
the removed MAUI file). The requirement those words stated is checked below
in its current wording.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TASK_WORK = REPO / "installer/core/commands/task-work.md"
TASK_WORK_BUILD = REPO / "installer/core/commands/task-work-phases-build-ext.md"
TEST_ORCHESTRATOR = REPO / "installer/core/agents/test-orchestrator.md"
TEST_ORCHESTRATOR_EXT = REPO / "installer/core/agents/test-orchestrator-ext.md"

ALL_FILES = [TASK_WORK, TASK_WORK_BUILD, TEST_ORCHESTRATOR, TEST_ORCHESTRATOR_EXT]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(content: str, heading: str) -> str:
    """The text from ``heading`` (a whole heading line) to the next heading of
    the same or a higher level. Lines inside code blocks (``# Step 1: ...``
    shell comments) are not headings."""
    level = len(heading) - len(heading.lstrip("#"))
    start = content.find(heading)
    assert start != -1, f"heading not found: {heading!r}"
    end_pattern = re.compile(r"^#{1,%d} " % level)
    lines = content[start:].split("\n")
    in_code = False
    for index, line in enumerate(lines[1:], start=1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        elif not in_code and end_pattern.match(line):
            return "\n".join(lines[:index])
    return content[start:]


# ---------------------------------------------------------------------------
# Category 1: the files exist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_file_exists(path):
    assert path.is_file(), f"not found: {path.relative_to(REPO)}"


# ---------------------------------------------------------------------------
# Category 2: Markdown syntax
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ALL_FILES, ids=lambda p: p.name)
def test_code_blocks_are_closed(path):
    fences = _read(path).count("```")
    assert fences % 2 == 0, f"{path.name}: {fences} code fence markers (one unclosed)"


@pytest.mark.parametrize("path", [TASK_WORK, TASK_WORK_BUILD], ids=lambda p: p.name)
def test_headers_have_a_space_after_the_hashes(path):
    bad = [
        line[:50]
        for line in _read(path).split("\n")
        if line.startswith("#") and not re.match(r"^#+\s+.+", line)
    ]
    assert not bad, f"{path.name}: malformed headers {bad}"


# ---------------------------------------------------------------------------
# Category 3: task-work, Phase 4, Phase 4.5 and Step 6
# ---------------------------------------------------------------------------


def test_phase_4_references_test_orchestrator():
    phase_4 = _section(_read(TASK_WORK_BUILD), "#### Phase 4: Testing")
    assert "test-orchestrator.md" in phase_4


def test_phase_4_has_the_mandatory_compilation_check():
    phase_4 = _section(_read(TASK_WORK_BUILD), "#### Phase 4: Testing")
    assert "MANDATORY COMPILATION CHECK" in phase_4
    assert "MUST verify code COMPILES" in phase_4
    assert "ONLY proceed to test execution if compilation succeeds" in phase_4


def test_phase_4_5_requires_clean_compilation_and_zero_failures():
    """The pass bar Phase 4.5 states (it said "ABSOLUTE REQUIREMENT" and
    "ZERO TOLERANCE" before 9b2b6d33): only clean compilation and zero test
    failures leave the fix loop, after at most three attempts."""
    phase_45 = _section(_read(TASK_WORK_BUILD), "#### Phase 4.5: Fix Loop (Ensure All Tests Pass)")
    assert "clean compilation **and** zero test failures" in phase_45
    assert "up to three fix attempts" in phase_45
    assert "BLOCKED" in phase_45


def test_step_5_gates_require_compilation_and_all_tests_passing():
    step_5 = _section(_read(TASK_WORK), "### Step 5: Evaluate Quality Gates (REQUIRED)")
    assert re.search(r"\| Code compiles \| 100% \|", step_5)
    assert re.search(r"\| All tests passing \| 100% \|", step_5)


def test_step_6_compilation_errors_block_the_task():
    step_6 = _section(_read(TASK_WORK), "### Step 6: Determine Next State (REQUIRED)")
    assert re.search(r"\| Compilation errors remain[^|]*\| `blocked` \|", step_6)


def test_step_6_any_test_failure_blocks_the_task():
    step_6 = _section(_read(TASK_WORK), "### Step 6: Determine Next State (REQUIRED)")
    assert re.search(
        r"\| Any test failure remains \(pass rate < 100 %\) \| `blocked` \| Zero-tolerance gate",
        step_6,
    )


def test_step_6_in_review_only_when_everything_passes():
    step_6 = _section(_read(TASK_WORK), "### Step 6: Determine Next State (REQUIRED)")
    assert re.search(
        r"\| Clean compile, all tests passing, coverage thresholds met \| `in_review` \|",
        step_6,
    )
    assert "**This is the ONLY path to IN_REVIEW state**" in step_6


# ---------------------------------------------------------------------------
# Category 4: test-orchestrator
# ---------------------------------------------------------------------------


def test_mandatory_rule_1_header():
    assert "## 🚨 MANDATORY RULE #1: BUILD BEFORE TEST 🚨" in _read(TEST_ORCHESTRATOR_EXT)
    # The core agent file points at the rule.
    assert "MANDATORY - see Rule #1" in _read(TEST_ORCHESTRATOR)


def test_rule_1_is_an_absolute_requirement():
    rule_1 = _section(_read(TEST_ORCHESTRATOR_EXT), "## 🚨 MANDATORY RULE #1: BUILD BEFORE TEST 🚨")
    assert "**ABSOLUTE REQUIREMENT**: Code MUST compile/build successfully BEFORE any tests are executed." in rule_1


def test_build_verification_sequence():
    rule_1 = _section(_read(TEST_ORCHESTRATOR_EXT), "## 🚨 MANDATORY RULE #1: BUILD BEFORE TEST 🚨")
    steps = [
        "Step 1: Clean",
        "Step 2: Restore",
        "Step 3: Build",
        "Step 4: IF build fails, STOP",
        "Step 5: ONLY if build succeeds",
    ]
    missing = [step for step in steps if step not in rule_1]
    assert not missing, f"missing steps: {missing}"
    positions = [rule_1.index(step) for step in steps]
    assert positions == sorted(positions), "the build steps are out of order"


def test_stack_specific_build_commands():
    rule_1 = _section(_read(TEST_ORCHESTRATOR_EXT), "## 🚨 MANDATORY RULE #1: BUILD BEFORE TEST 🚨")
    stacks = ["### .NET / C# / MAUI", "### TypeScript / Node.js", "### Python", "### Java"]
    missing = [stack for stack in stacks if stack not in rule_1]
    assert not missing, f"missing stacks: {missing}"


def test_quality_gates_zero_tolerance():
    gates = _section(_read(TEST_ORCHESTRATOR), "## Quality Gate Configuration")
    assert "**ZERO TOLERANCE**" in gates
    assert "unless ALL gates pass" in gates
    for setting in ("test_pass_rate: 100", "zero_failures: true", "no_exceptions: true"):
        assert setting in gates, f"missing {setting!r}"


def test_test_orchestrator_references_task_work_step_6():
    content = _read(TEST_ORCHESTRATOR)
    assert "See task-work.md Step 6" in content


# ---------------------------------------------------------------------------
# Category 6 and 7: emphasis and cross-references
# ---------------------------------------------------------------------------


def test_visual_emphasis_present():
    content = _read(TASK_WORK) + _read(TEST_ORCHESTRATOR)
    found = [marker for marker in ("🚨", "❌", "✅") if marker in content]
    assert len(found) >= 2, f"only {found}"


def test_task_work_references_test_orchestrator():
    """task-work's build phases (split out of task-work.md in 51da6c6e) name
    the agent file, by its repository path too."""
    content = _read(TASK_WORK_BUILD)
    assert "test-orchestrator.md" in content
    assert "installer/core/agents/test-orchestrator.md" in content


def test_test_orchestrator_references_task_work():
    content = _read(TEST_ORCHESTRATOR)
    found = [ref for ref in ("task-work.md", "See task-work.md", "Phase 4", "Step 6") if ref in content]
    assert len(found) >= 2, f"only {found}"
