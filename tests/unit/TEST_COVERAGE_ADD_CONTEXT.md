# Test Coverage: guardkit graphiti add-context

## Overview

Comprehensive TDD test suite for the `guardkit graphiti add-context` CLI command (RED phase).

**Test File**: `tests/unit/test_graphiti_add_context.py`

**Total Tests**: 11 test scenarios covering all acceptance criteria and edge cases.

## Test Coverage

### 1. Single File Processing (test_add_context_single_file_with_known_parser)
- Reads file content
- Detects/uses specified parser
- Parses file into episodes
- Adds episodes to Graphiti
- Displays success summary

**Expected**: Exit code 0, file added to Graphiti

### 2. Directory Processing - Default Pattern (test_add_context_directory_with_default_pattern)
- Scans directory for `**/*.md` files (default glob)
- Processes each matching file
- Displays summary with file count

**Expected**: Multiple files processed, count displayed

### 3. Directory Processing - Custom Pattern (test_add_context_directory_with_custom_pattern)
- Uses custom glob pattern from `--pattern` flag
- Processes only matching files

**Expected**: Only files matching custom pattern processed

### 4. Auto-Detection of Parser Type (test_add_context_auto_detect_parser_type)
- Calls `registry.detect_parser()` when `--type` not provided
- Uses detected parser
- Displays parser type in output

**Expected**: Correct parser auto-detected based on file content/path

### 5. Dry-Run Preview Mode (test_add_context_dry_run_shows_preview_without_adding)
- Parses files
- Displays what would be added
- Does NOT call `GraphitiClient.add_episode()`
- Exits successfully

**Expected**: Preview shown, no actual changes made

### 6. Force Parser Type (test_add_context_type_flag_forces_parser)
- Uses `registry.get_parser(type)` instead of `detect_parser()`
- Forces specific parser even if auto-detection would differ

**Expected**: Specified parser used regardless of file content

### 7. Unsupported File Errors (test_add_context_graceful_error_for_unsupported_file)
- Detects when no parser can handle file
- Displays warning/error message
- Continues or exits gracefully

**Expected**: Clear error message, no crash

### 8. File Not Found Error (test_add_context_file_not_found_error)
- Checks file existence
- Displays clear error message
- Exits with non-zero code

**Expected**: User-friendly error, exit code != 0

### 9. Summary Output Format (test_add_context_summary_output_format)
- Shows number of files processed
- Shows number of episodes added
- Shows parser type(s) used
- Shows success/warning indicators
- Includes parser warnings

**Expected**: Informative, well-formatted summary

### 10. Force Flag Behavior (test_add_context_force_flag_overwrites_existing)
- When `--force` is used, overwrites existing episodes
- Displays indication that episodes were overwritten

**Expected**: Episodes overwritten with --force flag

### 11. Mixed Success/Failure (test_add_context_directory_with_mixed_success_and_failures)
- Continues processing after individual file failures
- Displays both successes and failures in summary
- Exits with appropriate status code

**Expected**: Resilient processing, clear summary of results

### 12. Graphiti Connection Error (test_add_context_graphiti_connection_error)
- Detects connection failure
- Displays clear error message
- Exits gracefully with non-zero code

**Expected**: User-friendly error, no crash

### 13. Add Episode Error (test_add_context_graphiti_add_episode_error)
- Detects `add_episode()` failure
- Displays error but continues processing other files
- Shows failure in summary

**Expected**: Resilient error handling, clear failure indication

### 14. End-to-End Workflow (test_add_context_end_to_end_workflow)
- Realistic scenario: adding directory of ADR files
- Files parsed successfully
- Episodes added to Graphiti
- Summary displayed

**Expected**: Complete workflow from CLI invocation to Graphiti storage

## Mocking Strategy

### GraphitiClient Mocking
- `AsyncMock` for all async methods
- Mock `initialize()` to return True
- Mock `add_episode()` to return UUIDs
- Mock `close()` for cleanup verification

### ParserRegistry Mocking
- Mock `get_parser(type)` for forced parser selection
- Mock `detect_parser(path, content)` for auto-detection
- Create test parsers (ADR, FeatureSpec) with configurable behavior

### Filesystem Mocking
- Mock `Path` for file existence checks
- Mock `Path.is_file()` and `Path.is_dir()`
- Mock `Path.glob()` for directory scanning
- Mock `open()` with `mock_open()` for file reading

## CLI Testing Pattern

Uses Click's `CliRunner` for isolated CLI testing:
```python
runner = CliRunner()
result = runner.invoke(graphiti, ["add-context", "path/to/file.md"])

assert result.exit_code == 0
assert "expected text" in result.output
```

## Expected Command Signature

Based on tests, the command should be implemented as:

```bash
guardkit graphiti add-context [OPTIONS] <PATH>

Arguments:
  PATH                    File or directory to add

Options:
  --type TEXT            Force parser type (adr, feature-spec, project-overview)
  --force                Overwrite existing context
  --dry-run              Show what would be added without adding
  --pattern TEXT         Glob pattern for directory (default: **/*.md)
```

## Running the Tests

These tests are designed to FAIL initially (RED phase) since the command doesn't exist yet.

```bash
# Run all tests (should fail)
pytest tests/unit/test_graphiti_add_context.py -v

# Run specific test
pytest tests/unit/test_graphiti_add_context.py::test_add_context_single_file_with_known_parser -v

# Run with coverage
pytest tests/unit/test_graphiti_add_context.py --cov=guardkit.cli.graphiti --cov-report=term
```

## Next Steps (GREEN Phase)

After tests are written and failing:

1. Implement `add_context` command in `guardkit/cli/graphiti.py`
2. Create async helper function `_cmd_add_context()`
3. Implement file/directory processing logic
4. Integrate with ParserRegistry
5. Add episodes to GraphitiClient
6. Format and display summary output
7. Run tests until all pass

## Test Quality Metrics

- **Coverage**: 100% of acceptance criteria
- **Edge Cases**: File not found, unsupported files, connection errors
- **Error Handling**: Graceful degradation, clear error messages
- **Realistic Scenarios**: End-to-end workflow testing
- **Isolation**: All external dependencies mocked
- **Assertions**: Verify both behavior and output

## Dependencies

Required packages:
- pytest
- pytest-asyncio
- click
- unittest.mock (standard library)

Install:
```bash
pip install pytest pytest-asyncio click
```
