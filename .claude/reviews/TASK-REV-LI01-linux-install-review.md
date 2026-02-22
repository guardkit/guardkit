# Review Report: TASK-REV-LI01 — Linux Install Analysis (Dell ProMax GB10, aarch64)

**Date**: 2026-02-22
**Reviewer**: Claude Code (automated review)
**Task**: TASK-REV-LI01
**Hardware**: Dell ProMax GB10, aarch64 / ARM64, Ubuntu, bash
**Install log**: `docs/reviews/linux_install/linux_insatall_1.md`
**Installer**: `installer/scripts/install.sh`

---

## Summary

5 issues were triaged (plus 1 discovered during code review). 2 require bug fixes, 2 are documentation/UX only, 1 is by-design, and 1 is a newly-discovered completions bug.

| # | Issue | Triage | Fix Task |
|---|-------|--------|----------|
| 1 | guardkit-py CLI not on PATH | **bug-fix-required** | TASK-FIX-LI01 (recommended) |
| 2 | Symlink `versions/latest` fails | **bug-fix-required** | TASK-FIX-LI02 (recommended) |
| 3 | Node.js missing — feature list not shown | documentation-only | — |
| 4 | Install dir `.agentecflow` vs CLI name `guardkit` | documentation-only | — |
| 5 | Backup of `.claude` on first install | by-design | — |
| 6 | Shell completions silently fail (NEW) | **bug-fix-required** | merge with TASK-FIX-LI01 |

---

## Issue 1 — CRITICAL BUG: guardkit-py CLI not on PATH

### Triage: `bug-fix-required`

### Root Cause

Confirmed by code inspection of `setup_shell_integration()` (lines 1260–1272 of `install.sh`).

The block written to `~/.bashrc` is:

```bash
# GuardKit
export PATH="$HOME/.agentecflow/bin:$PATH"
export AGENTECFLOW_HOME="$HOME/.agentecflow"
# Note: Config folder stays .agentecflow for methodology compatibility

# GuardKit completions (bash)
if [ -f "$HOME/.agentecflow/completions/guardkit.bash" ]; then
    source "$HOME/.agentecflow/completions/guardkit.bash"
fi
```

`$HOME/.local/bin` is **not added to PATH**. On Ubuntu/Debian Linux systems where `system site-packages` is not writeable (as seen at install log lines 24, 39, 69, 85, 167), pip defaults to user installation mode (`~/.local/lib/...`) and places all entry-point scripts in `~/.local/bin`. This is where `guardkit-py`, `guardkit`, `uvicorn`, `tqdm`, `httpx`, `openai`, `jsonschema`, `mcp`, `dotenv`, `f2py`, and `numpy-config` were all installed.

### Impact

After a fresh install, `guardkit-py` and `guardkit` are unreachable from a new terminal unless the user manually adds `~/.local/bin` to their PATH. The installer itself detects this at line 489 (`print_warning "guardkit-py CLI not found in PATH"`) but takes no corrective action.

### Proposed Fix

In `setup_shell_integration()`, add `$HOME/.local/bin` to PATH in the bash shell integration block. Additionally, perform a PATH-aware re-check of the CLI after shell integration is written to give a definitive "reachable after restart" vs "still not reachable" message.

```bash
# GuardKit
export PATH="$HOME/.local/bin:$HOME/.agentecflow/bin:$PATH"
export AGENTECFLOW_HOME="$HOME/.agentecflow"
```

Note: `~/.local/bin` should be listed **before** `~/.agentecflow/bin` to ensure pip-installed scripts take precedence, mirroring standard Ubuntu `.profile` behaviour.

### Verification

Run install in a clean shell where `~/.local/bin` is absent from PATH (e.g. `env -i HOME=$HOME PATH=/usr/bin:/bin bash -l ./install.sh`), then open a new terminal and confirm `which guardkit-py` resolves.

---

## Issue 2 — BUG: `versions/latest` symlink fails (`ln` target is empty string)

### Triage: `bug-fix-required`

### Root Cause

Confirmed by code inspection. There is a **variable name typo** throughout the installer.

- **Defined at line 17**: `AGENTECFLOW_VERSION="2.0.0"` (spelt A-G-E-N-T-**E**-C-F-L-O-W)
- **Used in version management functions**: `$AGENTICFLOW_VERSION` (spelt A-G-E-N-T-**I**-C-F-L-O-W — note 'I' not 'E')

The two spellings differ at character position 6. `AGENTICFLOW_VERSION` is **never assigned** in the script, so it expands to the empty string `""` in bash.

Affected lines using the undefined variable:

| Line | Code | Effect |
|------|------|--------|
| 535 | `mkdir -p "$INSTALL_DIR/versions/$AGENTICFLOW_VERSION"` | Creates `versions/` only, no version subdirectory |
| 1294 | `"version": "$AGENTICFLOW_VERSION"` | Config JSON gets empty version string |
| 1420 | `echo "$AGENTICFLOW_VERSION" > ".../versions/current"` | `current` file contains empty string |
| 1423 | `ln -sf "$AGENTICFLOW_VERSION" ".../versions/latest"` | `ln` target is `""` → **fails** with "No such file or directory" |
| 1426 | `cat > ".../versions/$AGENTICFLOW_VERSION/info.json"` | Writes to `versions//info.json` (= `versions/info.json`) |
| 1428 | `"version": "$AGENTICFLOW_VERSION"` | `info.json` gets empty version string |

The `set -e` at the top of the script should cause the script to exit on the `ln` failure, but because `create_version_management` is called late in `main()` and the `ln` command is not guarded with `set +e`, the script terminates abruptly after the error — silently, without printing the final summary or returning a non-zero exit code to the user (the shell prompt immediately returns as seen on install log line 349).

### Impact

- The `latest` symlink is never created, breaking any upgrade/rollback logic that resolves via `versions/latest`
- The `current` file contains an empty string (not `2.0.0`)
- The `info.json` files contain empty version strings
- The install exits without printing `print_summary()`, so the user misses the "Next Steps" guidance
- Silently broken — no visible error banner

### Proposed Fix

Replace all uses of `$AGENTICFLOW_VERSION` with `$AGENTECFLOW_VERSION` (the correctly-defined variable) at lines 535, 1294, 1420, 1423, 1426, and 1428.

Additionally, add defensive handling around the `ln` call to surface a clear error rather than relying on `set -e` silent exit.

### Verification

After fix, confirm:
1. `cat ~/.agentecflow/versions/current` outputs `2.0.0`
2. `readlink ~/.agentecflow/versions/latest` outputs `2.0.0`
3. `~/.agentecflow/versions/2.0.0/info.json` exists and contains `"version": "2.0.0"`
4. Installation completes with the full summary printed

---

## Issue 3 — Node.js not found warning lacks feature list

### Triage: `documentation-only`

### Root Cause

The warning at line 174:

```bash
print_warning "Node.js not found. Some features may be limited."
```

...does not enumerate which features or templates require Node.js.

### Impact

Minor UX issue. Users on Node.js-free machines (like this aarch64 Ubuntu device with no npm in PATH) cannot determine whether they need to install Node.js for their intended use case.

### Proposed Fix

Update the warning message to list affected features explicitly. Based on the template names in the installer:

```bash
print_warning "Node.js not found. The following templates require Node.js:"
echo "    react-typescript, nextjs-fullstack, react-fastapi-monorepo"
echo "  Features not requiring Node.js: fastapi-python, default"
```

This is documentation-level change only — no functional impact.

---

## Issue 4 — Install directory `.agentecflow` vs public name `guardkit`

### Triage: `documentation-only`

### Observation

The installer targets `~/.agentecflow` (a legacy name from when the product was called "Agentecflow"), while the current public-facing package name is `guardkit-py` and CLI commands are `guardkit`, `guardkit-init`, `gk`, `gki`. A user searching for `~/.guardkit` would not find it.

This is also referenced in the shell integration block comment: `# Note: Config folder stays .agentecflow for methodology compatibility`.

### Impact

Documentation and discoverability only. No functional impact — the installer is internally consistent about `~/.agentecflow`. The `guardkit doctor` command correctly reports `~/.agentecflow` as the home directory.

### Decision Required

Is a rename to `~/.guardkit` planned for a future release? If yes, issue a deprecation notice in the current installer output. If no, update the public documentation to state that GuardKit installs to `~/.agentecflow`.

---

## Issue 5 — Backup of existing `.claude` directory

### Triage: `by-design`

### Observation

The installer correctly detects and backs up the existing `.claude` directory:

```
⚠ Found existing installations: .claude
ℹ Creating backup of .claude at /home/richardwoollcott/.claude.backup.20260222_122430
✓ Backup created: /home/richardwoollcott/.claude.backup.20260222_122430
```

This is intentional and the logic in `backup_existing()` is correct. The backup preserves the user's prior Claude config.

### Recommendation

Add a note to the post-install docs / `INSTALL.md` explaining that a prior `.claude` directory is backed up (not deleted) so users know where to find their old configuration if needed.

---

## Issue 6 (NEW) — Shell completions silently fail to load

### Triage: `bug-fix-required` (merge into TASK-FIX-LI01)

### Root Cause

A filename mismatch between where the completions file is written and where the shell integration sources it:

- **`install_completions()`** (line 1335) writes to: `$INSTALL_DIR/completions/agentecflow.bash`
- **`setup_shell_integration()`** (line 1269) sources: `$HOME/.agentecflow/completions/guardkit.bash`

The file is named `agentecflow.bash` but the `source` command looks for `guardkit.bash`. The `if [ -f ... ]` guard silently suppresses the missing-file error, so no warning is shown. Bash completions for `guardkit` / `guardkit-init` / `gk` / `gki` do not load.

Additionally, the completions file itself (lines 1406–1408) registers completions for `agentecflow` and `af` — commands that no longer exist — not for `guardkit`, `guardkit-init`, `gk`, or `gki`.

### Proposed Fix (merge into TASK-FIX-LI01)

1. Rename the created completions file from `agentecflow.bash` to `guardkit.bash`
2. Update `_agentecflow()` → `_guardkit()` and register completions for `guardkit`, `guardkit-init`, `gk`, `gki`

---

## Key Questions Answered

| Question | Answer |
|----------|--------|
| Does the shell integration block include `export PATH="$HOME/.local/bin:$PATH"`? | **No** — this is the root cause of Issue 1 |
| What version variable is passed to `ln` and why is it empty? | `$AGENTICFLOW_VERSION` — defined nowhere; correct variable is `$AGENTECFLOW_VERSION` |
| Does the installer re-check CLI availability after sourcing the new PATH? | No — `install_python_package()` checks PATH at install time, cannot re-check for new shell |
| Can we list Node.js-required features in the warning message? | Yes — `react-typescript`, `nextjs-fullstack`, `react-fastapi-monorepo` |
| Is `.agentecflow` the intended permanent name? | Decision required — see Issue 4 |

---

## Recommended Follow-up Tasks

### TASK-FIX-LI01 — Fix installer PATH and completions for Linux user installs
- Add `$HOME/.local/bin` to PATH in `setup_shell_integration()` shell block
- Fix completions file name: `agentecflow.bash` → `guardkit.bash`
- Fix completions registrations to target `guardkit`, `guardkit-init`, `gk`, `gki`
- Update Node.js warning to list affected templates

### TASK-FIX-LI02 — Fix version management variable typo
- Replace all `$AGENTICFLOW_VERSION` → `$AGENTECFLOW_VERSION` (lines 535, 1294, 1420, 1423, 1426, 1428)
- Add `set +e` / error handling around `ln` call to produce a clear error if it still fails
- Verify `versions/current`, `versions/latest`, and `versions/2.0.0/info.json` all have correct content post-fix

### DOC — Update documentation
- Note that GuardKit installs to `~/.agentecflow` (legacy name)
- Note that `.claude` backup is created at `.claude.backup.<timestamp>` on re-install
- Clarify which templates require Node.js

---

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| Root cause of CLI-not-on-PATH identified and fix proposed | ✅ Complete |
| Root cause of symlink failure identified and fix proposed | ✅ Complete |
| Node.js missing feature list documented | ✅ Complete |
| All issues triaged | ✅ Complete |
| At least one concrete fix task created per `bug-fix-required` issue | ✅ TASK-FIX-LI01 + TASK-FIX-LI02 recommended |
| Review report written | ✅ This document |
