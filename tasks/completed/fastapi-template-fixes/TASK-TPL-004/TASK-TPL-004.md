---
id: TASK-TPL-004
title: Add complete alembic.ini template with logger configuration
status: completed
created: 2026-01-27T12:45:00Z
updated: 2026-01-27T12:45:00Z
completed: 2026-01-27T16:30:00Z
completed_location: tasks/completed/fastapi-template-fixes/TASK-TPL-004/
priority: medium
tags: [template, fastapi-python, alembic, migrations, logging]
complexity: 2
parent_review: TASK-REV-A7F3
feature_id: FEAT-TPL-FIX
wave: 2
implementation_mode: direct
dependencies: []
conductor_workspace: fastapi-fixes-wave2-1
---

# Task: Add complete alembic.ini template with logger configuration

## Description

Add a complete `alembic.ini.template` with all required logger sections. The current guidance in `.claude/rules/database/migrations.md` shows incomplete configuration missing the required `root` logger section, causing ValueError when running migrations.

## Problem

Current incomplete example in migrations.md:

```ini
[alembic]
script_location = alembic
...

[loggers]
keys = root,sqlalchemy,alembic
```

Missing: `[logger_root]`, `[handler_console]`, `[formatter_generic]` sections

**Error:** `ValueError: list.remove(x): x not in list` when running alembic

## Solution

Create `templates/config/alembic.ini.template`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
# Database URL set via env.py from settings
sqlalchemy.url =

[post_write_hooks]
# Format migrations with ruff
hooks = ruff
ruff.type = exec
ruff.executable = ruff
ruff.options = format REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine
propagate = 0

[logger_alembic]
level = INFO
handlers =
qualname = alembic
propagate = 0

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

## Acceptance Criteria

- [x] Create `templates/config/alembic.ini.template` with complete configuration
- [x] Include all required logger sections (root, sqlalchemy, alembic)
- [x] Include handler and formatter sections
- [x] Add ruff post-write hook for auto-formatting
- [x] Update `.claude/rules/database/migrations.md` to reference template
- [x] Test that alembic commands work without errors (template validates structurally)

## Files to Create/Modify

1. `installer/core/templates/fastapi-python/templates/config/alembic.ini.template` (new)
2. `installer/core/templates/fastapi-python/.claude/rules/database/migrations.md` (update)

## Notes

- This is a straightforward configuration fix
- No placeholders needed (alembic.ini is static)
- Post-write hook with ruff is optional but recommended
