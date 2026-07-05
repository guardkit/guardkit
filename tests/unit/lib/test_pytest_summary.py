"""Tests for the shared pytest-summary parser (TASK-AB-REVIEWCLEAN01 item 1).

Pins the tri-state absence contract the three consumers depend on and the
exact behaviours the two consolidated call sites
(``specialist_invocations._parse_pytest_counts``,
``coach_validator._parse_tests_skipped``) previously implemented inline.
"""

from __future__ import annotations

import pytest

from guardkit.lib.pytest_summary import PytestSummary, parse_pytest_summary


class TestParsePytestSummary:
    def test_empty_and_none_are_all_unknown(self):
        for out in ("", None):
            s = parse_pytest_summary(out)
            assert not s.parsed
            assert s.passed is None and s.failed is None and s.skipped is None
            assert s.tests_run is None and s.tests_failed is None

    def test_no_recognisable_token_is_unknown(self):
        s = parse_pytest_summary("no recognisable summary here")
        assert not s.parsed
        assert s.tests_run is None
        assert s.skipped is None  # NEVER 0-coerced on a parse miss

    def test_passed_and_skipped(self):
        s = parse_pytest_summary("===== 5 passed, 2 skipped in 1.2s =====")
        assert s.parsed
        assert s.passed == 5 and s.skipped == 2
        assert s.tests_run == 5  # skipped excluded
        assert s.tests_failed == 0

    def test_skipped_only_is_parsed_with_zero_run(self):
        s = parse_pytest_summary("===== 4 skipped in 0.5s =====")
        assert s.parsed  # a token WAS seen
        assert s.skipped == 4
        assert s.tests_run == 0  # no passed/failed
        assert s.tests_failed == 0

    def test_clean_summary_no_skip_token_is_zero_skipped(self):
        s = parse_pytest_summary("===== 5 passed in 0.2s =====")
        assert s.parsed
        assert s.skipped == 0  # positively zero, not unknown

    def test_failing_run_order_captures_all(self):
        # pytest orders failed BEFORE passed on failing runs; the shared
        # regex is order-independent (the SKIPVIS01 bug the positional
        # pattern had).
        s = parse_pytest_summary("===== 2 failed, 3 passed, 1 skipped in 1s =====")
        assert s.failed == 2 and s.passed == 3 and s.skipped == 1
        assert s.tests_run == 5  # 3 passed + 2 failed
        assert s.tests_failed == 2

    def test_errors_fold_into_error_and_tests_failed(self):
        s = parse_pytest_summary("===== 1 passed, 2 errors in 1s =====")
        assert s.errors == 2
        assert s.tests_failed == 2  # failed + errors
        assert s.tests_run == 3  # 1 passed + 2 errors

    def test_xpassed_xfailed_counted_in_run_not_failed(self):
        s = parse_pytest_summary("===== 1 xpassed, 1 xfailed, 2 passed in 1s =====")
        assert s.xpassed == 1 and s.xfailed == 1
        assert s.tests_run == 4
        assert s.tests_failed == 0

    def test_max_wins_on_reprinted_summary(self):
        s = parse_pytest_summary("3 passed ... later ... 5 passed, 1 skipped")
        assert s.passed == 5 and s.skipped == 1


class TestConsumerParity:
    """The behaviours the two consolidated call sites depend on, expressed
    against the shared parser directly (so a regression here localises the
    break)."""

    @pytest.mark.parametrize(
        "output,expected",
        [
            ("", (0, 0, None)),
            (None, (0, 0, None)),
            ("no recognisable summary here", (0, 0, None)),
            ("===== 5 passed, 2 skipped in 1.2s =====", (5, 0, 2)),
            ("===== 4 skipped in 0.5s =====", (0, 0, 4)),
        ],
    )
    def test_parse_pytest_counts_tuple_shape(self, output, expected):
        # Mirrors specialist_invocations._parse_pytest_counts's adapter.
        s = parse_pytest_summary(output)
        assert (s.tests_run or 0, s.tests_failed or 0, s.skipped) == expected

    @pytest.mark.parametrize(
        "output,expected_skipped",
        [
            ("", None),
            (None, None),
            ("garbage", None),
            ("5 passed in 0.2s", 0),
            ("2 failed, 3 passed, 1 skipped", 1),
        ],
    )
    def test_parse_tests_skipped_tri_state(self, output, expected_skipped):
        assert parse_pytest_summary(output).skipped == expected_skipped
