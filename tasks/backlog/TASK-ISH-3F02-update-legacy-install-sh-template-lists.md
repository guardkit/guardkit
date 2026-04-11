---
id: TASK-ISH-3F02
title: Update legacy install.sh template lists to match current builtins
status: backlog
created: 2026-04-11T12:00:00Z
updated: 2026-04-11T12:00:00Z
priority: low
tags: [installer, shell, cleanup, documentation, technical-debt]
parent_review: TASK-REV-D0C1
implementation_mode: task-work
complexity: 3
depends_on: []
---

# Task: Update legacy install.sh template lists to match current builtins

## Description

[installer/scripts/install.sh](../../installer/scripts/install.sh) contains three hardcoded template enumerations that are out of date. They were surfaced during the TASK-REV-D0C1 review but de-scoped from that task because fixing them partially (just adding `dotnet-railway-fastendpoints`) would still leave them stale for 5+ other templates. This task addresses all of them comprehensively.

## Current State (3 Stale Locations)

### Location 1: [install.sh:557](../../installer/scripts/install.sh#L557) — mkdir for template directories

```bash
mkdir -p "$INSTALL_DIR/templates"/{default,react-typescript,fastapi-python,nextjs-fullstack,react-fastapi-monorepo,python-library,nats-asyncio-service}
```

**Missing**: `fastmcp-python`, `mcp-typescript`, `langchain-deepagents`, `langchain-deepagents-orchestrator`, `langchain-deepagents-weighted-evaluation`, `dotnet-railway-fastendpoints` (after DRF-002).

### Location 2: [install.sh:834](../../installer/scripts/install.sh#L834) — stack-agents mkdir

```bash
mkdir -p "$INSTALL_DIR/stack-agents"/{default,react-typescript,fastapi-python,nextjs-fullstack,react-fastapi-monorepo}
```

**Missing**: same set as above plus `python-library`, `nats-asyncio-service`.

### Location 3: [install.sh:865-870](../../installer/scripts/install.sh#L865) — print_help() template descriptions

```bash
echo "Templates:"
echo "  default              - Language-agnostic foundation ..."
echo "  react-typescript     - React frontend ..."
echo "  fastapi-python       - FastAPI backend ..."
echo "  nextjs-fullstack     - Next.js ..."
echo "  react-fastapi-monorepo - React + FastAPI monorepo ..."
echo "  python-library         - Standalone pip-installable ..."
# ends here — missing all other templates
```

## Acceptance Criteria

- [ ] **Decide on approach** before editing:
  - **(a) Hardcode all current templates** — simple, but repeats the same staleness pattern. Needs a comment pointing at the single source of truth.
  - **(b) Dynamically enumerate from `installer/core/templates/`** at install time — more robust, harder to implement in pure bash. May require a helper script.
  - **(c) Retire install.sh's template-specific logic entirely** — the main CLI already auto-discovers; check whether install.sh's legacy path (the `~/.agentecflow` tree) is still supported and, if not, remove or simplify.

- [ ] **Audit usage**: is `installer/scripts/install.sh` still the supported install path, or has it been superseded by `pip install guardkit-py` + `guardkit init`? If superseded, prefer simplification / retirement over maintenance. Check [README.md](../../README.md) and [installer/scripts/install.sh](../../installer/scripts/install.sh) header comments.

- [ ] **If approach (a) or (b)**: update all 3 locations (lines 557, 834, 865-870) to include every template currently in `installer/core/templates/`, excluding `common/` and `guardkit.marker.json`.

- [ ] **Test**: dry-run the installer if possible, or at minimum confirm `bash -n installer/scripts/install.sh` passes (syntax check).

- [ ] **Add a maintenance note** near each hardcoded list (if approach (a)) pointing to this task and stating "keep in sync with `installer/core/templates/`".

## Known Templates (as of 2026-04-11)

```
common            (NOT a template — shared resources)
default
dotnet-railway-fastendpoints  (pending TASK-DRF-002)
fastapi-python
fastmcp-python
langchain-deepagents
langchain-deepagents-orchestrator
langchain-deepagents-weighted-evaluation
mcp-typescript
nats-asyncio-service
nextjs-fullstack
python-library
react-fastapi-monorepo
react-typescript
```

## Rationale

- Install script silently provides an incomplete experience for users who install the legacy way and then try to use a missing template.
- Any new template registration inherits this debt.
- The staleness was noted in [TASK-REV-D0C1 review report §6](../../.claude/reviews/TASK-REV-D0C1-review-report.md) but fixing it partially during registration would have been worse than leaving it alone.

## Notes

- **Not blocking** TASK-DRF-001/002/003/004. This can run before or after the dotnet template registration.
- **Strongly consider retiring the install.sh path** if it's no longer the recommended install method — that's cheaper than keeping 3 hardcoded lists in sync. Check with the project maintainer before removing.
