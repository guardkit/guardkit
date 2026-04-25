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
2. Don't put machine-specific absolute paths (`/Users/...`, `/home/...`) in
   committed `.claude/settings.json`. Use `.claude/settings.local.json` for
   per-machine overrides — it's gitignored.
3. `.mcp.json` for Graphiti must be `http://promaxgb10-41b1:8004/mcp` —
   no trailing slash.
4. Run `/doctor` on each machine after cloning a repo. Apply the fixes below
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
