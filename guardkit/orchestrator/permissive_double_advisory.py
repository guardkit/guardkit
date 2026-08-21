"""One home for the "test stand-in that accepts anything" advisory.

What the signal is, in plain words
----------------------------------
A test "double" is a stand-in object a test uses in place of the real thing.
A *permissive* double accepts any arguments at all. A test using one keeps
passing even after the real function it stands for has changed its argument
names — so the test is green and the wiring underneath it is dead. That is
the defect class that shipped forge's Mode P dead on arrival (post-merge
review ``forge/docs/reviews/feat-spl-002-post-merge-review-2026-07-06.md``).

The analyzer in ``guardkitfactory`` detects these on every run and writes them
into ``analyze_wiring(...)["permissive_double"]``.

Why the findings are split into two groups
------------------------------------------
There are far too many findings to read line by line: the estate scan of
2026-08-21 counted 3,156 of them across guardkit, forge, specialist-agent and
guardkitfactory. So this module sorts them into a SHARP group (46 of the
3,156) and a BROAD group (the other 3,110).

**The split is a volume filter, not a defect judgement.** It answers "which
handful can a reader start with", not "which ones are real". The estate's
worst known regression of this exact class sat entirely in the broad group:
forge's ``tests/cli/test_serve_planning_wiring.py`` at the broken commit
produced 24 findings, every one of them broad and none of them sharp.

The reason is structural, not a tuning accident. The sharp group is reached
one of two ways, and the Mode P defect reached neither:

* ``target_evidence == "name_matched"`` — the analyzer only emits this when
  the stand-in's name, with a ``Fake``/``Stub``/``Mock``-style affix stripped
  off, is itself a real first-party symbol. forge's class was
  ``RecordingFake``, which strips to ``Recording``; no such symbol exists, so
  the analyzer discarded the class entirely rather than reporting it.
* ``form == "star_args_fake"`` — the literal ``*args``/``**kwargs`` shape,
  which only ever carries that name-match evidence with it.

What was left was the 24 ordinary ``patch("module.function")`` sites, which
all land in the broad group. So a reader told "the broad group is noise" would
have been told to ignore the only evidence there was.

Both groups are ADVISORY everywhere they are used: nothing here can reject a
turn. Promoting either group to turn-rejecting must be a deliberate,
separately-reviewed decision.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "SHARP_TARGET_EVIDENCE",
    "SHARP_FORM",
    "split_findings",
    "coach_advisory_text",
]

#: A finding is SHARP when the stand-in is named after a real first-party
#: symbol, or when it literally declares ``*args``/``**kwargs``. Everything
#: else is BROAD. See the module docstring: this is a volume filter for a
#: reader's attention, NOT a judgement about which findings are real.
SHARP_TARGET_EVIDENCE = "name_matched"
SHARP_FORM = "star_args_fake"


def split_findings(
    wiring_result: Optional[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Sort ``wiring_result["permissive_double"]["findings"]`` into two groups.

    Returns ``(sharp, broad)``. This is the single implementation of the rule:
    the run log and the reviewing model's prompt both call it, so they can
    never disagree about the same run.

    Absence-safe: a missing key, a status other than ``"ran"``, or any
    unexpected shape yields two empty lists rather than raising. An absent
    signal is never evidence of anything, and this must never break either
    the run log or prompt construction.
    """
    if not isinstance(wiring_result, dict):
        return [], []
    pd = wiring_result.get("permissive_double")
    if not isinstance(pd, dict) or pd.get("status") != "ran":
        return [], []
    findings = pd.get("findings")
    if not isinstance(findings, list):
        return [], []
    sharp: List[Dict[str, Any]] = []
    broad: List[Dict[str, Any]] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        is_sharp = (
            f.get("target_evidence") == SHARP_TARGET_EVIDENCE
            or f.get("form") == SHARP_FORM
        )
        (sharp if is_sharp else broad).append(f)
    return sharp, broad


def coach_advisory_text(sharp_count: int, broad_count: int) -> str:
    """The advisory paragraph appended to the reviewing model's prompt.

    Deliberately does NOT tell the reader the broad group is safe to skip.
    An earlier draft of this text called the broad entries "near-certainly not
    defects"; rendered against the one file this whole advisory exists for
    (forge's planning wiring test, 0 sharp and 24 broad) that wording told the
    reader there was nothing to look at. See the module docstring.
    """
    return (
        f"\nADVISORY: wiring.permissive_double — {sharp_count} sharp, "
        f"{broad_count} broad.\n"
        "A permissive double is a stand-in object a test uses in place of the "
        "real thing which accepts ANY arguments, so the test stays green even "
        "after the real function's argument names have changed underneath it — "
        "green test, dead wiring.\n"
        "THE SHARP/BROAD SPLIT IS A VOLUME FILTER, NOT A DEFECT JUDGEMENT. It "
        "tells you where to start reading when there are too many findings to "
        "read them all. It does NOT tell you which findings are real, and a "
        "broad entry is NOT evidence that the wiring is fine.\n"
        "Sharp (target_evidence \"name_matched\", or form \"star_args_fake\") "
        "means the stand-in is named after a real function in this repo. Those "
        "are few and worth naming in your findings first.\n"
        "Broad means the ordinary patch(\"module.function\") idiom, which is "
        "common enough that you cannot read every one. Do not read that as "
        "safe: the estate's worst known regression of this exact class — the "
        "one this advisory exists for — was 24 findings, ALL of them broad and "
        "NONE sharp, because the sharp path needs the stand-in's name to match "
        "a real symbol and that file's class was named \"RecordingFake\". If "
        "this turn changed a function's arguments, check the broad entries that "
        "name it, however many there are.\n"
        "Advisory only — never reject the turn on these counts alone.\n"
    )
