"""One deliberately-failing test — a triaged red the F2 baseline must record.

Named check_*.py (not test_*.py) so guardkit's own suite never collects it; the
qa-seed observe_suite subprocess (rootdir = this fixture, python_files=check_*.py)
does collect it, producing the passed=3 / failed=1 observation the ledger seeds.
"""


def check_known_red():
    # Intentional failure — represents a known, to-be-triaged red at harvest time.
    assert 1 == 2
