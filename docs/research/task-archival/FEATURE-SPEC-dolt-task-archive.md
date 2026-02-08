# Feature Specification: Dolt Task Archive Integration

> **For**: `/feature-plan` command
> **Status**: Ready for Implementation
> **Created**: 2026-02-07
> **Architecture Score**: N/A (new infrastructure)
> **Depends On**: FEATURE-SPEC-task-lifecycle-cleanup (Wave 1 minimum)

---

## Feature Overview

Integrate Dolt (a version-controlled SQL database) as the archival backend for GuardKit task data, implementing a hybrid approach where active tasks remain as human-readable markdown files and completed/cancelled tasks are archived into a queryable Dolt database with the markdown files then removed.

**Problem Solved**:
- Repository congestion: 400+ completed task files/directories create clutter and slow Git operations
- No queryable history: "which features had the most fix tasks?" requires manually reading hundreds of markdown files
- No pattern detection: cannot systematically identify recurring review feedback, common failure modes, or estimation accuracy
- Beads integration (11 planned tasks) no longer warranted given Dolt's maturity and Yegge's own endorsement
- Future Graphiti integration needs structured historical data as a secondary knowledge source

**Expected Outcomes**:
- Completed tasks queryable via SQL (e.g. `SELECT * FROM tasks WHERE duration_days > 5`)
- Repository size reduction: completed markdown files replaced by single Dolt database
- Foundation for analytics: estimation accuracy, failure patterns, review frequency
- Version-controlled archive: every change to archived data tracked with Git-style commits
- Clean migration path from markdown-only to hybrid storage

---

## Technology Decision: Dolt

### What is Dolt?

Dolt is a MySQL-compatible SQL database with Git-style version control. It stores data in tables (not files) and supports branch, merge, diff, commit, push, and pull operations. It is often described as "Git and MySQL had a baby."

### Licensing & Cost

| Option | License | Cost | Notes |
|--------|---------|------|-------|
| **Dolt CLI (self-hosted)** | Apache 2.0 | **Free** | Single Go binary, runs locally, no server needed for CLI mode |
| **Dolt SQL Server (self-hosted)** | Apache 2.0 | **Free** | MySQL-compatible server, `dolt sql-server` command |
| **DoltHub (cloud)** | Proprietary SaaS | Free for public repos | GitHub-like hosting for Dolt databases |
| **Hosted Dolt (managed)** | Proprietary SaaS | From ~$50/month | AWS-managed Dolt instances |
| **DoltLab (self-hosted hub)** | Proprietary | Free community edition | Self-hosted DoltHub alternative |

**Recommendation**: Use **Dolt CLI + local SQL Server** (Apache 2.0, completely free). This aligns with GuardKit's zero-cost-to-start principle and keeps data local. No cloud dependency. The Dolt binary is a single Go executable installable via `brew install dolt` (macOS), `curl` script (Linux), or `.msi` (Windows).

### Python Integration

Dolt exposes a MySQL-compatible wire protocol. GuardKit (Python) connects using standard MySQL libraries:

**Recommended approach**: `dolt sql-server` + `mysql-connector-python` (or `pymysql`)

```python
import mysql.connector

config = {
    'user': 'root',
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'guardkit_archive',
}
cnx = mysql.connector.connect(**config)
cursor = cnx.cursor()
cursor.execute("SELECT * FROM tasks WHERE status = 'completed'")
```

**Alternative for simpler operations**: `dolt sql -q "SELECT ..."` via subprocess (no server needed, but slower for batch operations).

**Version control operations** are exposed as SQL stored procedures:
```sql
CALL DOLT_ADD('-A');
CALL DOLT_COMMIT('-m', 'Archive 5 completed tasks from feature FEAT-ABC');
```

**Available Python libraries**:
- `mysql-connector-python` — recommended by Dolt team, pure Python, well-tested
- `pymysql` — pure Python alternative, also well-tested with Dolt
- `SQLAlchemy` — ORM layer if needed, works via either connector
- `doltcli` — thin Python wrapper around Dolt CLI (subprocess-based), useful for Git-style operations without running a server
- `doltpy` — older/deprecated Python API, now recommends using MySQL connectors directly

### Why Dolt over SQLite/Postgres?

- **Version control is native**: every INSERT/UPDATE/DELETE is diffable and reversible without application-layer logic
- **Git-compatible workflow**: `dolt commit`, `dolt push`, `dolt diff` feel natural alongside Git
- **Branch for experiments**: test schema migrations on a branch, merge when confident
- **Rollback is instant**: `dolt revert` or `dolt checkout` to undo bad archive operations
- **MySQL compatibility**: reuse existing MySQL ecosystem (ORMs, tools, knowledge)
- **Aligns with Yegge's insight**: "What if your database was versioned with Git? Every single change?"

### What Dolt is NOT needed for

- Active task management (markdown files remain the working format)
- Real-time collaboration (GuardKit is single-developer)
- High-throughput writes (archival is batch, low-frequency)

---

## Scope

**Total Estimate**: 36-48 hours (~5-6 days)

### Wave 1: Dolt Foundation (10-14h)

Set up Dolt infrastructure, schema, and basic Python integration.

| Task | Description | Mode | Estimate |
|------|-------------|------|----------|
| DTA-001 | Design Dolt schema for task archival - tables for tasks, features, reviews, metadata | task-review | 3h |
| DTA-002 | Create `guardkit dolt init` command - initialises Dolt database in `.guardkit/archive/` with schema | task-work | 3h |
| DTA-003 | Implement DoltClient Python class - connection management, query execution, version control operations | task-work | 4h |
| DTA-004 | Add Dolt binary detection and installation guidance to GuardKit setup | task-work | 2h |
| DTA-005 | Add configuration for Dolt (enable/disable, data directory path, server port) | task-work | 2h |

### Wave 2: Archival Pipeline (12-16h)

Build the pipeline that extracts structured data from markdown tasks and archives to Dolt.

| Task | Description | Mode | Estimate |
|------|-------------|------|----------|
| DTA-010 | Implement markdown-to-structured-data parser - extract frontmatter, acceptance criteria, metadata, outcomes | task-work | 4h |
| DTA-011 | Implement archive-on-complete hook - when task-complete runs, extract and insert into Dolt | task-work | 3h |
| DTA-012 | Implement post-archive markdown deletion - remove markdown file after successful Dolt insert, with safety checks | task-work | 2h |
| DTA-013 | Implement feature directory archival - when all tasks in a feature are archived, archive feature metadata and remove directory | task-work | 3h |
| DTA-014 | Add Dolt commit per archival batch - group related archives into atomic Dolt commits with descriptive messages | task-work | 2h |
| DTA-015 | Add error handling and rollback - if archival fails, markdown files are preserved | task-work | 2h |

### Wave 3: Query & Analytics (8-10h)

Expose the archived data through useful queries and reports.

| Task | Description | Mode | Estimate |
|------|-------------|------|----------|
| DTA-020 | Implement `guardkit archive query` command - run SQL queries against the archive | task-work | 2h |
| DTA-021 | Create built-in query templates - common queries as named shortcuts (e.g. `--stale-features`, `--estimation-accuracy`, `--failure-patterns`) | task-work | 3h |
| DTA-022 | Implement `guardkit archive stats` command - summary dashboard of task history | task-work | 2h |
| DTA-023 | Add Dolt diff/log integration - show what was archived when and by whom | task-work | 1h |
| DTA-024 | Documentation for archive system | direct | 2h |

### Wave 4: Migration (6-8h)

Migrate existing completed tasks into the Dolt archive.

| Task | Description | Mode | Estimate |
|------|-------------|------|----------|
| DTA-030 | Create bulk migration script - process all existing completed/ and cancelled/ directories | task-work | 3h |
| DTA-031 | Implement validation pass - verify all data was correctly archived before deletion | task-work | 2h |
| DTA-032 | Create backup-before-migration safety step | task-work | 1h |
| DTA-033 | Update .gitignore for Dolt data directory (or decide on Git-tracking strategy) | task-work | 1h |

---

## Proposed Dolt Schema

```sql
CREATE TABLE tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status ENUM('completed', 'cancelled', 'obsolete') NOT NULL,
    feature_slug VARCHAR(100),
    complexity INT,
    estimated_hours DECIMAL(5,1),
    actual_hours DECIMAL(5,1),
    mode ENUM('task-work', 'task-review', 'direct') DEFAULT 'task-work',
    created_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    review_outcome VARCHAR(50),
    tags JSON,
    acceptance_criteria TEXT,
    completion_summary TEXT,
    archived_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_path VARCHAR(500)  -- original markdown path for traceability
);

CREATE TABLE features (
    feature_slug VARCHAR(100) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    total_tasks INT,
    completed_tasks INT,
    cancelled_tasks INT,
    estimated_hours DECIMAL(6,1),
    actual_hours DECIMAL(6,1),
    created_at DATETIME,
    completed_at DATETIME,
    archived_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reviews (
    review_id VARCHAR(50) PRIMARY KEY,
    task_id VARCHAR(50),
    review_type VARCHAR(50),
    outcome ENUM('accept', 'cancel', 'implement', 'rework'),
    findings TEXT,
    recommendations TEXT,
    reviewed_at DATETIME,
    archived_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

CREATE TABLE task_metadata (
    task_id VARCHAR(50),
    key_name VARCHAR(100),
    value TEXT,
    PRIMARY KEY (task_id, key_name),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
```

---

## Acceptance Criteria

### Wave 1: Foundation
- WHEN `guardkit dolt init` runs THEN a Dolt database is created at `.guardkit/archive/` with the defined schema
- WHEN Dolt is not installed THEN GuardKit provides clear installation instructions (brew/curl/msi)
- WHEN Dolt is disabled in config THEN all archival features gracefully degrade (markdown files remain, no errors)
- WHEN DoltClient connects THEN it can execute queries and version control stored procedures

### Wave 2: Archival Pipeline
- WHEN a task completes AND Dolt is enabled THEN task data is extracted from markdown and inserted into Dolt
- WHEN archival succeeds THEN the source markdown file is deleted
- WHEN archival fails THEN the markdown file is preserved and an error is logged
- WHEN all tasks in a feature directory are archived THEN the feature metadata is archived and directory removed
- WHEN a batch of tasks is archived THEN a single Dolt commit groups them with a descriptive message

### Wave 3: Query & Analytics
- WHEN `guardkit archive query "SELECT..."` runs THEN it returns formatted results from the Dolt database
- WHEN `guardkit archive stats` runs THEN it displays task count, avg duration, completion rate, and top failure patterns
- WHEN built-in query templates are used THEN they return meaningful insights without requiring SQL knowledge

### Wave 4: Migration
- WHEN migration runs THEN all existing completed/cancelled tasks are archived to Dolt
- WHEN migration validation passes THEN markdown files are removed
- WHEN validation fails for any task THEN that task's markdown is preserved and flagged for manual review
- WHEN migration begins THEN a Git-level backup is created first

---

## Technical Notes

### Dolt Server Lifecycle

For archival operations, GuardKit should start `dolt sql-server` as a child process, perform the archival batch, then stop the server. This avoids a persistent background process. The `doltcli` Python library can manage this, or it can be done via subprocess.

For query operations, the same start-query-stop pattern applies, or `dolt sql -q` can be used directly for single queries without starting a server.

### Git Integration Strategy

Two options for the Dolt data directory:

1. **Git-tracked** (recommended for single-developer): `.guardkit/archive/` committed to Git. Dolt's internal storage is content-addressable and efficient. This means the archive travels with the repo.
2. **Git-ignored**: `.guardkit/archive/` in `.gitignore`, backed up separately. Better for large archives or multi-developer repos where Dolt data would bloat Git.

Recommend starting with option 1 and adding option 2 as a configuration choice.

### Graphiti Integration (Future)

The Dolt archive becomes a queryable source for Graphiti knowledge graph seeding. When `/system-plan` or `/feature-plan` needs historical context (e.g. "what patterns of failure occurred in similar features?"), Graphiti can query Dolt for structured historical data rather than parsing old markdown files. This connection is out of scope for this feature but the schema is designed with it in mind.

### Graceful Degradation

Dolt is an optional dependency. If not installed:
- Task lifecycle works exactly as today (markdown only)
- Archive commands show a helpful message: "Dolt not installed. Run `brew install dolt` to enable archival."
- No errors, no degraded functionality in core task workflows

---

## Dependencies

- **FEATURE-SPEC-task-lifecycle-cleanup** (Wave 1 minimum): terminal action cleanup ensures tasks reach proper terminal state before archival
- **Dolt binary**: `brew install dolt` (macOS), `curl` install script (Linux), `.msi` (Windows)
- **mysql-connector-python**: `pip install mysql-connector-python` (Apache 2.0 + MySQL FOSS Exception)

## Risks

- Dolt adds a binary dependency - mitigated by making it fully optional with graceful degradation
- Schema evolution needs careful handling - mitigated by Dolt's branch-and-merge for schema changes
- Bulk migration of 400+ existing files could be slow - mitigated by batch processing and progress reporting
- Markdown parsing may miss edge cases in older task formats - mitigated by validation pass before deletion

---

## Retirement: Beads Integration

This feature replaces the planned Beads integration (11 tasks in `tasks/backlog/beads-integration/`). The Beads integration should be moved to `tasks/obsolete/` with a note referencing this feature spec. Key reasons:

1. Steve Yegge himself stated he would have used Dolt instead of creating Beads had Dolt been mature enough at the time
2. Dolt provides a superset of Beads' functionality: version-controlled storage, SQL queryability, Git semantics
3. GuardKit already has Graphiti for cross-session knowledge/memory (Beads' primary value proposition)
4. The TaskBackend abstraction concept from BI-001/BI-002 is preserved - Dolt simply becomes the archival backend rather than Beads becoming the active backend

**Files to retire**:
- `tasks/backlog/beads-integration/` (entire directory, 11 tasks + README + implementation guide)
- `tasks/backlog/TASK-REV-b8c3-guardkit-beads-requirekit-vision.md` (update to reference this spec)
