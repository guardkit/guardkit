#!/usr/bin/env bash
#
# Install GuardKit's committed git hooks into this clone — TASK-FIX-CIGUARD01.
#
# Currently installs the direct-to-main collection guard (scripts/pre-push.sh)
# as .git/hooks/pre-push via a symlink, so edits to the committed script take
# effect immediately with no re-install.
#
# Usage:
#   ./scripts/install-git-hooks.sh
#
# Idempotent: safe to run repeatedly. Re-points the symlink if it already
# exists. Refuses to clobber a pre-existing NON-symlink pre-push hook (so a
# hand-written local hook is never silently destroyed).
#
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$(git rev-parse --git-path hooks)"   # honours worktrees / core.hooksPath-free clones
SRC="${REPO_ROOT}/scripts/pre-push.sh"
DEST="${HOOKS_DIR}/pre-push"

if [[ ! -f "$SRC" ]]; then
  echo "install-git-hooks: source guard not found: $SRC" >&2
  exit 1
fi

chmod +x "$SRC"
mkdir -p "$HOOKS_DIR"

# Refuse to overwrite a real (non-symlink) existing hook.
if [[ -e "$DEST" && ! -L "$DEST" ]]; then
  echo "install-git-hooks: $DEST already exists and is NOT a symlink." >&2
  echo "                   Refusing to clobber it. Move it aside and re-run." >&2
  exit 1
fi

# Relative symlink so it survives the repo being moved/renamed.
REL_SRC="$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$SRC" "$HOOKS_DIR" 2>/dev/null || echo "$SRC")"
ln -sf "$REL_SRC" "$DEST"
chmod +x "$DEST" 2>/dev/null || true

echo "✅ installed pre-push collection guard:"
echo "   $DEST -> $REL_SRC"
echo "   (bypass a single push with: git push --no-verify)"
