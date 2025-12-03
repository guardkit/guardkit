# Contributing to GuardKit

Thank you for your interest in contributing to GuardKit! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Submitting Changes](#submitting-changes)
- [Review Process](#review-process)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/guardkit.git
   cd guardkit
   ```
3. **Set up the development environment** (see below)
4. **Create a branch** for your changes:
   ```bash
   git checkout -b your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip or poetry for dependency management
- Git

### Installation

```bash
# Install GuardKit
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Initialize with a template (optional, for testing)
guardkit init react-typescript
```

### Running Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=term --cov-report=json

# Run specific test file
pytest tests/test_specific.py -v

# Run with specific markers (if applicable)
pytest -m "unit" -v
```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes**: Fix issues identified in the issue tracker
- **New features**: Implement new functionality (discuss in an issue first)
- **Documentation**: Improve guides, examples, or code documentation
- **Templates**: Create new stack templates for common frameworks
- **Tests**: Add or improve test coverage
- **Refactoring**: Improve code quality and maintainability

### Before You Start

1. **Check existing issues** to avoid duplicate work
2. **Open an issue** to discuss significant changes before implementation
3. **Ask questions** if anything is unclear

## Coding Standards

### Python Code Style

- Follow **PEP 8** style guide
- Use **type hints** for function signatures
- Maximum line length: **88 characters** (Black formatter default)
- Use **descriptive variable names**

### Code Quality

- **Self-documenting code**: Write clear, readable code
- **Comments**: Explain "why", not "what"
- **Error handling**: Use appropriate exception handling
- **SOLID principles**: Follow architectural best practices

### GuardKit Workflow

When working on GuardKit itself, we dogfood our own system:

```bash
# Create a task for your work
/task-create "Your contribution description" priority:medium

# Work on the task (includes automatic quality gates)
/task-work TASK-XXX

# Complete when done
/task-complete TASK-XXX
```

This ensures all contributions go through:
- Implementation planning (Phase 2)
- Architectural review (Phase 2.5)
- Complexity evaluation (Phase 2.7)
- Testing with quality gates (Phase 4-4.5)
- Code review (Phase 5)
- Plan audit (Phase 5.5)

## Testing Requirements

All code contributions must meet these quality gates:

### Coverage Requirements

- **Line coverage**: ≥80%
- **Branch coverage**: ≥75%
- **All tests must pass**: 100% pass rate

### Test Types

1. **Unit tests**: Test individual functions/classes
2. **Integration tests**: Test component interactions
3. **End-to-end tests**: Test complete workflows (where applicable)

### Writing Tests

```python
# Example test structure
import pytest
from src.module import function_to_test

def test_function_behavior():
    """Test that function_to_test handles normal input correctly."""
    # Arrange
    input_data = "test input"
    expected_output = "expected result"

    # Act
    result = function_to_test(input_data)

    # Assert
    assert result == expected_output

def test_function_error_handling():
    """Test that function_to_test handles invalid input correctly."""
    with pytest.raises(ValueError):
        function_to_test(None)
```

## Submitting Changes

### Commit Messages

Follow the **Conventional Commits** format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(templates): add Vue.js template with TypeScript support

fix(task-manager): resolve state transition bug in BLOCKED tasks

docs(guides): update template creation guide with new examples
```

### Pull Request Process

1. **Update documentation** if you've added/changed functionality
2. **Add tests** for new features or bug fixes
3. **Ensure all tests pass** locally
4. **Update CHANGELOG.md** with your changes
5. **Push to your fork** and create a pull request
6. **Fill out the PR template** with relevant information

### Pull Request Template

When creating a PR, include:

- **Description**: What does this PR do?
- **Related Issue**: Link to issue number (if applicable)
- **Type of Change**: Bug fix, feature, docs, etc.
- **Testing**: How was this tested?
- **Checklist**:
  - [ ] Tests pass locally
  - [ ] Code follows style guidelines
  - [ ] Documentation updated
  - [ ] CHANGELOG.md updated

## Review Process

### What to Expect

1. **Automated checks**: CI/CD runs tests and linters
2. **Code review**: Maintainers review code quality and design
3. **Feedback**: You may be asked to make changes
4. **Approval**: Once approved, maintainers will merge

### Review Criteria

Reviews focus on:

- **Correctness**: Does the code work as intended?
- **Quality**: Is the code well-structured and maintainable?
- **Tests**: Are there adequate tests with good coverage?
- **Documentation**: Is the change properly documented?
- **Architectural alignment**: Does it follow GuardKit principles?

### Response Time

We aim to:
- **Acknowledge** new PRs within 2 business days
- **Review** PRs within 1 week
- **Merge** approved PRs within 2 business days

## Additional Resources

- **Project Guide**: [CLAUDE.md](CLAUDE.md) - Main documentation
- **Workflow Guide**: [docs/guides/guardkit-workflow.md](docs/guides/guardkit-workflow.md)
- **Template Creation**: [docs/guides/creating-local-templates.md](docs/guides/creating-local-templates.md)
- **Issue Tracker**: [GitHub Issues](https://github.com/guardkit/guardkit/issues)

## Questions?

If you have questions:

1. **Check documentation** in [CLAUDE.md](CLAUDE.md) and [docs/](docs/)
2. **Search existing issues** for similar questions
3. **Open a new issue** with your question
4. **Join discussions** in existing issues

## License

By contributing to GuardKit, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

Thank you for contributing to GuardKit! Your efforts help make this project better for everyone.
