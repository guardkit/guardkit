"""The command line.

::

    python -m guardkit.conformance --repo /path/to/repo
    python -m guardkit.conformance --repo /path/to/repo --json
    python -m guardkit.conformance --repo /path/to/repo --diff origin/main..HEAD
    python -m guardkit.conformance --repo /path/to/repo --rules /path/to/rules.yaml \
        --json-out /path/to/receipt.json

Exit codes, and they are the whole of what this command decides:

* **0** — it ran, and it has nothing to report.
* **1** — it ran, and there are findings to read. It still blocks nothing.
* **2** — it could not run everything it was asked to run: no rules file, a rules file
  it could not read, rules written for a different repository, or a rule naming a shape
  of check this program does not have. Exit 0 in that last case would be the program
  reporting success for work it never did.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from guardkit.conformance.engine import run
from guardkit.conformance.report import to_json, to_text
from guardkit.conformance.rules import DEFAULT_RULES_PATH


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m guardkit.conformance",
        description="Report where a repository's code sits relative to that "
                    "repository's own written architecture rules. Reports facts; "
                    "decides nothing; blocks nothing.")
    p.add_argument("--repo", required=True, type=Path,
                   help="the repository to read")
    p.add_argument("--rules", type=Path, default=None,
                   help=f"the rules file (default: <repo>/{DEFAULT_RULES_PATH})")
    p.add_argument("--diff", metavar="RANGE", default=None,
                   help="report only on the files this range of commits touched, e.g. "
                        "'abc123~1..abc123'. Every rule still runs over the whole source "
                        "tree, so the counts stay honest; findings outside the change are "
                        "counted and not listed.")
    p.add_argument("--json", action="store_true",
                   help="print the report as JSON instead of as text")
    p.add_argument("--json-out", type=Path, default=None,
                   help="also write the JSON report to this file")
    p.add_argument("--allow-foreign-rules", action="store_true",
                   help="run rules written for a different repository. For experiments; "
                        "on seven estate repositories in 2026-08 this produced 15 to 85 "
                        "observations each, all of them noise.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(args.repo, args.rules.resolve() if args.rules else None,
                 args.allow_foreign_rules, diff_range=args.diff)
    payload = to_json(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2) if args.json else to_text(report))
    return report.exit_code()


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main())
