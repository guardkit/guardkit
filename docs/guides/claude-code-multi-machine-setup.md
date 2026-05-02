# Claude Code Setup — Multi-Machine (MacBook + GB10)

Operational guide for working on the appmilla_github repos from either the MacBook
or the GB10 (`promaxgb10-41b1`). Covers Anthropic Agent Skills (a.k.a.
"langchain-skills"), `.claude/settings.json` hygiene, and how it all interacts with
the Graphiti MCP.

**Companion doc**: [graphiti-gb10-deployment.md](graphiti-gb10-deployment.md) covers
the Graphiti server stack itself; this doc covers the Claude Code client side.

---

## TL;DR

1. Install Anthropic Skills with `npx skills add ...` — **never** add
   `langchain-skills` to `enabledPlugins`. It is not a plugin.
2. Install `gh` and run `gh auth login` on each machine — without it, every
   `git push` from the GB10 fails with `could not read Username for
   'https://github.com'`. If you use a fine-grained PAT, **set Contents:
   Read and write** per repo, otherwise pushes 403.
3. Don't put machine-specific absolute paths (`/Users/...`, `/home/...`) in
   committed `.claude/settings.json`. Use `.claude/settings.local.json` for
   per-machine overrides — it's gitignored.
4. `.mcp.json` for Graphiti must be `http://promaxgb10-41b1:8004/mcp` —
   no trailing slash.
5. Install [`uv`](https://astral.sh/uv) on every machine that runs
   `guardkit autobuild`. Any target repo whose `pyproject.toml` declares
   `[tool.uv.sources]` (sibling-path / git overrides) **hard-fails at
   bootstrap** without `uv` on PATH — pip cannot honour those overrides
   and silently producing a broken venv would be worse than failing fast.
6. Run `/doctor` on each machine after cloning a repo. Apply the fixes below
   if it complains.

---

## Skills vs Plugins vs MCPs — three different things

Claude Code has three extensibility systems with overlapping vocabulary. They
are easy to confuse — and on this setup, the confusion has caused recurring
`/doctor` failures.

| System | What it is | How installed | Where it lives | Config entry |
|--------|-----------|---------------|----------------|--------------|
| **Skills** | Markdown reference material loaded into context on demand | `npx skills add <repo>` | `~/.claude/skills/` | none — auto-loaded |
| **Plugins** | Bundles of agents/commands/hooks distributed via marketplaces | `claude plugin install <name>@<marketplace>` | `~/.claude/plugins/` | `enabledPlugins` |
| **MCP servers** | External processes Claude Code calls over stdio or HTTP | per-repo `.mcp.json` | (anywhere) | `mcpServers` in `.mcp.json` |

`langchain-skills` (the package the LangChain team publishes for DeepAgents) is
in the **first** category — Skills. There is **no** Claude Code plugin called
`langchain-skills` and no marketplace called `langchain-skills`. Adding
`"langchain-skills@langchain-skills": true` to `enabledPlugins` will produce:

```
Plugin langchain-skills not found in marketplace langchain-skills
```

If you see that, the fix is always **delete the entry** — never "install the
marketplace", because there isn't one to install.

---

## Installing langchain-skills (Anthropic Skills) — both machines

### Prerequisite: Node.js (npm/npx)

The `skills` CLI ships via npm, so you need Node.js available. We use **nvm**
on both machines for consistency — it installs in user space, no sudo, and
keeps Node easy to upgrade. The Graphiti deployment doc already assumes nvm
on the Mac for the same reason.

If `which npx` returns nothing, install nvm first:

```bash
# 1. Install nvm (writes ~/.nvm/, appends source lines to ~/.bashrc)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# 2. Load nvm into the current shell (new shells pick it up automatically
#    via the lines appended to ~/.bashrc)
export NVM_DIR="$HOME/.nvm" && \. "$NVM_DIR/nvm.sh"

# 3. Install latest LTS Node (currently v24.x)
nvm install --lts
```

Verify with `which node npm npx` — all three should resolve under
`~/.nvm/versions/node/<version>/bin/`.

> **macOS note**: same nvm install line works on macOS. Claude Desktop on the
> Mac additionally needs the **absolute** path to `npx` (e.g.
> `/opt/homebrew/bin/npx`) in its config — see the Claude Desktop section of
> [graphiti-gb10-deployment.md](graphiti-gb10-deployment.md#client-configuration-summary).

### Install the skills

```bash
npx skills add langchain-ai/langchain-skills --skill '*' --yes --global
```

What happens (as of 2026-04-25, `skills` CLI v-current):

- Downloads the `skills` CLI on demand (no global install needed)
- Clones https://github.com/langchain-ai/langchain-skills
- Copies all 11 skill markdown directories into **`~/.agents/skills/`**
  (the agent-agnostic location — shared across Claude Code, Codex, Cursor,
  Cline, Amp, etc.)
- **Symlinks** each skill into `~/.claude/skills/` so Claude Code finds them
- Registers globally so every project sees them

Skills load automatically — no `.claude/settings.json` entry is needed or
appropriate. The 11 skills currently in the langchain-skills bundle:

```
deep-agents-core              langchain-middleware
deep-agents-memory            langchain-rag
deep-agents-orchestration     langgraph-fundamentals
framework-selection           langgraph-human-in-the-loop
langchain-dependencies        langgraph-persistence
langchain-fundamentals
```

### Verify

```bash
# Symlinks Claude Code will pick up
ls ~/.claude/skills/

# The actual skill content
ls ~/.agents/skills/
```

Both should list the 11 directories above. The `~/.claude/skills/` entries
should be symlinks (`ls -la` shows `-> ../../.agents/skills/<name>`).

### When skills go missing

Skills have been lost twice on this setup when `~/.claude/` was restructured —
once on 2026-03-17 (recovered from `~/.claude.backup.20260317_101318/skills/`).
If you have a backup directory matching that pattern, restore is:

```bash
cp -r ~/.claude.backup.YYYYMMDD_HHMMSS/skills ~/.claude/skills
```

Otherwise re-run `npx skills add ...` above — it's idempotent.

> **Note on the new layout**: backups predating the agent-agnostic split
> (i.e. before mid-2025) contain skill *content* directly under
> `.claude/skills/`. Newer installs put content under `~/.agents/skills/`
> with symlinks from `~/.claude/skills/`. Either layout works for Claude
> Code; the symlink form is how fresh `npx skills add` lays things out today.

### Per-machine state (as of 2026-04-25)

- **MacBook**: skills installed (per project history)
- **GB10**: skills installed today — 11 skills under `~/.agents/skills/`,
  symlinked into `~/.claude/skills/`. Node v24.15.0 LTS via nvm v0.40.1.

---

## GitHub CLI (gh) — both machines

Why it matters: Claude Code session pushes go through the same `git push`
mechanism as terminal pushes, which means the user's git credential setup
on each machine determines whether autonomous agents can ship work or get
stuck at "auth failed". On the GB10 specifically, no GitHub SSH key is
configured (`ssh -T git@github.com` returns "Permission denied (publickey)"),
no `~/.netrc`, no credential helper — so without `gh`, every `git push` to
github.com fails with `fatal: could not read Username for 'https://github.com'`.

`gh` solves this by registering itself as a credential helper for HTTPS
remotes. Once `gh auth login` succeeds, `git push` Just Works for every repo
the token covers.

### Install — GB10 (Ubuntu 24.04 noble, aarch64/arm64)

The official Debian/Ubuntu apt repository auto-detects architecture via
`dpkg --print-architecture`, so the same one-liner ships arm64 packages on
the GB10. Source:
[github.com/cli/cli/blob/trunk/docs/install_linux.md](https://github.com/cli/cli/blob/trunk/docs/install_linux.md).

```bash
(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
    && sudo mkdir -p -m 755 /etc/apt/keyrings \
    && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    && cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && sudo mkdir -p -m 755 /etc/apt/sources.list.d \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && sudo apt update \
    && sudo apt install gh -y
```

Subsequent updates: `sudo apt update && sudo apt install gh`.

### Install — MacBook

```bash
brew install gh
```

### Authenticate

```bash
gh auth login
```

Prompts:
- GitHub.com (not Enterprise)
- HTTPS (not SSH)
- "Authenticate Git with your GitHub credentials?" → **Yes**
- Login method:
  - **"Login with a web browser"** if a browser is reachable (GB10 over
    SSH from a Mac: copy the one-time code, open the URL on your laptop,
    paste the code, approve)
  - **"Paste an authentication token"** if headless and you already have
    a PAT — see "Tokens" below for what scopes to use

Verify with `gh auth status`. A healthy entry shows:
```
github.com
  ✓ Logged in to github.com account <username> (keyring)
  - Active account: true
  - Git operations protocol: https
  - Token: github_pat_11... (or ghp_... for classic)
```

Then `git push` to any github.com remote will succeed without further
prompting — `gh` registers itself as a credential helper and supplies the
token transparently.

### Tokens — fine-grained PAT vs classic PAT (the gotcha that cost us 30 min on 2026-04-25)

GitHub offers two PAT types and they behave **very differently** for
multi-repo workflows:

| | Fine-grained PAT (`github_pat_11...`) | Classic PAT (`ghp_...`) |
|---|---|---|
| Per-repo selection | ✅ explicit allowlist | ❌ all your repos |
| Per-permission granularity | ✅ Contents / Issues / Pull-requests / etc. each Read or R+W | ❌ flat scopes (`repo`, `workflow`, etc.) |
| `git push` requires | **Contents: Read and write** on each target repo | `repo` scope |
| Default Contents permission on creation | **Read only** | n/a |

**The trap**: a fresh fine-grained PAT created via the "what scopes do
I need?" UI defaults Contents to *Read*. `git fetch` works, `gh repo view`
works, the API can confirm your account has admin rights — but `git push`
returns:

```
remote: Permission to <org>/<repo>.git denied to <username>.
fatal: ... The requested URL returned error: 403
```

And `gh api -X POST repos/<org>/<repo>/...` returns:

```
"Resource not accessible by personal access token" (HTTP 403)
```

That second message is GitHub's specific wording for **fine-grained PAT
missing a permission**. If you see "Resource not accessible by personal
access token", the answer is always to add the missing permission — it is
NOT an account-level access problem.

**Fix**: edit the token at https://github.com/settings/personal-access-tokens,
set **Contents: Read and write** for each target repo, save. The keychain
entry stays valid; no need to re-run `gh auth login`. (If you want the
agent to open issues/PRs, also set Issues: R+W and Pull requests: R+W.)

**Recommended for this setup**: classic PAT with `repo` + `workflow`
scopes for the GB10's day-to-day token. Fine-grained PATs are great for
narrow agent-specific tokens (e.g. a CI bot scoped to one repo), but for
a "I work across guardkit/guardkit, guardkit/forge, guardkit/nats-core,
guardkit/nats-infrastructure, ..." workflow they're more friction than
they're worth.

### Per-machine state (as of 2026-04-25)

- **MacBook**: gh installed long-term (per Homebrew history)
- **GB10**: gh `2.x` installed today via the apt repo above; logged in as
  `RichWoollcott` via fine-grained PAT after correcting the Contents
  permission. Both `guardkit/guardkit` and `guardkit/forge` push-tested
  green.

---

## uv (Astral Python package manager) — both machines

Why it matters: GuardKit's environment bootstrap (`environment_bootstrap.py`)
inspects every target repo's `pyproject.toml`. If it finds a
`[tool.uv.sources]` table — used to point a dep at a sibling worktree, a
local path, or a git ref instead of PyPI — it raises
`UvSourcesRequireUvError` *before any pip work runs* unless `uv` is on
PATH. Plain pip silently ignores `[tool.uv.sources]`, which would fetch
`nats-core` (or whatever) from PyPI instead of `../nats-core`, producing
a venv where imports succeed but the wrong code runs. Failing fast at
bootstrap is the correct behaviour; the fix is to install uv. (The
hard-fail was introduced in TASK-FIX-F09A2; TASK-FIX-FD32 later
adjusted the `uv.lock` install command but did not change this gate.)

Affected repos in this fleet: any with `[tool.uv.sources]` in
`pyproject.toml`. As of 2026-05-02 that includes `forge` (overrides
`nats-core` to `../nats-core`). Grep before assuming a repo is exempt:

```bash
# Run from ~/Projects/appmilla_github
for d in */pyproject.toml; do
  grep -l "^\[tool\.uv\.sources\]" "$d" 2>/dev/null && echo "  ↑ needs uv on host"
done
```

`install.sh` does **not** install uv — it never has. You must install it
explicitly on each host that runs `guardkit autobuild`.

### Install — GB10 (Ubuntu 24.04 noble, aarch64/arm64)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# uv installs to ~/.local/bin/ — load it into the current shell:
source ~/.local/bin/env
# New shells pick it up automatically (the installer writes to ~/.bashrc).
which uv && uv --version
```

### Install — MacBook

```bash
brew install uv
# or, matching the GB10 method:
curl -LsSf https://astral.sh/uv/install.sh | sh
which uv && uv --version
```

### Symptom if you skipped this

`guardkit autobuild feature FEAT-XXX` (or `task TASK-XXX`) exits at the
worktree-bootstrap phase with:

```
ERROR ... Bootstrap hard-fail (uv-sources require uv): /.../pyproject.toml
declares [tool.uv.sources] but `uv` is not on PATH. pip cannot honour
these sibling-source overrides — installing would silently produce a
broken environment. Fix by installing uv (https://astral.sh/uv) or
removing the [tool.uv.sources] block from pyproject.toml.
```

If `which uv` works in your interactive shell but autobuild still errors,
the venv guardkit was launched from has a stripped PATH — confirm with
`env | grep '^PATH=' ` in the same shell that runs `guardkit`, and either
re-launch from a shell that has uv on PATH or symlink uv into a directory
that's already on the bootstrap PATH (e.g. `/usr/local/bin`).

### Per-machine state (as of 2026-05-02)

- **MacBook**: uv installed long-term (Homebrew).
- **GB10**: uv **not yet installed**; surfaces as the FEAT-DEA8 bootstrap
  hard-fail in
  `forge/docs/history/autobuild-FEAT-FORGE-010-fail-run-1-history.md`.
  Install via the curl one-liner above before the next autobuild run.

---

## .claude/settings.json hygiene

Project `.claude/settings.json` is **committed to git** — it applies on every
machine that clones the repo. Two failure modes recur:

### Failure mode 1: stale `enabledPlugins` references

```json
"enabledPlugins": {
  "langchain-skills@langchain-skills": true
}
```

**Always wrong** — see "Skills vs Plugins" above. Delete the entry; if
`enabledPlugins` becomes empty, delete the whole block. No real plugin
functionality is lost because none was ever installed.

### Failure mode 2: hardcoded absolute paths

These two machines have different home directory roots:

- **MacBook**: `/Users/richardwoollcott/...`
- **GB10**: `/home/richardwoollcott/...`

A path that hardcodes one will silently never match on the other. Concrete
examples that have been seen in the wild:

```json
{
  "permissions": {
    "allow": [
      "Bash(rm /Users/richardwoollcott/.../foo.md)",        // breaks on GB10
      "Read(//Users/richardwoollcott/.agentecflow/agents/**)" // breaks on GB10
    ],
    "additionalDirectories": [
      "/Users/richardwoollcott/.../reviews"                  // breaks on GB10
    ]
  }
}
```

**Recommended approaches**, in order of preference:

1. **Avoid absolute paths in committed configs.** Most permission entries can
   use repo-relative paths or shell glob patterns that work anywhere. Prefer
   `Read(.claude/agents/**)` over the absolute form.
2. **If you must use absolute paths**, put them in `.claude/settings.local.json`
   — gitignored per the GuardKit template, so each machine's copy can use that
   machine's paths.
3. **If neither works** (e.g., a path that genuinely is the same logical location
   but different absolute path), document the cross-machine mapping in the
   project's CLAUDE.md and accept the maintenance cost of keeping the two in
   sync. This is what we currently do for some entries; it's a known wart.

### Quick audit on either machine

```bash
# Run from ~/Projects/appmilla_github

# Find committed settings that still reference the wrong-platform paths
for d in */.claude/settings.json; do
  # On Linux / GB10 — these break here:
  grep -l "/Users/richardwoollcott" "$d" 2>/dev/null && echo "  ↑ stale macOS paths"
  # On macOS — these break there:
  grep -l "/home/richardwoollcott" "$d" 2>/dev/null && echo "  ↑ stale Linux paths"
done

# Find committed settings with the broken plugin entry
for d in */.claude/settings.json; do
  grep -l "langchain-skills@langchain-skills" "$d" 2>/dev/null
done
```

---

## MCP server (Graphiti)

The Graphiti MCP server runs on the GB10 — every Claude Code session reaches the
same HTTP endpoint over Tailscale. Full deployment runbook:
[graphiti-gb10-deployment.md](graphiti-gb10-deployment.md).

For Claude Code, every repo's `.mcp.json` is identical and machine-agnostic:

```json
{
  "mcpServers": {
    "graphiti": {
      "type": "http",
      "url": "http://promaxgb10-41b1:8004/mcp"
    }
  }
}
```

Three things to watch:

- **No trailing slash on `/mcp`.** The slash triggers a 307 redirect that
  Claude Code's HTTP MCP transport does not follow on POST. See
  [graphiti-gb10-deployment.md → Known upstream quirks #2](graphiti-gb10-deployment.md#2-mcp-endpoint-url-must-not-have-a-trailing-slash).
  Fingerprint of this bug: `/mcp` connects, `/mcp/` silently fails to connect
  with no error.
- **Tailscale must be up on the client machine.** `promaxgb10-41b1` is a
  Tailscale hostname, not public DNS. `tailscale status | grep promaxgb10`
  should show it.
- **`.mcp.json` is read at Claude Code launch.** Restart after editing.

### Quick fix one-liners

```bash
# Strip trailing slash (Linux GNU sed — GB10)
sed -i 's#:8004/mcp/#:8004/mcp#' .mcp.json

# Strip trailing slash (macOS BSD sed — MacBook)
sed -i '' 's#:8004/mcp/#:8004/mcp#' .mcp.json

# Sweep all sibling repos at once (run from ~/Projects/appmilla_github)
# Linux / GB10:
for d in */.mcp.json; do sed -i 's#:8004/mcp/#:8004/mcp#' "$d"; done
# macOS:
for d in */.mcp.json; do sed -i '' 's#:8004/mcp/#:8004/mcp#' "$d"; done
```

---

## Verifying a healthy install

After cloning a repo, or after applying any of the fixes above:

```bash
# 1. Inside Claude Code: check overall health
/doctor
# Expect: no plugin errors. The
# "Plugin langchain-skills not found in marketplace langchain-skills" error
# means a stale enabledPlugins entry sneaked back in. See "Failure mode 1".

# 2. Skills loaded?
ls ~/.claude/skills/    # symlinks into ~/.agents/skills/ on fresh installs
ls ~/.agents/skills/    # actual skill content
# Expect: 11 directories (deep-agents-*, langchain-*, langgraph-*, framework-selection)
# Empty / missing dirs = run `npx skills add ...` (needs Node — see Prerequisite section)

# 3. Graphiti MCP reachable from this machine?
curl -s -o /dev/null -w "%{http_code}\n" http://promaxgb10-41b1:8004/mcp
# 406 = correct (FastMCP wants a session — proves reachable + correctly addressed)
# 307 = client config still has the trailing slash — see fix above
# Connection failure = Tailscale or GB10 stack is down — see graphiti-gb10-deployment.md

# 4. Inside Claude Code: confirm MCP is connected
/mcp
# Expect: graphiti: connected

# 5. uv on PATH? (only required on hosts that run `guardkit autobuild`
#    against repos with [tool.uv.sources] — see the uv section above)
which uv && uv --version
# Missing = autobuild will hard-fail at bootstrap on affected repos.
```

---

## Currently-clean repos (audited 2026-04-25 on GB10)

These have been swept and are clean of both failure modes:

- `guardkit`
- `agentic-dataset-factory`
- `forge`
- `specialist-agent`
- `nats-core`
- `nats-infrastructure`

When cloning a fresh repo or onboarding a new sibling on either machine, run
`/doctor` once and apply the fixes above if needed. Then add it to this list.

---

## Why this keeps happening (so we can stop it happening)

The recurring root cause is that **"skills" is overloaded vocabulary** — both
Anthropic and LangChain use the word, and the LangChain package is published
under a name (`langchain-skills`) that grammatically reads like "a skills
plugin for langchain". Earlier Claude Code sessions on this setup pattern-matched
on the name and added a plugin entry, not realising the package is actually
distributed via a different mechanism (`npx skills add` → file-based skills).

To prevent recurrence:
- A user-level feedback memory has been saved
  ([`feedback_langchain_skills_not_a_plugin.md`](../../../.claude/projects/-home-richardwoollcott-Projects-appmilla-github-guardkit/memory/feedback_langchain_skills_not_a_plugin.md))
  so future Claude Code sessions on this machine see the constraint.
- This document is the human-facing equivalent.
- If a future Claude session ever proposes adding `enabledPlugins` for any
  langchain-* entry, push back and point at this doc.
