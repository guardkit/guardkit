"""Reports where a repository's code sits relative to its own written architecture rules.

WHAT THIS IS
------------
A repository can write down how it is meant to be built — "database queries live in
crud.py", "one feature does not import another feature" — and the code can then drift
away from that description without anybody noticing, because the tests still pass and
the description is prose that nothing reads.

This package reads a YAML file in the target repository that states those rules in a
form a machine can apply, walks the repository's Python source as a syntax tree, and
writes down every place the code sits somewhere the rule did not name.

WHAT IT DOES NOT DO — read this before adding anything
------------------------------------------------------
* **No score, no confidence number.** The only calibration this estate has run on a
  local reviewer measured 19% catch and 74% over-flag. A number from an uncalibrated
  instrument is a decoration.
* **No verdict.** Nothing here says aligned, misaligned, violation, pass or fail.
* **No severity.** Severity is a judgement about consequence and this cannot see
  consequence. If it is ever added it comes from the rules file, where a person put
  it, never from here.
* **No model, no network.** Python's standard library plus PyYAML. The only process
  it ever starts is one read-only ``git diff --name-only``, and only when it is asked
  to report on the files a range of commits touched. What it does can be proved by
  reading it, which is why it is in this form.
* **It changes nothing and blocks nothing.** It is a command that prints.

WHAT IT CANNOT SEE — stated up front, not buried
-------------------------------------------------
* Only Python, and only files that parse. A file with a syntax error is named as
  unparsed and skipped, never silently dropped.
* Only the shapes listed in ``checks.py``. A rule needing judgement — "is this
  business logic?", "does this module duplicate that one?" — cannot be expressed here
  and must not be forced into it. A rule naming a shape this program does not have is
  reported as **unsupported** and drives the exit code to 2; it is never reported as
  clean.
* Only what a single file's syntax tree shows. Names are not resolved across files and
  call graphs are not followed.
* Only what the rules file states. A repository with no rules file gets "could not
  run", never "clean".

WHY A SYNTAX TREE AND NOT A TEXT SEARCH
----------------------------------------
Because a text search cannot tell code from prose. api_test carries
``users = await db.execute(select(User))`` inside a docstring at
``src/db/dependencies.py:29``. A text search reports it. A syntax tree does not see
it at all. Any run can be checked against that one line to confirm the instrument is
reading code — and if it ever appears in a report, every number this has produced is
suspect.

RUNNING IT
----------
``python -m guardkit.conformance --repo /path/to/repo``. See ``cli.py`` for the flags
and for what each exit code means.

Two modes. By default it reports on the whole source tree. With ``--diff <range>`` it
reports only on the files that range of commits touched — every rule still runs over
the whole tree, because "nine of the eleven other query sites are in crud.py" is what
makes a finding readable, and that sentence needs the whole tree to be true.

RELATED
-------
``guardkit/qa/arch_conformance.py`` is the earlier version of this idea, written on
2026-08-22 against a four-rule draft rules file whose YAML shape (``says``, ``check``,
``source``) was superseded when api_test's architecture record was ruled on 2026-08-30.
This package reads the ruled shape (``rule``, ``signals``, ``source_sentence``), covers
ten shapes of check rather than three, and returns an exit code. The older module is
left where it is; nothing here changes it.
"""

from guardkit.conformance.engine import run
from guardkit.conformance.model import Report, RuleOutcome, Site
from guardkit.conformance.report import to_json, to_text

__all__ = ["run", "to_json", "to_text", "Report", "RuleOutcome", "Site"]
