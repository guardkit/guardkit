# Feature Plan --context Option

## Overview

The `--context` option allows users to explicitly specify context files when running `/feature-plan`, supplementing or overriding the automatic context detection.

## Acceptance Criteria

- ✅ `--context path/to/spec.md` seeds specified file
- ✅ Multiple `--context` flags supported
- ✅ Works alongside auto-detection
- ✅ Help text documents usage

## Usage

### Basic Usage

```bash
# Single context file
/feature-plan "implement OAuth" --context docs/auth-design.md
```

### Multiple Context Files

```bash
# Multiple files (processed in order)
/feature-plan "add API" --context docs/api-spec.md --context docs/security.md
```

### With Other Flags

```bash
# Combine with clarification flags
/feature-plan "implement feature" --context spec.md --with-questions

# Combine with structured output control
/feature-plan "add service" --context design.md --no-structured
```

## When to Use --context

**Use `--context` when:**
- Feature spec is not in standard location (`docs/features/`)
- Need to include additional architectural context
- Want to override auto-detection with specific files
- Testing or automation scenarios requiring explicit context
- Working with external specifications or design documents

**Auto-detection works well when:**
- Feature specs follow naming convention (`FEAT-XXX-*.md`)
- Files are in `docs/features/` directory
- CLAUDE.md contains relevant project context

## Implementation Details

### File Requirements

- Must be readable markdown files
- Can include frontmatter metadata
- Paths can be relative (to project root) or absolute
- Nonexistent files are handled gracefully (warning logged)

### Processing Order

1. Explicit `--context` files are loaded first (in order specified)
2. Auto-detected context files are loaded second
3. All context is merged and passed to the feature planning analysis

### Error Handling

- Nonexistent files: Warning logged, planning continues
- Unreadable files: Warning logged, planning continues
- Invalid paths: Converted to Path objects automatically

## Technical Implementation

### Code Structure

```
guardkit/
├── commands/
│   └── feature_plan_integration.py  # Main integration class
└── knowledge/
    └── feature_plan_context.py     # Context builder

tests/
├── unit/
│   └── commands/
│       ├── test_feature_plan_cli_context.py      # CLI option tests (14 tests)
│       └── test_feature_plan_integration.py      # Integration tests (20 tests)
└── integration/
    └── test_feature_plan_context_option.py       # E2E test
```

### Test Coverage

- **Unit Tests**: 14 tests covering all acceptance criteria
- **Integration Tests**: 20 tests for feature plan integration
- **E2E Test**: 1 integration test demonstrating complete workflow
- **Total Coverage**: 35 tests, all passing

### API

```python
# FeaturePlanIntegration.build_enriched_prompt signature
async def build_enriched_prompt(
    self,
    description: str,
    context_files: Optional[List[Path]] = None,
    tech_stack: str = "python"
) -> str:
    """Build enriched prompt with Graphiti context.

    Args:
        description: Feature description
        context_files: Optional explicit context files
        tech_stack: Technology stack (default: python)

    Returns:
        Enriched prompt string with context injection
    """
```

## Examples

### Example 1: Feature with External Spec

```bash
# Planning a feature defined in external specification
/feature-plan "implement payment gateway" \
  --context vendor/stripe-integration-spec.md \
  --context docs/security-requirements.md
```

### Example 2: Override Auto-detection

```bash
# Use specific version of spec instead of auto-detected one
/feature-plan "implement FEAT-GR-003" \
  --context docs/features/FEAT-GR-003-v2-revised.md
```

### Example 3: Additional Architectural Context

```bash
# Include architecture docs not auto-detected
/feature-plan "refactor authentication" \
  --context docs/architecture/auth-architecture.md \
  --context docs/decisions/ADR-042-auth-strategy.md
```

## Related Documentation

- [Feature Plan Command](../../installer/core/commands/feature-plan.md)
- [Feature Plan Context Builder](../../guardkit/knowledge/feature_plan_context.py)
- [Graphiti Integration](../../docs/guides/graphiti-integration.md)

## Changelog

### Version 1.0 (2026-02-01)

- ✅ Initial implementation of `--context` option
- ✅ Support for multiple context files
- ✅ Integration with auto-detection
- ✅ Comprehensive test coverage
- ✅ Documentation and usage examples
