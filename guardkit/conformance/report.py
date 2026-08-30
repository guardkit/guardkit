"""Saying what was seen: one JSON object, and one short page of plain text.

Both renderings state facts and stop there. There is no score, no confidence number,
no severity, and no word that concludes — nothing here says aligned, misaligned,
violation, pass or fail. A rule that matched something in a place the rule did not
name produces a *finding*: the rule's own sentence, where the sentence came from, the
file and line, what is there, and how the checker established it. Whether that should
change is a judgement, and it belongs to whoever reads this.
"""

from __future__ import annotations

from typing import Any

from guardkit.conformance.model import AT_HOME, ELSEWHERE, EXCEPTED, UNSUPPORTED, Report

LINE = "=" * 78


def _source_line(source: dict[str, Any]) -> str:
    doc = source.get("document") or "(no document named)"
    section = source.get("section")
    sentence = source.get("sentence") or ""
    where = f"{doc}" + (f", section \"{section}\"" if section else "")
    return f"{where} — \"{sentence}\""


def to_json(report: Report) -> dict[str, Any]:
    out: dict[str, Any] = {
        "checker": "guardkit.conformance",
        "reports": "facts only — no score, no verdict, no severity",
        "repo": report.repo,
        "repo_identified_as": report.repo_identified_as,
        "rules_file": report.rules_path,
        "rules_written_for": report.rules_written_for,
        "ran": report.ran,
        "could_not_run": report.could_not_run,
        "narrowed_to_the_files_this_change_touched": report.diff_scope,
        "files_scanned": report.files_scanned,
        "files_unparsed": report.files_unparsed,
        "notes": report.notes,
        "rules": [],
        "findings": [],
        "findings_elsewhere_in_the_repository": 0,
        "unsupported_rules": [],
        "exit_code": report.exit_code(),
    }
    for rule in report.rules:
        counts = rule.counts()
        entry: dict[str, Any] = {
            "rule_id": rule.rule_id,
            "status": rule.status,
            "rule_says": rule.says,
            "rule_source": rule.source,
            "check_kind": rule.kind,
            "scope": rule.scope,
            "examined": rule.examined,
            "signals_inherited_from_another_rule": rule.inherited_signals,
            "sites_matched": len(rule.sites),
            "sites_by_placement": counts,
            "all_sites": [{"at": s.where, "placement": s.placement} for s in rule.sites],
            "findings_in_the_whole_repository": len(rule.findings),
        }
        if rule.status == UNSUPPORTED:
            entry["unsupported_reason"] = rule.unsupported_reason
            out["unsupported_rules"].append(
                {"rule_id": rule.rule_id, "check_kind": rule.kind,
                 "reason": rule.unsupported_reason})
        out["rules"].append(entry)

        for site in rule.reported_findings(report.narrowed):
            out["findings"].append({
                "rule_id": rule.rule_id,
                "rule_says": rule.says,
                "rule_source": rule.source,
                "observed_at": site.where,
                "in_this_change": site.in_this_change,
                "file": site.path,
                "line": site.line,
                "observed": site.observed,
                "enclosing_function": site.enclosing,
                "how_observed": site.how_observed,
                "also_at": site.also_at,
                "same_repo_comparison": {
                    "sites_matching_this_pattern": len(rule.sites),
                    "sites_in_the_file_the_rule_names": counts[AT_HOME],
                    "sites_named_as_exceptions_in_the_rules_file": counts[EXCEPTED],
                    "sites_in_neither": counts[ELSEWHERE],
                    "where_the_other_sites_are": sorted(
                        {s.path for s in rule.sites if s.placement == AT_HOME}),
                },
            })
    out["findings_elsewhere_in_the_repository"] = (
        len(report.all_findings) - len(report.reported_findings))
    return out


def to_text(report: Report) -> str:
    L: list[str] = [f"Architecture rules check — {report.repo}"]
    if report.could_not_run or not report.ran:
        L.append("")
        L.append("COULD NOT RUN. Nothing was checked, which is not the same as clean.")
        for note in report.notes:
            L.append(f"  {note}")
        return "\n".join(L)

    L.append(f"Rules file: {report.rules_path}")
    L.append(f"Python files read as syntax trees: {report.files_scanned}"
             + (f"; {len(report.files_unparsed)} would not parse"
                if report.files_unparsed else ""))
    for u in report.files_unparsed:
        L.append(f"  DID NOT PARSE — nothing below covers it: {u['path']} — {u['reason']}")
    for note in report.notes:
        L.append(f"  {note}")

    for rule in report.rules:
        counts = rule.counts()
        findings = rule.reported_findings(report.narrowed)
        L.append("")
        L.append(LINE)
        L.append(f"{rule.rule_id}  —  {rule.status.upper()}"
                 f"   ({rule.kind}, scope: {rule.scope})")
        L.append(f"  says:   {rule.says}")
        L.append(f"  source: {_source_line(rule.source)}")
        if rule.inherited_signals:
            L.append(f"  borrowed from another rule, as this rule's own words ask: "
                     f"{', '.join(rule.inherited_signals)}")
        if rule.status == UNSUPPORTED:
            L.append(f"  NOT CHECKED: {rule.unsupported_reason}")
            continue
        examined = ", ".join(f"{k}: {v}" for k, v in rule.examined.items()) or "nothing"
        L.append(f"  looked at — {examined}")
        if not rule.sites:
            L.append("  nothing in this repository matched this rule's pattern.")
        else:
            L.append(f"  matched {len(rule.sites)} site(s): {counts[AT_HOME]} in the file "
                     f"the rule names, {counts[EXCEPTED]} named as exceptions in the rules "
                     f"file, {counts[ELSEWHERE]} in neither.")
        for site in findings:
            L.append("")
            L.append(f"  {site.where}")
            L.append(f"      observed:     {site.observed}"
                     + (f", inside {site.enclosing}()" if site.enclosing else ""))
            for extra in site.also_at:
                L.append(f"      also here:    {extra}")
            L.append(f"      how observed: {site.how_observed}")
            L.append(f"      the rule says: {rule.says}")
        if findings:
            others = [s for s in rule.sites if s.placement != ELSEWHERE]
            L.append("")
            L.append("  Every other place in this repository matching the same pattern:")
            for s in others:
                if s.placement == AT_HOME:
                    L.append(f"      {s.where}   (the file the rule names)")
                else:
                    L.append(f"      {s.where}   (an exception: {s.exception_reason})")
            if not others:
                L.append("      there are none.")

    L.append("")
    L.append(LINE)
    findings = report.reported_findings
    unsupported = report.unsupported
    L.append(f"{len(findings)} finding(s) across {len(report.rules)} rule(s); "
             f"{len(unsupported)} rule(s) could not be checked.")
    elsewhere_count = len(report.all_findings) - len(findings)
    if report.narrowed:
        L.append(f"Only the {len(report.diff_scope or [])} file(s) this change touched "
                 f"are listed above; {elsewhere_count} further finding(s) sit elsewhere "
                 f"in this repository and were not listed.")
    if unsupported:
        L.append("  Rules that could not be checked — these are NOT clean:")
        for rule in unsupported:
            L.append(f"      {rule.rule_id}: {rule.unsupported_reason}")
    L.append("This is a list of observations. It is not a verdict, a score, or a count "
             "of defects, and it blocks nothing.")
    L.append(f"Exit code {report.exit_code()} — "
             + {0: "ran, nothing to report.",
                1: "ran, and there is something to read above.",
                2: "could not run everything it was asked to run."}[report.exit_code()])
    return "\n".join(L)
