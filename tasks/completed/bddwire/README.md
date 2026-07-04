# FEAT-BDDWIRE — Wire the guardkitfactory BDD plugin subsystem into the Coach

**Source:** `tasks/backlog/TASK-HMIG-BDDWIRE-wire-factory-bdd-plugins-into-coach.md`
**Why:** the factory multi-stack BDD plugins (pytest-bdd / reqnroll / cucumber-js,
42 tests) are built but **unconsumed** — .NET/JS BDD verification is unreachable from
a run. This feature wires `discover(stack)→BDDRunResult→bundle.bdd` into the Coach.

**Also:** this is the **first real autobuild generalization-test** feature (a novel,
never-built feature run cold) and the **dependency that unblocks SPEC_GAP** in the
QA-Verifier wiring scope (`docs/features/qa-verifier-wiring-probes-scope.md`).

## Tasks

| Wave | Task | Complexity | Depends on |
|---|---|---:|---|
| 1 | TASK-BDDW-001 — core wiring + Python e2e (AC-1,3,4,5,6) | 5 | — |
| 2 | TASK-BDDW-002 — multi-stack reachability .NET/JS (AC-2) | 4 | TASK-BDDW-001 |

## Run

```bash
guardkit autobuild feature FEAT-BDDWIRE --verbose
```

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for the data-flow diagram
(the disconnection this feature fixes) and the integration contract.
