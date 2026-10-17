# Security Check Guide

Rewritten 17 October 2026. Earlier versions of this page described a "quick security
scan" (Phase 4.3) and a "full security review" (Phase 2.5C) with `security:` settings.
Nothing in a build ever called them, so they never ran. They have been removed, and this
page describes the check that replaced them.

## What runs

Every AutoBuild task gets one security check on the files it changes. It is an ordinary
`assert_command` conformance rule, `security-check`, built by
`guardkit/orchestrator/security_check.py` and added in `snapshot_task_conformance` beside
the architecture rules check. It is frozen before the first turn, so the Player cannot
change it, and a failure reaches the Player through the Coach as one must-fix issue on the
next turn.

The check runs whenever the build image holds Gitleaks or OSV-Scanner. There is no switch
and no project setting. With neither tool installed, no rule is added and a build is
unchanged.

It reads only the files the task changed since it started (`git diff --name-only <start>`
plus files git is not yet tracking, with `.guardkit/` left out).

## Check 1: secrets

Gitleaks runs in `dir` mode over copies of the changed text files, with its built-in
rules, `--redact` and `--ignore-gitleaks-allow`. Each finding names the file, the line and
the kind of secret, never the value.

To fix one, read the secret from the environment or a secret file. In a test, build the
token or key at run time instead of writing it as a literal.

## Check 2: dependencies

This runs only when the task changed a file OSV-Scanner reads (lockfiles and manifests, by
the scanner's own recognition). OSV-Scanner reads the head and starting versions of those
files.

| Finding | Result |
|---------|--------|
| A known malicious package (`MAL-` advisory) | blocks |
| A new advisory with a severity score of 7.0 or more | blocks |
| An advisory already there, when the task changed that package's version and it still applies | blocks |
| A new advisory scoring under 7.0 | printed as advice |
| An old advisory in a package the task did not change | not listed |
| A package new in this change, first published under 30 days ago (deps.dev) | blocks |

Each advisory lists every fixed version OSV records for it. The check does not compare
versions itself; the Player picks one and the next turn checks it.

## Repository settings are not read

The Player can edit anything in the repository, so no scanner reads settings from it.
`.gitleaks.toml`, `.gitleaksignore` and `osv-scanner.toml` are never copied for scanning,
OSV-Scanner is given an empty factory setting (`/opt/factory-security/osv-scanner.toml` in
the image), Gitleaks' ignore-file lookup is pointed at an empty factory folder
(`/opt/factory-security/gitleaks-ignore/`), and inline `gitleaks:allow` comments are
ignored. The command runs as `python -I -m ...` with the scanners named by absolute paths,
so files the Player writes cannot replace the checker.

## It never becomes a wall

A missing tool, an unreachable network, or a scanner that errors or runs out of time
prints "<what> was not checked: <why>. Nothing was checked, which is not the same as
clean." and that part passes. The command keeps a 200-second budget inside the rule's
300-second limit. Confirmed findings from the parts that finished still block.

## Wider checks

Broader code-pattern rules (Opengrep), container configuration rules and a whole-history
secrets scan run in the factory's nightly sweep, not on each change. A project that wants
more on each change, such as gosec or Bandit, can declare its own `assert_command` rule.
