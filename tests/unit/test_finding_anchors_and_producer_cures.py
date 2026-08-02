"""GA3 — the finding anchor + the two producer cures (LI stage 2, §5).

Three mechanisms, one suite:

1. **The anchor.** Every finding rendered into ``## Detection Findings`` gains
   ``anchor`` = ``<normalized repo-relative file>|<severity>``. It is the
   pipeline's dedup key: the fix-task id is prose+position-derived (88 distinct
   ids for ~5 defects in the 2026-08-02 runaway) and the *line* drifts
   (14 / null / 0 / 36 for one defect), so neither can carry identity. The FILE
   survives — 162 findings collapsed to 31 (file, line) pairs and 8 files.
   ``line`` stays a separate data field and never enters the anchor.

2. **The prefix pad.** A derived fix-task prefix is padded to >= 3 characters so
   the file stem passes the pipeline's ``^TASK-[A-Z0-9]{3,12}(?:-[A-Za-z0-9]+)*$``
   head. Before the pad, a two-word feature slug minted ``TASK-FW-001-…`` and the
   dispatcher dropped it in silence.

3. **The effort coercion.** ``estimated_effort_days`` is summed as a float while
   the producer carries effort as ``"1d"``; the resulting ``TypeError`` at step
   9/10 meant 42/42 legs of the crossing produced fix tasks but never a guide.

**forge is NOT imported.** Its regexes are COPIED below with their home named —
the same discipline as ``test_task_review_leg.py``'s header. A copy that drifts
fails here; an import would make this suite depend on a sibling checkout.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pytest

from guardkit.orchestrator import review_runner
from guardkit.orchestrator.review_runner import (
    ANCHOR_NO_FILE,
    ANCHOR_NO_SEVERITY,
    anchored_findings,
    finding_anchor,
    render_marker_block,
)


# ===========================================================================
# Copies of forge's scrape shapes — never imports
# ===========================================================================

# Home: forge/src/forge/cli/_serve_deps_stage_log.py:398 (the fix-task stem the
# dispatcher recognises). The queue guards the same shape at
# forge/src/forge/cli/queue.py:403 with `^TASK-[A-Z0-9]{3,12}$`.
FORGE_FIX_TASK_ID_RE = re.compile(r"^TASK-[A-Z0-9]{3,12}(?:-[A-Za-z0-9]+)*$")

# Home: forge/src/forge/adapters/guardkit/parser.py:36-61 — the findings block
# scrape. Its extractor keeps every dict element verbatim (parser.py:225-241),
# which is why `anchor` can be additive.
FORGE_DETECTION_FINDINGS_SECTION_RE = re.compile(
    r"^##\s+Detection\s+Findings\s*$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE
)
FORGE_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.MULTILINE)


def forge_extract_findings(stdout: str):
    section = FORGE_DETECTION_FINDINGS_SECTION_RE.search(stdout)
    if section is None:
        return None
    fence = FORGE_JSON_FENCE_RE.search(section.group(1))
    if fence is None:
        return None
    payload = json.loads(fence.group(1).strip())
    if not isinstance(payload, list):
        return None
    return [item for item in payload if isinstance(item, dict)]


# ===========================================================================
# 1. The anchor — normalization
# ===========================================================================


class TestAnchorNormalization:
    def test_plain_repo_relative_file_and_severity(self):
        assert (
            finding_anchor({"file": "src/parser.py", "severity": "high"})
            == "src/parser.py|high"
        )

    def test_dot_slash_prefix_is_stripped(self):
        assert (
            finding_anchor({"file": "./src/parser.py", "severity": "high"})
            == "src/parser.py|high"
        )

    def test_windows_separators_become_posix(self):
        assert (
            finding_anchor({"file": r"src\core\config.py", "severity": "medium"})
            == "src/core/config.py|medium"
        )

    def test_trailing_line_suffix_never_enters_the_anchor(self):
        """``src/parser.py:88`` is a file value carrying a line — strip it.

        The whole point of the anchor is that the line drifts. If the model
        writes the line into the ``file`` field, the identity must not drift
        with it.
        """
        assert (
            finding_anchor({"file": "src/parser.py:88", "severity": "high"})
            == "src/parser.py|high"
        )
        assert (
            finding_anchor({"file": "src/parser.py:88:4", "severity": "high"})
            == "src/parser.py|high"
        )

    def test_absolute_path_inside_the_repo_is_relativized(self, tmp_path):
        target = tmp_path / "src" / "parser.py"
        target.parent.mkdir(parents=True)
        target.write_text("x", encoding="utf-8")
        assert (
            finding_anchor({"file": str(target), "severity": "high"}, tmp_path)
            == "src/parser.py|high"
        )

    def test_absolute_path_outside_the_repo_is_kept_verbatim(self, tmp_path):
        """Naming a foreign path honestly beats inventing a relative one."""
        anchor = finding_anchor(
            {"file": "/etc/hosts", "severity": "low"}, tmp_path / "repo"
        )
        assert anchor == "/etc/hosts|low"

    def test_severity_is_case_and_whitespace_normalized(self):
        assert (
            finding_anchor({"file": "a.py", "severity": "  HIGH "}) == "a.py|high"
        )

    def test_missing_file_uses_the_named_sentinel(self):
        assert (
            finding_anchor({"severity": "must_fix"})
            == f"{ANCHOR_NO_FILE}|must_fix"
        )

    def test_missing_severity_uses_the_named_sentinel(self):
        assert (
            finding_anchor({"file": "a.py"}) == f"a.py|{ANCHOR_NO_SEVERITY}"
        )

    @pytest.mark.parametrize("bad", [None, 12, [], {}, "", "   ", "./"])
    def test_unusable_file_values_never_raise(self, bad):
        anchor = finding_anchor({"file": bad, "severity": "high"})
        assert anchor == f"{ANCHOR_NO_FILE}|high"


# ===========================================================================
# 2. The anchor — the dedup property that the stop depends on
# ===========================================================================


class TestAnchorIsTheStableKey:
    """The measured drift from the runaway ledger, replayed in miniature."""

    def test_same_defect_under_drifting_line_id_and_title_shares_one_anchor(self):
        # src/core/config.py recurred 39 times under 23 titles in the runaway.
        drifted = [
            {"id": "F1", "title": "Config not validated", "file": "src/core/config.py",
             "line": 14, "severity": "high"},
            {"id": "F7", "title": "Unvalidated configuration load",
             "file": "src/core/config.py", "line": None, "severity": "high"},
            {"id": "F3", "title": "config.py accepts anything",
             "file": "./src/core/config.py", "line": 0, "severity": "HIGH"},
            {"id": "F9", "title": "Config validation missing",
             "file": "src/core/config.py:36", "line": 36, "severity": "high"},
        ]
        anchors = {finding_anchor(f) for f in drifted}
        assert anchors == {"src/core/config.py|high"}

    def test_different_severity_on_the_same_file_is_a_different_anchor(self):
        a = finding_anchor({"file": "src/core/config.py", "severity": "high"})
        b = finding_anchor({"file": "src/core/config.py", "severity": "low"})
        assert a != b

    def test_line_survives_as_data_and_is_absent_from_the_anchor(self):
        [item] = anchored_findings(
            [{"file": "src/parser.py", "line": 88, "severity": "high"}]
        )
        assert item["line"] == 88
        assert "88" not in item["anchor"]


# ===========================================================================
# 3. The anchor — additive, and it round-trips the block forge parses
# ===========================================================================


class TestAnchorIsAdditive:
    SAMPLE = {
        "id": "F1",
        "severity": "high",
        "title": "Unguarded attribute access",
        "file": "src/parser.py",
        "line": 88,
        "detail": "match.group(1) dereferenced without a None check.",
    }

    def test_every_existing_key_survives_byte_identically(self):
        [item] = anchored_findings([self.SAMPLE])
        assert {k: v for k, v in item.items() if k != "anchor"} == self.SAMPLE

    def test_only_anchor_is_added(self):
        [item] = anchored_findings([self.SAMPLE])
        assert set(item) - set(self.SAMPLE) == {"anchor"}

    def test_the_input_findings_are_not_mutated(self):
        before = dict(self.SAMPLE)
        anchored_findings([self.SAMPLE])
        assert self.SAMPLE == before
        assert "anchor" not in self.SAMPLE

    def test_a_supplied_anchor_is_never_overwritten(self):
        """The rule is stated once and applied once — a replay keeps its key."""
        [item] = anchored_findings(
            [dict(self.SAMPLE, anchor="legacy/path.py|critical")]
        )
        assert item["anchor"] == "legacy/path.py|critical"

    def test_a_blank_supplied_anchor_is_recomputed(self):
        [item] = anchored_findings([dict(self.SAMPLE, anchor="  ")])
        assert item["anchor"] == "src/parser.py|high"

    def test_empty_input_stays_empty(self):
        assert anchored_findings([]) == []

    def test_anchors_round_trip_through_the_pipelines_findings_scrape(self):
        """The block the conductor actually reads carries the anchors."""
        block = render_marker_block(
            fix_task_paths=("tasks/backlog/f/TASK-HPR-001-fix.md",),
            findings=anchored_findings([self.SAMPLE, {"file": "a.py"}]),
        )
        recovered = forge_extract_findings(block)
        assert recovered is not None
        assert [f["anchor"] for f in recovered] == [
            "src/parser.py|high",
            f"a.py|{ANCHOR_NO_SEVERITY}",
        ]
        # …and the rest of the finding survived the trip untouched.
        assert recovered[0]["detail"] == self.SAMPLE["detail"]
        assert recovered[0]["line"] == 88


class TestWorkLegResidualsCarryAnchors:
    """GA2's residual channel promised this block; GA3 makes the promise true."""

    def test_residual_finding_carries_an_honest_no_file_anchor(self):
        from guardkit.orchestrator.work_runner import residual_findings

        findings = residual_findings(
            approved=False,
            final_decision="needs_revision",
            turn_history=(),
            error="the Player never produced a report",
        )
        assert findings
        assert all(
            f["anchor"] == f"{ANCHOR_NO_FILE}|must_fix" for f in findings
        )

    def test_an_approved_leg_still_reports_no_residual(self):
        from guardkit.orchestrator.work_runner import residual_findings

        assert (
            residual_findings(
                approved=True, final_decision="approved", turn_history=(), error=None
            )
            == []
        )


# ===========================================================================
# 4. The prefix pad — proven against the COPIED stem regex
# ===========================================================================


def _extract_prefix(slug: str) -> str:
    from lib.review_parser import SubtaskExtractor

    # The extractor takes the report path it will read; the prefix derivation
    # does not touch it, so a non-existent path is honest here.
    return SubtaskExtractor("does-not-exist.md")._extract_prefix_from_slug(slug)


class TestFixTaskPrefixPad:
    def test_two_word_title_stem_matches_the_pipelines_regex(self):
        """The headline: the class that silently lost fix tasks in the crossing.

        Regex copied from forge/src/forge/cli/_serve_deps_stage_log.py:398 —
        deliberately NOT imported (forge is a separate repo/checkout).
        """
        from lib.review_parser import SubtaskExtractor

        subtasks = SubtaskExtractor("does-not-exist.md").parse_subtasks_from_numbered_list(
            "1. Add a null guard to parse_header() in src/parser.py.\n"
            "2. Cover the truncated-header path in tests/test_parser.py.\n",
            "feature-workflow",
        )
        assert len(subtasks) == 2
        for subtask in subtasks:
            stem = f"{subtask['id']}-a-slugified-title"
            assert FORGE_FIX_TASK_ID_RE.match(stem), stem
        assert [s["id"] for s in subtasks] == ["TASK-FWO-001", "TASK-FWO-002"]

    def test_the_unpadded_two_letter_prefix_really_would_have_failed(self):
        """Mutation control: without the pad the stem is rejected.

        If this ever passes, the regex copy above has drifted from its forge
        home and the pad test would be vacuous.
        """
        assert not FORGE_FIX_TASK_ID_RE.match("TASK-FW-001-a-slugified-title")

    def test_bulleted_parser_pads_the_same_way(self):
        from lib.review_parser import SubtaskExtractor

        subtasks = SubtaskExtractor("does-not-exist.md").parse_subtasks_from_bulleted_list(
            "- Add a null guard\n- Cover the truncated path\n", "dark-mode"
        )
        assert [s["id"] for s in subtasks] == ["TASK-DMO-001", "TASK-DMO-002"]
        assert all(
            FORGE_FIX_TASK_ID_RE.match(f"{s['id']}-slug") for s in subtasks
        )

    @pytest.mark.parametrize(
        "slug,expected",
        [
            ("feature-workflow", "FWO"),          # the crossing's own slug
            ("dark-mode", "DMO"),
            ("progressive-disclosure", "PDI"),
            ("workflow", "WOR"),                  # single word
            ("auth-api-gateway-layer", "AAGL"),   # already >= 3, unchanged
            ("a-b-c", "ABC"),                     # already exactly 3
            ("a-b", "ABT"),                       # nothing to continue → fallback
            ("2fa", "2FA"),                       # digits are in the stem class
            ("!!!", "TSK"),                       # nothing usable at all
            ("", "TSK"),
        ],
    )
    def test_derived_prefixes(self, slug, expected):
        assert _extract_prefix(slug) == expected

    @pytest.mark.parametrize(
        "slug",
        [
            "feature-workflow", "dark-mode", "workflow", "a-b", "!!!", "",
            "café-crème", "auth-api-gateway-layer", "2fa", "x",
        ],
    )
    def test_every_derived_prefix_yields_an_admissible_stem(self, slug):
        prefix = _extract_prefix(slug)
        assert 3 <= len(prefix) <= 12
        assert FORGE_FIX_TASK_ID_RE.match(f"TASK-{prefix}-001-some-slug"), prefix


# ===========================================================================
# 4b. The TABLE path mints ids too — and took them verbatim
# ===========================================================================


#: The exact shape a producer report writes, ids and all.
REPORT_TABLE = """
| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| FW-001 | Create /feature-plan command | Direct | 3 | 0.5d |
| FW-002 | Cover the truncated-header path | task-work | 5 | 1d |
"""


class TestReportTablePrefixPad:
    def _table_subtasks(self, table=REPORT_TABLE, slug="feature-workflow"):
        from lib.review_parser import SubtaskExtractor

        return SubtaskExtractor("does-not-exist.md").parse_subtasks_from_table(
            table, slug
        )

    def test_the_table_path_pads_like_every_other_mint(self):
        """The hole GA3 left open.

        ``parse_subtasks_from_table`` took the report's ``ID`` column verbatim
        and only prepended ``TASK-``, so the very rows a producer writes —
        ``| FW-001 |`` — minted ``TASK-FW-001-…``: a two-character head that
        the dispatcher's stem regex rejects, dropping the fix task in silence.
        """
        subtasks = self._table_subtasks()
        assert [s["id"] for s in subtasks] == ["TASK-FWO-001", "TASK-FWO-002"]
        for subtask in subtasks:
            stem = f"{subtask['id']}-a-slugified-title"
            assert FORGE_FIX_TASK_ID_RE.match(stem), stem

    def test_the_verbatim_form_really_would_have_been_rejected(self):
        """Mutation control for the row above — the unpadded stem fails."""
        assert not FORGE_FIX_TASK_ID_RE.match("TASK-FW-001-a-slugified-title")

    def test_a_legal_head_is_left_exactly_as_the_report_wrote_it(self):
        subtasks = self._table_subtasks(
            """
| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| AUTH-001 | Rotate the token | Direct | 3 | 1d |
""",
            "dark-mode",
        )
        assert [s["id"] for s in subtasks] == ["TASK-AUTH-001"]

    def test_an_id_already_carrying_the_task_prefix_is_padded_not_doubled(self):
        subtasks = self._table_subtasks(
            """
| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| TASK-FW-003 | Cure the swallow | Direct | 3 | 1d |
""",
        )
        assert [s["id"] for s in subtasks] == ["TASK-FWO-003"]
        assert FORGE_FIX_TASK_ID_RE.match("TASK-FWO-003-slug")

    def test_a_lowercase_head_is_normalized_into_the_stem_class(self):
        """``[A-Z0-9]`` — a lowercase head fails the head class just as surely."""
        subtasks = self._table_subtasks(
            """
| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| fw-004 | Cure the swallow | Direct | 3 | 1d |
""",
        )
        assert [s["id"] for s in subtasks] == ["TASK-FWO-004"]

    def test_an_over_long_head_is_truncated_to_the_regex_cap_not_dropped(self):
        """The re-verify coach's find: the pad closed the SHORT head only.

        A report head longer than the ``{3,12}`` cap is the identical
        silent-drop class — ``TASK-ABCDEFGHIJKLM-001`` fails the stem regex
        just as surely as ``TASK-FW-001``. Truncate to the cap, keeping as
        much of the report's naming as the rule admits.
        """
        subtasks = self._table_subtasks(
            """
| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| ABCDEFGHIJKLM-001 | Thirteen chars | Direct | 3 | 1d |
| VERYLONGPREFIXHEAD-002 | Eighteen chars | Direct | 3 | 1d |
""",
        )
        assert [s["id"] for s in subtasks] == [
            "TASK-ABCDEFGHIJKL-001",
            "TASK-VERYLONGPREF-002",
        ]
        for subtask in subtasks:
            assert FORGE_FIX_TASK_ID_RE.match(f"{subtask['id']}-a-slug"), subtask

    def test_a_twelve_char_head_sits_exactly_on_the_cap_and_is_kept(self):
        subtasks = self._table_subtasks(
            """
| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| ABCDEFGHIJKL-001 | Twelve chars | Direct | 3 | 1d |
""",
        )
        assert [s["id"] for s in subtasks] == ["TASK-ABCDEFGHIJKL-001"]

    def test_every_column_the_row_carried_still_arrives(self):
        """The pad touches the id and nothing else."""
        first = self._table_subtasks()[0]
        assert first["title"] == "Create /feature-plan command"
        assert first["implementation_mode"] == "direct"
        assert first["complexity"] == 3
        assert first["effort_estimate"] == "0.5d"

    def test_the_pad_is_stated_once_and_shared_by_both_mints(self):
        """One rule, one implementation — a copy would be a future lie."""
        import inspect

        from lib.review_parser import SubtaskExtractor

        source = inspect.getsource(SubtaskExtractor)
        assert source.count("def _pad_task_prefix") == 1
        assert source.count("FALLBACK_TASK_PREFIX)[:MIN_TASK_PREFIX_LEN]") == 1


# ===========================================================================
# 5. The effort coercion
# ===========================================================================


class TestEffortCoercion:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1d", 1.0),          # the exact shape from the runaway
            ("2d", 2.0),
            ("0.5d", 0.5),
            ("4h", 0.5),
            ("8h", 1.0),
            ("2 hours", 0.25),
            ("1w", 5.0),
            ("3", 3.0),           # a bare number is already days
            ("2.5", 2.5),
            (1, 1.0),
            (2.5, 2.5),
            ("  1d  ", 1.0),
            ("1D", 1.0),
        ],
    )
    def test_parsed_shapes(self, raw, expected):
        from lib.guide_generator import coerce_effort_days

        assert coerce_effort_days(raw) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "raw",
        [None, "", "soon", "a couple of days", [], True,
         # SIGNED values (the GA3 coach's find): the regex's ``[+-]?`` accepted
         # these, and a negative effort SUBTRACTS from the wave total — one
         # mistyped row quietly shortened the plan instead of being caught.
         "-2d", "-1", "-0.5w", "+2d", -2, -0.5],
    )
    def test_unparseable_falls_back_to_one_day_and_says_so(self, raw, caplog):
        from lib.guide_generator import DEFAULT_EFFORT_DAYS, coerce_effort_days

        with caplog.at_level(logging.WARNING, logger="lib.guide_generator"):
            assert coerce_effort_days(raw, subtask_id="TASK-FWO-001") == (
                DEFAULT_EFFORT_DAYS
            )
        assert any(
            "unparseable effort estimate" in r.message for r in caplog.records
        ), "the guess must be made out loud"
        assert any("TASK-FWO-001" in r.getMessage() for r in caplog.records)

    def test_a_negative_effort_can_never_shorten_a_wave(self):
        """The consequence the sign rule exists to prevent, driven end to end."""
        from lib.guide_generator import DEFAULT_EFFORT_DAYS, coerce_effort_days

        assert coerce_effort_days("-2d") == DEFAULT_EFFORT_DAYS
        total = coerce_effort_days("3d") + coerce_effort_days("-2d")
        assert total == pytest.approx(3.0 + DEFAULT_EFFORT_DAYS)
        assert total > coerce_effort_days("3d")

    def test_normalize_subtask_coerces_the_runaway_shape(self):
        from lib.guide_generator import _normalize_subtask

        normalized = _normalize_subtask(
            {"id": "TASK-FWO-001", "title": "Fix it", "estimated_effort_days": "1d"}
        )
        assert isinstance(normalized.estimated_effort_days, float)
        assert normalized.estimated_effort_days == 1.0

    def test_guide_generates_from_the_exact_runaway_shape(self):
        """The end the crossing never reached: a wave duration, not a TypeError."""
        from lib.guide_generator import generate_guide_content

        subtasks = [
            {
                "id": "TASK-FWO-001",
                "title": "Add a null guard to parse_header()",
                "implementation_method": "task-work",
                "complexity": 5,
                "estimated_effort_days": "1d",   # <- the shape that raised
                "parallel_group": 1,
                "conductor_workspace": "",
                "dependencies": [],
            },
            {
                "id": "TASK-FWO-002",
                "title": "Cover the truncated-header path",
                "implementation_method": "task-work",
                "complexity": 5,
                "estimated_effort_days": "4h",
                "parallel_group": 1,
                "conductor_workspace": "",
                "dependencies": [],
            },
        ]
        content = generate_guide_content("Feature Workflow", subtasks)
        assert "TASK-FWO-001" in content
        assert "1.5 days" in content  # 1d + 4h, summed as floats
        assert "1.0d" in content and "0.5d" in content


# ===========================================================================
# 6. The producer, driven for real — both cures at once
# ===========================================================================


class TestProducerEndToEnd:
    """The real ``handle_implement_option_sync``: no fake at this seam.

    Network-free — the producer only parses markdown and writes files.
    """

    REPORT = (
        "# Review Report — TASK-REV-A1B2C3\n\n"
        "## Summary\n\nTwo defects.\n\n"
        "## Recommendations\n\n"
        "1. Add a null guard to parse_header() in src/parser.py.\n"
        "2. Cover the truncated-header path in tests/test_parser.py.\n"
    )

    def _run(self, tmp_path: Path, title: str):
        import os

        report = tmp_path / ".claude" / "reviews" / "TASK-REV-A1B2C3-review-report.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(self.REPORT, encoding="utf-8")
        cwd = Path.cwd()
        os.chdir(tmp_path)
        try:
            return review_runner.produce_fix_tasks(
                task_id="TASK-REV-A1B2C3",
                task={"frontmatter": {"title": title}},
                report_path=report,
                repo_root=tmp_path,
            )
        finally:
            os.chdir(cwd)

    def test_two_word_feature_produces_admissible_stems_a_guide_and_a_readme(
        self, tmp_path
    ):
        written, info = self._run(tmp_path, "Review feature workflow")

        # Cure 1 — every stem the dispatcher will see is admissible.
        assert written
        assert all(FORGE_FIX_TASK_ID_RE.match(p.stem) for p in written), [
            p.stem for p in written
        ]
        assert all(p.stem.startswith("TASK-FWO-") for p in written)

        # Cure 2 — the producer reaches step 10/10 and both sidecars land.
        assert info["ok"] is True, info.get("error")
        target = written[0].parent
        assert (target / "IMPLEMENTATION-GUIDE.md").is_file()
        assert (target / "README.md").is_file()
        guide = (target / "IMPLEMENTATION-GUIDE.md").read_text(encoding="utf-8")
        assert "TASK-FWO-001" in guide
        assert "days" in guide or "hours" in guide
