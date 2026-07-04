"""pytest-bdd glue for TASK-QAV-005 against features/qav-behavioural-gates/qav-behavioural-gates.feature.

Binds the @task:TASK-QAV-005 scenario: "A correctly-wired stub with green
co-generated tests is still flagged".

Per .claude/rules/bdd-per-task-glue.md the glue module MUST be named
test_<slug>__<TASK-ID>.py to avoid cross-task race conditions in parallel
wave execution.
"""

from pathlib import Path

from pytest_bdd import scenario


_FEATURE = Path(__file__).with_name("qav-behavioural-gates.feature")


@scenario(
    _FEATURE,
    "A correctly-wired stub with green co-generated tests is still flagged",
)
def test_correctly_wired_stub_flagged():
    """Bind the TASK-QAV-005 regression scenario."""
    pass
