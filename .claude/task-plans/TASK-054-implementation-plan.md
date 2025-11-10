# TASK-054 Implementation Plan: Basic Information Section

## Overview
Enhance Section 1 of the Q&A flow to include all required basic information fields as specified in the original task requirements.

## Current State
- ✅ `template_name` - exists with validation
- ✅ `template_purpose` - exists (choice field)
- ❌ `description` - missing (required)
- ❌ `version` - missing (optional, default: "1.0.0")
- ❌ `author` - missing (optional)

## Implementation Strategy
Add missing fields to Section 1 while maintaining backward compatibility with existing `template_purpose` field.

## Changes Required

### 1. Update Questions Definition
**File:** `installer/global/commands/lib/template_qa_questions.py`

Add three new questions to `SECTION1_QUESTIONS`:
```python
Question(
    id="description",
    section="Template Identity",
    text="Briefly describe this template's purpose:",
    type="text",
    default=None,
    help_text="What will developers use this template for?",
    validation="min_length_10"
),
Question(
    id="version",
    section="Template Identity",
    text="Initial version:",
    type="text",
    default="1.0.0",
    help_text="Semantic version (e.g., 1.0.0)",
    validation="version_string"
),
Question(
    id="author",
    section="Template Identity",
    text="Author or team name:",
    type="text",
    default=None,
    help_text="Optional: Who maintains this template?"
)
```

### 2. Update GreenfieldAnswers Dataclass
**File:** `installer/global/commands/lib/template_qa_session.py`

Add new fields to `GreenfieldAnswers`:
```python
@dataclass
class GreenfieldAnswers:
    # Section 1: Template Identity
    template_name: str
    template_purpose: str
    description: Optional[str] = None  # NEW
    version: str = "1.0.0"  # NEW
    author: Optional[str] = None  # NEW
    # ... rest of fields
```

### 3. Update Validators
**File:** `installer/global/commands/lib/template_qa_validator.py`

Add new validation functions:
```python
def validate_min_length(text: str, min_length: int) -> str:
    """Validate text has minimum length"""
    if len(text.strip()) < min_length:
        raise ValidationError(f"Must be at least {min_length} characters")
    return text.strip()

def validate_version_string(version: str) -> str:
    """Validate version follows semantic versioning"""
    import re
    pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$'
    if not re.match(pattern, version):
        raise ValidationError("Version must follow semantic versioning (e.g., 1.0.0)")
    return version
```

### 4. Update Session Question Handling
**File:** `installer/global/commands/lib/template_qa_session.py`

Update `_ask_text()` method to handle new validation types:
```python
def _ask_text(self, question: questions.Question) -> str:
    """Ask a text question."""
    prompt = display.prompt_text(question.text, question.default, question.help_text)

    while True:
        response = input(prompt).strip()

        # Use default if empty
        if not response and question.default:
            response = question.default

        # Validate
        try:
            if question.id == "template_name":
                return validator.validate_template_name(response)
            elif question.validation == "non_empty":
                return validator.validate_non_empty(response)
            elif question.validation == "min_length_10":  # NEW
                return validator.validate_min_length(response, 10)
            elif question.validation == "version_string":  # NEW
                return validator.validate_version_string(response)
            else:
                return response
        except validator.ValidationError as e:
            display.print_error(str(e))
            prompt = "Please try again: "
```

### 5. Update _build_result() Method
**File:** `installer/global/commands/lib/template_qa_session.py`

Add new fields to result building:
```python
def _build_result(self) -> GreenfieldAnswers:
    """Build GreenfieldAnswers from collected answers."""
    return GreenfieldAnswers(
        # Section 1
        template_name=self.answers.get("template_name", "my-template"),
        template_purpose=self.answers.get("template_purpose", "quick_start"),
        description=self.answers.get("description"),  # NEW
        version=self.answers.get("version", "1.0.0"),  # NEW
        author=self.answers.get("author"),  # NEW
        # Section 2
        primary_language=self.answers.get("primary_language", "csharp"),
        # ... rest of fields
    )
```

## Testing Strategy

### Unit Tests to Add/Update

**File:** `tests/test_template_qa_session.py`

1. Test new field inclusion in GreenfieldAnswers
```python
def test_greenfield_answers_with_new_fields():
    """Test GreenfieldAnswers includes new basic info fields"""
    answers = GreenfieldAnswers(
        template_name="test-template",
        template_purpose="quick_start",
        description="A test template for demonstration",  # NEW
        version="1.0.0",  # NEW
        author="Test Team",  # NEW
        # ... required fields
    )

    assert answers.description == "A test template for demonstration"
    assert answers.version == "1.0.0"
    assert answers.author == "Test Team"
```

2. Test validation for description
```python
def test_description_validation():
    """Test description must be at least 10 characters"""
    from template_qa_validator import validate_min_length, ValidationError

    # Valid
    assert validate_min_length("A valid description", 10) == "A valid description"

    # Invalid
    with pytest.raises(ValidationError):
        validate_min_length("Short", 10)
```

3. Test version validation
```python
def test_version_validation():
    """Test version follows semantic versioning"""
    from template_qa_validator import validate_version_string, ValidationError

    # Valid
    assert validate_version_string("1.0.0") == "1.0.0"
    assert validate_version_string("2.1.3") == "2.1.3"
    assert validate_version_string("1.0.0-beta.1") == "1.0.0-beta.1"

    # Invalid
    with pytest.raises(ValidationError):
        validate_version_string("1.0")
    with pytest.raises(ValidationError):
        validate_version_string("v1.0.0")
```

4. Test optional fields
```python
def test_optional_fields_default_values():
    """Test author is optional, version has default"""
    session = TemplateQASession(skip_qa=True)
    answers = session.run()

    # Version should have default
    assert answers.version == "1.0.0"

    # Author should be None if not provided
    assert answers.author is None or isinstance(answers.author, str)
```

### Integration Tests

**File:** `tests/integration/test_qa_workflow.py`

1. Test complete Section 1 flow with new fields
```python
def test_section1_complete_flow(monkeypatch):
    """Test Section 1 Q&A with all fields"""
    inputs = [
        "my-awesome-template",  # template_name
        "1",  # template_purpose (choice)
        "A comprehensive template for building awesome applications",  # description
        "1.0.0",  # version (default)
        "Engineering Team",  # author
        # ... other sections
    ]

    input_iter = iter(inputs)
    monkeypatch.setattr('builtins.input', lambda _: next(input_iter))

    session = TemplateQASession()
    answers = session.run()

    assert answers.template_name == "my-awesome-template"
    assert answers.description == "A comprehensive template for building awesome applications"
    assert answers.version == "1.0.0"
    assert answers.author == "Engineering Team"
```

## Files Modified

1. `installer/global/commands/lib/template_qa_questions.py` - Add 3 new questions
2. `installer/global/commands/lib/template_qa_session.py` - Update dataclass and methods
3. `installer/global/commands/lib/template_qa_validator.py` - Add 2 new validators
4. `tests/test_template_qa_session.py` - Add/update unit tests
5. `tests/integration/test_qa_workflow.py` - Add integration tests

## Backward Compatibility

✅ All changes are **additive** - no breaking changes
✅ Existing code using `template_purpose` continues to work
✅ New fields are optional except `description` (but has graceful handling)
✅ Default values provided for `version`

## Acceptance Criteria Verification

From TASK-054:
- [x] Template name question with validation (min 3 chars, hyphen required) - ✅ Already exists
- [x] Description question with validation (min 10 chars) - ✅ Will implement
- [x] Version question with default "1.0.0" - ✅ Will implement
- [x] Author question (optional) - ✅ Will implement
- [x] Returns basic_info dict - ✅ Already works, will be enhanced
- [x] Unit tests passing - ✅ Will implement

## Estimated Implementation Time

- Update questions: 15 minutes
- Update dataclass: 10 minutes
- Update validators: 20 minutes
- Update session methods: 15 minutes
- Write unit tests: 45 minutes
- Write integration tests: 30 minutes
- Testing and fixes: 45 minutes

**Total: ~3 hours** (matches original estimate)

## Complexity Assessment

**Score: 3/10**
- Simple additive changes
- Straightforward validation logic
- Well-defined requirements
- No architectural changes

## Risks

1. **Low Risk:** Breaking existing tests that expect only 2 Section 1 questions
   - **Mitigation:** Run full test suite and update affected tests

2. **Low Risk:** Existing code assumes specific GreenfieldAnswers structure
   - **Mitigation:** All new fields are optional except description (which is nullable initially for backward compat)

## Success Metrics

- ✅ All TASK-054 acceptance criteria met
- ✅ Test coverage ≥ 80% for new code
- ✅ All existing tests pass
- ✅ No breaking changes to existing functionality
