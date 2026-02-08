"""Test suite for prohibition checklist generation and validation.

TDD RED PHASE: All tests are written BEFORE implementation.
These tests MUST fail initially and will pass once implementation is complete.

Tests cover:
- 12-category prohibition analysis
- Unconditionally prohibited categories (5, 8, 11, 12)
- Override detection for conditional categories (1-4, 6-7, 9-10)
- Two-tier compliance validation (pattern matching + AST)
- Zero false negatives for critical categories
- Checklist serialization and token budget
"""

import json
from typing import Any, Dict, List

import pytest

# These imports WILL fail until implementation exists - this is expected in TDD RED phase
from guardkit.orchestrator.prohibition_checklist import (
    ProhibitionCategory,
    ProhibitionChecklist,
    ProhibitionChecker,
    Violation,
    ViolationSeverity,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_design_elements() -> List[Dict[str, Any]]:
    """Sample design elements extracted from a Figma design."""
    return [
        {
            "name": "LoginForm",
            "type": "component",
            "children": [
                {"name": "UsernameInput", "type": "input", "props": {"placeholder": "Username"}},
                {"name": "PasswordInput", "type": "input", "props": {"placeholder": "Password"}},
                {"name": "LoginButton", "type": "button", "props": {"text": "Login"}},
            ],
        },
        {
            "name": "UserProfileCard",
            "type": "component",
            "children": [
                {"name": "Avatar", "type": "image"},
                {"name": "NameLabel", "type": "text"},
                {"name": "EmailLabel", "type": "text"},
            ],
        },
    ]


@pytest.fixture
def design_elements_with_loading_state() -> List[Dict[str, Any]]:
    """Design elements that explicitly show a loading state."""
    return [
        {
            "name": "LoginForm",
            "type": "component",
            "children": [
                {"name": "UsernameInput", "type": "input"},
                {"name": "PasswordInput", "type": "input"},
                {"name": "LoginButton", "type": "button"},
                {
                    "name": "LoadingSpinner",
                    "type": "loader",
                    "props": {"variant": "spinner"},
                },
            ],
        }
    ]


@pytest.fixture
def design_elements_with_error_state() -> List[Dict[str, Any]]:
    """Design elements that explicitly show an error state."""
    return [
        {
            "name": "LoginForm",
            "type": "component",
            "children": [
                {"name": "UsernameInput", "type": "input"},
                {"name": "PasswordInput", "type": "input"},
                {"name": "LoginButton", "type": "button"},
                {
                    "name": "ErrorMessage",
                    "type": "alert",
                    "props": {"variant": "error", "text": "Invalid credentials"},
                },
            ],
        }
    ]


@pytest.fixture
def design_elements_with_animation() -> List[Dict[str, Any]]:
    """Design elements that specify animations."""
    return [
        {
            "name": "Modal",
            "type": "component",
            "props": {"animation": "fade-in", "duration": "300ms"},
            "children": [
                {"name": "ModalContent", "type": "container"},
            ],
        }
    ]


@pytest.fixture
def design_elements_with_responsive() -> List[Dict[str, Any]]:
    """Design elements that show responsive breakpoints."""
    return [
        {
            "name": "Dashboard",
            "type": "component",
            "props": {
                "breakpoints": {
                    "mobile": "320px",
                    "tablet": "768px",
                    "desktop": "1024px",
                }
            },
        }
    ]


@pytest.fixture
def prohibition_checker() -> ProhibitionChecker:
    """ProhibitionChecker instance for testing."""
    return ProhibitionChecker()


@pytest.fixture
def sample_code_with_api_call() -> str:
    """Sample code containing an API integration."""
    return """
    import axios from 'axios';

    const fetchUserData = async (userId: string) => {
        const response = await axios.get(`/api/users/${userId}`);
        return response.data;
    };
    """


@pytest.fixture
def sample_code_with_fetch() -> str:
    """Sample code using fetch API."""
    return """
    const getUserProfile = async (id: string) => {
        const response = await fetch(`/api/profile/${id}`);
        return await response.json();
    };
    """


@pytest.fixture
def sample_code_with_loading_state() -> str:
    """Sample code implementing a loading state."""
    return """
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async () => {
        setIsLoading(true);
        // ... implementation
        setIsLoading(false);
    };
    """


@pytest.fixture
def sample_code_with_best_practice() -> str:
    """Sample code adding best practice that wasn't in design."""
    return """
    // Added error boundary for better UX (not in design)
    <ErrorBoundary fallback={<ErrorFallback />}>
        <LoginForm />
    </ErrorBoundary>
    """


@pytest.fixture
def sample_code_with_extra_props() -> str:
    """Sample code adding extra props for flexibility."""
    return """
    interface ButtonProps {
        text: string;
        onClick: () => void;
        // Added for flexibility (not in design)
        variant?: 'primary' | 'secondary' | 'outline';
        size?: 'small' | 'medium' | 'large';
        disabled?: boolean;
        loading?: boolean;
    }
    """


# ============================================================================
# Test Classes
# ============================================================================


class TestProhibitionChecklist:
    """Tests for ProhibitionChecklist generation and structure."""

    def test_checklist_has_12_categories(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that checklist contains all 12 categories."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        assert len(checklist.categories) == 12

    def test_checklist_categories_have_names(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that all categories have descriptive names."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        expected_categories = [
            "loading_states",
            "error_states",
            "form_validation",
            "state_management",
            "api_integrations",
            "navigation",
            "additional_controls",
            "sample_data",
            "responsive_breakpoints",
            "animations",
            "best_practices",
            "extra_props",
        ]
        actual_categories = [cat.name for cat in checklist.categories]
        assert set(actual_categories) == set(expected_categories)

    def test_checklist_serializable_to_dict(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that checklist can be serialized to dictionary."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        checklist_dict = checklist.to_dict()
        assert isinstance(checklist_dict, dict)
        assert "categories" in checklist_dict
        assert isinstance(checklist_dict["categories"], list)

    def test_checklist_serializable_to_json(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that checklist can be serialized to JSON."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        json_str = checklist.to_json()
        assert isinstance(json_str, str)
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert "categories" in parsed

    def test_category_has_prohibited_status(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that each category has a prohibited status (True/False)."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        for category in checklist.categories:
            assert hasattr(category, "prohibited")
            assert isinstance(category.prohibited, bool)

    def test_category_has_reasoning(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that each category includes reasoning for its status."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        for category in checklist.categories:
            assert hasattr(category, "reasoning")
            assert isinstance(category.reasoning, str)
            assert len(category.reasoning) > 0


class TestCategory1LoadingStates:
    """Tests for Category 1: Loading states."""

    def test_loading_states_prohibited_by_default(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that loading states are prohibited when not in design."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        loading_category = next(c for c in checklist.categories if c.name == "loading_states")
        assert loading_category.prohibited is True
        assert "not shown in design" in loading_category.reasoning.lower()

    def test_loading_states_allowed_when_in_design(
        self, prohibition_checker: ProhibitionChecker, design_elements_with_loading_state: List[Dict]
    ):
        """Test that loading states are allowed when explicitly shown in design."""
        checklist = prohibition_checker.generate_checklist(design_elements_with_loading_state)
        loading_category = next(c for c in checklist.categories if c.name == "loading_states")
        assert loading_category.prohibited is False
        assert "shown in design" in loading_category.reasoning.lower() or "explicit" in loading_category.reasoning.lower()

    def test_loading_state_detection_spinner(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of loading spinner in design elements."""
        elements = [
            {
                "name": "Component",
                "children": [{"name": "Spinner", "type": "loader"}],
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        loading_category = next(c for c in checklist.categories if c.name == "loading_states")
        assert loading_category.prohibited is False

    def test_loading_state_detection_skeleton(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of skeleton loader in design elements."""
        elements = [
            {
                "name": "Component",
                "children": [{"name": "SkeletonLoader", "type": "skeleton"}],
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        loading_category = next(c for c in checklist.categories if c.name == "loading_states")
        assert loading_category.prohibited is False


class TestCategory2ErrorStates:
    """Tests for Category 2: Error states."""

    def test_error_states_prohibited_by_default(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that error states are prohibited when not in design."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        error_category = next(c for c in checklist.categories if c.name == "error_states")
        assert error_category.prohibited is True

    def test_error_states_allowed_when_in_design(
        self, prohibition_checker: ProhibitionChecker, design_elements_with_error_state: List[Dict]
    ):
        """Test that error states are allowed when shown in design."""
        checklist = prohibition_checker.generate_checklist(design_elements_with_error_state)
        error_category = next(c for c in checklist.categories if c.name == "error_states")
        assert error_category.prohibited is False

    def test_error_state_detection_alert(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of error alert in design."""
        elements = [
            {
                "name": "Form",
                "children": [{"name": "ErrorAlert", "type": "alert", "props": {"variant": "error"}}],
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        error_category = next(c for c in checklist.categories if c.name == "error_states")
        assert error_category.prohibited is False

    def test_error_state_detection_error_message(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of error message component."""
        elements = [
            {
                "name": "Form",
                "children": [{"name": "ErrorMessage", "type": "text"}],
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        error_category = next(c for c in checklist.categories if c.name == "error_states")
        assert error_category.prohibited is False


class TestCategory3FormValidation:
    """Tests for Category 3: Additional form validation."""

    def test_form_validation_prohibited_by_default(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that additional form validation is prohibited by default."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        validation_category = next(c for c in checklist.categories if c.name == "form_validation")
        assert validation_category.prohibited is True

    def test_form_validation_allowed_when_validation_shown(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that validation is allowed when shown in design."""
        elements = [
            {
                "name": "Form",
                "children": [
                    {
                        "name": "EmailInput",
                        "type": "input",
                        "props": {"validation": "email", "errorMessage": "Invalid email"},
                    }
                ],
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        validation_category = next(c for c in checklist.categories if c.name == "form_validation")
        assert validation_category.prohibited is False


class TestCategory4StateManagement:
    """Tests for Category 4: Complex state management."""

    def test_state_management_prohibited_by_default(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that complex state management is prohibited by default."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        state_category = next(c for c in checklist.categories if c.name == "state_management")
        assert state_category.prohibited is True

    def test_state_management_allowed_for_interactive_components(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that state management is allowed for interactive components shown in design."""
        elements = [
            {
                "name": "TabPanel",
                "type": "tabs",
                "props": {"tabs": ["Tab1", "Tab2", "Tab3"], "defaultTab": 0},
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        state_category = next(c for c in checklist.categories if c.name == "state_management")
        assert state_category.prohibited is False


class TestCategory5APIIntegrations:
    """Tests for Category 5: API integrations (UNCONDITIONALLY PROHIBITED)."""

    def test_api_integrations_always_prohibited(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that API integrations are ALWAYS prohibited."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        api_category = next(c for c in checklist.categories if c.name == "api_integrations")
        assert api_category.prohibited is True

    def test_api_integrations_no_override_possible(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that API integrations cannot be overridden even if design shows them."""
        # Even with "api" in design, should remain prohibited
        elements = [
            {
                "name": "DataFetcher",
                "type": "component",
                "props": {"dataSource": "api", "endpoint": "/users"},
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        api_category = next(c for c in checklist.categories if c.name == "api_integrations")
        assert api_category.prohibited is True
        assert "unconditionally prohibited" in api_category.reasoning.lower()

    def test_api_category_marked_as_unconditional(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that API category is marked as unconditionally prohibited."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        api_category = next(c for c in checklist.categories if c.name == "api_integrations")
        assert hasattr(api_category, "unconditional")
        assert api_category.unconditional is True


class TestCategory6Navigation:
    """Tests for Category 6: Navigation beyond design."""

    def test_navigation_prohibited_by_default(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that navigation beyond design is prohibited by default."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        nav_category = next(c for c in checklist.categories if c.name == "navigation")
        assert nav_category.prohibited is True

    def test_navigation_allowed_when_shown_in_design(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that navigation is allowed when shown in design."""
        elements = [
            {
                "name": "Navbar",
                "type": "navigation",
                "children": [
                    {"name": "HomeLink", "type": "link", "props": {"href": "/home"}},
                    {"name": "ProfileLink", "type": "link", "props": {"href": "/profile"}},
                ],
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        nav_category = next(c for c in checklist.categories if c.name == "navigation")
        assert nav_category.prohibited is False


class TestCategory7AdditionalControls:
    """Tests for Category 7: Additional buttons/controls."""

    def test_additional_controls_prohibited_by_default(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that additional controls are prohibited by default."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        controls_category = next(c for c in checklist.categories if c.name == "additional_controls")
        assert controls_category.prohibited is True

    def test_only_design_controls_allowed(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that only controls shown in design are allowed."""
        elements = [
            {
                "name": "Form",
                "children": [
                    {"name": "SubmitButton", "type": "button"},
                    {"name": "CancelButton", "type": "button"},
                ],
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        # Should still be prohibited (can't add MORE controls)
        controls_category = next(c for c in checklist.categories if c.name == "additional_controls")
        assert controls_category.prohibited is True
        assert "only implement controls shown" in controls_category.reasoning.lower()


class TestCategory8SampleData:
    """Tests for Category 8: Sample data beyond design (UNCONDITIONALLY PROHIBITED)."""

    def test_sample_data_always_prohibited(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that sample data beyond design is ALWAYS prohibited."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        data_category = next(c for c in checklist.categories if c.name == "sample_data")
        assert data_category.prohibited is True

    def test_sample_data_no_override_possible(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that sample data cannot be overridden even with data in design."""
        elements = [
            {
                "name": "UserList",
                "type": "list",
                "props": {"sampleData": ["User1", "User2", "User3"]},
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        data_category = next(c for c in checklist.categories if c.name == "sample_data")
        assert data_category.prohibited is True

    def test_sample_data_marked_as_unconditional(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that sample data category is marked as unconditionally prohibited."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        data_category = next(c for c in checklist.categories if c.name == "sample_data")
        assert hasattr(data_category, "unconditional")
        assert data_category.unconditional is True


class TestCategory9ResponsiveBreakpoints:
    """Tests for Category 9: Responsive breakpoints."""

    def test_responsive_prohibited_by_default(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that responsive breakpoints are prohibited by default."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        responsive_category = next(c for c in checklist.categories if c.name == "responsive_breakpoints")
        assert responsive_category.prohibited is True

    def test_responsive_allowed_when_in_design(
        self, prohibition_checker: ProhibitionChecker, design_elements_with_responsive: List[Dict]
    ):
        """Test that responsive breakpoints are allowed when shown in design."""
        checklist = prohibition_checker.generate_checklist(design_elements_with_responsive)
        responsive_category = next(c for c in checklist.categories if c.name == "responsive_breakpoints")
        assert responsive_category.prohibited is False


class TestCategory10Animations:
    """Tests for Category 10: Animations not specified."""

    def test_animations_prohibited_by_default(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that animations are prohibited by default."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        animation_category = next(c for c in checklist.categories if c.name == "animations")
        assert animation_category.prohibited is True

    def test_animations_allowed_when_in_design(
        self, prohibition_checker: ProhibitionChecker, design_elements_with_animation: List[Dict]
    ):
        """Test that animations are allowed when specified in design."""
        checklist = prohibition_checker.generate_checklist(design_elements_with_animation)
        animation_category = next(c for c in checklist.categories if c.name == "animations")
        assert animation_category.prohibited is False


class TestCategory11BestPractices:
    """Tests for Category 11: Best practice additions (UNCONDITIONALLY PROHIBITED)."""

    def test_best_practices_always_prohibited(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that best practice additions are ALWAYS prohibited."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        best_practices_category = next(c for c in checklist.categories if c.name == "best_practices")
        assert best_practices_category.prohibited is True

    def test_best_practices_no_override(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that best practices cannot be overridden."""
        # Even with accessibility in design
        elements = [
            {
                "name": "Button",
                "props": {"aria-label": "Submit", "role": "button"},
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        best_practices_category = next(c for c in checklist.categories if c.name == "best_practices")
        assert best_practices_category.prohibited is True

    def test_best_practices_marked_as_unconditional(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that best practices category is marked as unconditionally prohibited."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        best_practices_category = next(c for c in checklist.categories if c.name == "best_practices")
        assert hasattr(best_practices_category, "unconditional")
        assert best_practices_category.unconditional is True


class TestCategory12ExtraProps:
    """Tests for Category 12: Extra props for flexibility (UNCONDITIONALLY PROHIBITED)."""

    def test_extra_props_always_prohibited(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that extra props are ALWAYS prohibited."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        extra_props_category = next(c for c in checklist.categories if c.name == "extra_props")
        assert extra_props_category.prohibited is True

    def test_extra_props_no_override(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that extra props cannot be overridden."""
        elements = [
            {
                "name": "Button",
                "props": {"text": "Click me", "variant": "primary"},
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        extra_props_category = next(c for c in checklist.categories if c.name == "extra_props")
        assert extra_props_category.prohibited is True

    def test_extra_props_marked_as_unconditional(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that extra props category is marked as unconditionally prohibited."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        extra_props_category = next(c for c in checklist.categories if c.name == "extra_props")
        assert hasattr(extra_props_category, "unconditional")
        assert extra_props_category.unconditional is True


class TestUnconditionallyProhibited:
    """Tests specifically for unconditionally prohibited categories (5, 8, 11, 12)."""

    def test_four_categories_unconditionally_prohibited(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that exactly 4 categories are unconditionally prohibited."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        unconditional = [c for c in checklist.categories if getattr(c, "unconditional", False)]
        assert len(unconditional) == 4

    def test_unconditional_categories_correct(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that categories 5, 8, 11, 12 are marked as unconditional."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        unconditional_names = {
            c.name for c in checklist.categories if getattr(c, "unconditional", False)
        }
        expected = {"api_integrations", "sample_data", "best_practices", "extra_props"}
        assert unconditional_names == expected

    def test_unconditional_always_prohibited_regardless_of_design(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that unconditional categories remain prohibited even with design hints."""
        elements = [
            {
                "name": "DataComponent",
                "props": {
                    "api": "/users",
                    "sampleData": ["User1", "User2"],
                    "accessibilityProps": {"aria-label": "Data"},
                    "extraProps": {"variant": "primary", "size": "large"},
                },
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)

        api_cat = next(c for c in checklist.categories if c.name == "api_integrations")
        data_cat = next(c for c in checklist.categories if c.name == "sample_data")
        best_cat = next(c for c in checklist.categories if c.name == "best_practices")
        props_cat = next(c for c in checklist.categories if c.name == "extra_props")

        assert all([
            api_cat.prohibited,
            data_cat.prohibited,
            best_cat.prohibited,
            props_cat.prohibited,
        ])


class TestOverrideDetection:
    """Tests for override detection in conditional categories."""

    def test_detect_loading_state_by_loader_type(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of loading state via loader type."""
        elements = [{"name": "Loader", "type": "loader"}]
        checklist = prohibition_checker.generate_checklist(elements)
        loading_cat = next(c for c in checklist.categories if c.name == "loading_states")
        assert loading_cat.prohibited is False

    def test_detect_loading_state_by_spinner_name(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of loading state via spinner in name."""
        elements = [{"name": "LoadingSpinner", "type": "component"}]
        checklist = prohibition_checker.generate_checklist(elements)
        loading_cat = next(c for c in checklist.categories if c.name == "loading_states")
        assert loading_cat.prohibited is False

    def test_detect_error_state_by_alert_type(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of error state via alert type."""
        elements = [{"name": "Alert", "type": "alert", "props": {"variant": "error"}}]
        checklist = prohibition_checker.generate_checklist(elements)
        error_cat = next(c for c in checklist.categories if c.name == "error_states")
        assert error_cat.prohibited is False

    def test_detect_error_state_by_error_name(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of error state via error in name."""
        elements = [{"name": "ErrorBoundary", "type": "component"}]
        checklist = prohibition_checker.generate_checklist(elements)
        error_cat = next(c for c in checklist.categories if c.name == "error_states")
        assert error_cat.prohibited is False

    def test_detect_validation_by_props(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of validation via validation props."""
        elements = [
            {
                "name": "Input",
                "type": "input",
                "props": {"validation": "email", "required": True},
            }
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        validation_cat = next(c for c in checklist.categories if c.name == "form_validation")
        assert validation_cat.prohibited is False

    def test_detect_animation_by_props(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of animation via animation props."""
        elements = [
            {"name": "Modal", "props": {"animation": "fade", "transition": "ease-in"}}
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        animation_cat = next(c for c in checklist.categories if c.name == "animations")
        assert animation_cat.prohibited is False

    def test_detect_responsive_by_breakpoints(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test detection of responsive design via breakpoints."""
        elements = [
            {"name": "Layout", "props": {"breakpoints": {"mobile": 320, "tablet": 768}}}
        ]
        checklist = prohibition_checker.generate_checklist(elements)
        responsive_cat = next(c for c in checklist.categories if c.name == "responsive_breakpoints")
        assert responsive_cat.prohibited is False


class TestComplianceValidation:
    """Tests for compliance validation (Tier 1: Pattern matching)."""

    def test_validate_compliance_returns_violations(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that validate_compliance returns list of violations."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        violations = prohibition_checker.validate_compliance(
            ["src/components/test.tsx"],
            checklist
        )
        assert isinstance(violations, list)

    def test_tier1_detects_axios_api_call(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test Tier 1 pattern matching detects axios API calls."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        # Create a test file with axios
        test_file = "/tmp/test_component.tsx"
        with open(test_file, "w") as f:
            f.write("import axios from 'axios';\nconst data = await axios.get('/api/users');")

        violations = prohibition_checker.validate_compliance([test_file], checklist)

        # Should detect API integration violation
        api_violations = [v for v in violations if "api" in v.category.lower()]
        assert len(api_violations) > 0

    def test_tier1_detects_fetch_api_call(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test Tier 1 pattern matching detects fetch API calls."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        test_file = "/tmp/test_fetch.tsx"
        with open(test_file, "w") as f:
            f.write("const response = await fetch('/api/data');")

        violations = prohibition_checker.validate_compliance([test_file], checklist)
        api_violations = [v for v in violations if "api" in v.category.lower()]
        assert len(api_violations) > 0

    def test_tier1_detects_loading_state_pattern(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test Tier 1 detects loading state patterns."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        test_file = "/tmp/test_loading.tsx"
        with open(test_file, "w") as f:
            f.write("const [isLoading, setIsLoading] = useState(false);")

        violations = prohibition_checker.validate_compliance([test_file], checklist)
        loading_violations = [v for v in violations if "loading" in v.category.lower()]
        assert len(loading_violations) > 0

    def test_tier1_detects_error_state_pattern(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test Tier 1 detects error state patterns."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        test_file = "/tmp/test_error.tsx"
        with open(test_file, "w") as f:
            f.write("const [error, setError] = useState<Error | null>(null);")

        violations = prohibition_checker.validate_compliance([test_file], checklist)
        error_violations = [v for v in violations if "error" in v.category.lower()]
        assert len(error_violations) > 0

    def test_tier1_fast_pattern_matching(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that Tier 1 pattern matching is fast (regex-based)."""
        import time

        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        # Create a larger test file
        test_file = "/tmp/test_large.tsx"
        with open(test_file, "w") as f:
            f.write("const Component = () => {\n" * 1000)
            f.write("return <div>Test</div>;\n" * 1000)
            f.write("};\n" * 1000)

        start = time.time()
        prohibition_checker.validate_compliance([test_file], checklist)
        duration = time.time() - start

        # Should be fast (< 1 second for pattern matching)
        assert duration < 1.0


class TestTier2ASTAnalysis:
    """Tests for Tier 2 AST analysis (activated only after Tier 1 detects potential violations)."""

    def test_tier2_activated_only_on_tier1_match(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that Tier 2 AST analysis only runs when Tier 1 finds potential violations."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        # Clean file with no violations
        test_file = "/tmp/test_clean.tsx"
        with open(test_file, "w") as f:
            f.write("const Component = () => <div>Hello</div>;")

        # Should not trigger AST analysis (no violations detected)
        violations = prohibition_checker.validate_compliance([test_file], checklist)

        # Verify AST wasn't run (check internal state or timing)
        # This test verifies the two-tier architecture
        assert len(violations) == 0

    def test_tier2_confirms_real_violation(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that Tier 2 AST analysis confirms real violations."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        test_file = "/tmp/test_real_api.tsx"
        with open(test_file, "w") as f:
            f.write("""
                import axios from 'axios';

                const fetchData = async () => {
                    const response = await axios.get('/api/users');
                    return response.data;
                };
            """)

        violations = prohibition_checker.validate_compliance([test_file], checklist)

        # Tier 2 should confirm this is a real API call
        api_violations = [v for v in violations if "api" in v.category.lower()]
        assert len(api_violations) > 0
        assert any(v.confidence == "high" for v in api_violations)

    def test_tier2_dismisses_false_positive(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that Tier 2 AST analysis can dismiss false positives."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        test_file = "/tmp/test_false_positive.tsx"
        with open(test_file, "w") as f:
            f.write("""
                // Comment mentioning fetch but not using it
                const Component = () => {
                    // We should fetch data here later
                    return <div>Component</div>;
                };
            """)

        violations = prohibition_checker.validate_compliance([test_file], checklist)

        # Tier 2 should not report violation for comments
        api_violations = [v for v in violations if "api" in v.category.lower()]
        assert len(api_violations) == 0

    def test_tier2_ast_provides_line_numbers(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that Tier 2 AST analysis provides specific line numbers."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        test_file = "/tmp/test_line_numbers.tsx"
        with open(test_file, "w") as f:
            f.write("""
                import axios from 'axios';

                const Component = () => {
                    const data = axios.get('/api/users');  // Line 4
                    return <div>{data}</div>;
                };
            """)

        violations = prohibition_checker.validate_compliance([test_file], checklist)

        api_violations = [v for v in violations if "api" in v.category.lower()]
        assert len(api_violations) > 0
        assert hasattr(api_violations[0], "line_number")
        assert api_violations[0].line_number is not None


class TestZeroFalseNegatives:
    """Tests to ensure zero false negatives for unconditionally prohibited categories."""

    def test_unconditional_categories_comprehensive_patterns(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that all common patterns for unconditional categories are detected."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        # Test various API integration patterns
        api_patterns = [
            "import axios from 'axios';",
            "fetch('/api/data')",
            "await fetch(url)",
            "axios.get('/users')",
            "axios.post('/api/data', {})",
            "$.ajax({url: '/api'})",
            "XMLHttpRequest()",
        ]

        for pattern in api_patterns:
            test_file = "/tmp/test_pattern.tsx"
            with open(test_file, "w") as f:
                f.write(f"const test = () => {{ {pattern} }};")

            violations = prohibition_checker.validate_compliance([test_file], checklist)
            api_violations = [v for v in violations if "api" in v.category.lower()]
            assert len(api_violations) > 0, f"Failed to detect: {pattern}"

    def test_api_integration_all_patterns_detected(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that all API integration patterns are detected."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        patterns = [
            "axios",
            "fetch(",
            "XMLHttpRequest",
            "$.ajax",
            "$.get",
            "$.post",
            "http.get",
            "http.post",
        ]

        detected_count = 0
        for pattern in patterns:
            test_file = "/tmp/test_api_pattern.tsx"
            with open(test_file, "w") as f:
                f.write(f"const test = {pattern}")

            violations = prohibition_checker.validate_compliance([test_file], checklist)
            if any("api" in v.category.lower() for v in violations):
                detected_count += 1

        # Should detect most/all patterns
        assert detected_count >= len(patterns) * 0.8

    def test_best_practice_patterns_detected(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that best practice addition patterns are detected."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        patterns = [
            "ErrorBoundary",
            "Suspense",
            "React.memo",
            "useMemo(",
            "useCallback(",
            "aria-label",
            "role=",
        ]

        detected_count = 0
        for pattern in patterns:
            test_file = "/tmp/test_best_practice.tsx"
            with open(test_file, "w") as f:
                f.write(f"const test = () => <div {pattern}></div>")

            violations = prohibition_checker.validate_compliance([test_file], checklist)
            if any("best_practice" in v.category.lower() for v in violations):
                detected_count += 1

        # Should detect most patterns
        assert detected_count >= len(patterns) * 0.7


class TestSerialization:
    """Tests for checklist serialization and token budget."""

    def test_checklist_serializable_to_json(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that checklist can be serialized to JSON."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        json_str = checklist.to_json()

        # Verify valid JSON
        parsed = json.loads(json_str)
        assert "categories" in parsed
        assert len(parsed["categories"]) == 12

    def test_serialized_checklist_under_500_tokens(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that serialized checklist is under 500 tokens."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        json_str = checklist.to_json()

        # Rough token estimate: ~4 chars per token
        estimated_tokens = len(json_str) / 4
        assert estimated_tokens < 500

    def test_checklist_includes_per_category_decision(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that checklist includes decision for each category."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        checklist_dict = checklist.to_dict()

        for category in checklist_dict["categories"]:
            assert "prohibited" in category
            assert isinstance(category["prohibited"], bool)

    def test_checklist_includes_reasoning(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that checklist includes reasoning for each decision."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        checklist_dict = checklist.to_dict()

        for category in checklist_dict["categories"]:
            assert "reasoning" in category
            assert isinstance(category["reasoning"], str)
            assert len(category["reasoning"]) > 0

    def test_checklist_compact_representation(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that checklist uses compact representation for token efficiency."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)
        json_str = checklist.to_json()

        # Should not have excessive whitespace
        assert "\n\n" not in json_str or json_str.count("\n\n") < 5

        # Should use abbreviated keys if possible
        parsed = json.loads(json_str)
        # Just verify it's efficient
        assert len(json_str) < 3000  # Under 3K chars


class TestViolationObjects:
    """Tests for Violation data structures."""

    def test_violation_has_required_fields(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that Violation objects have required fields."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        test_file = "/tmp/test_violation.tsx"
        with open(test_file, "w") as f:
            f.write("import axios from 'axios'; axios.get('/api/data');")

        violations = prohibition_checker.validate_compliance([test_file], checklist)

        if violations:
            violation = violations[0]
            assert hasattr(violation, "category")
            assert hasattr(violation, "file_path")
            assert hasattr(violation, "description")

    def test_violation_has_severity(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that violations have severity levels."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        test_file = "/tmp/test_severity.tsx"
        with open(test_file, "w") as f:
            f.write("fetch('/api/users')")

        violations = prohibition_checker.validate_compliance([test_file], checklist)

        if violations:
            violation = violations[0]
            assert hasattr(violation, "severity")
            # Should be high severity for unconditional prohibition
            assert violation.severity in ["critical", "high", ViolationSeverity.CRITICAL, ViolationSeverity.HIGH]

    def test_unconditional_violations_critical_severity(
        self, prohibition_checker: ProhibitionChecker, sample_design_elements: List[Dict]
    ):
        """Test that unconditionally prohibited violations have critical severity."""
        checklist = prohibition_checker.generate_checklist(sample_design_elements)

        test_file = "/tmp/test_critical.tsx"
        with open(test_file, "w") as f:
            f.write("const data = await fetch('/api/data');")

        violations = prohibition_checker.validate_compliance([test_file], checklist)

        api_violations = [v for v in violations if "api" in v.category.lower()]
        assert len(api_violations) > 0
        assert all(v.severity in ["critical", ViolationSeverity.CRITICAL] for v in api_violations)


class TestIntegrationWithDesignData:
    """Tests for integration with DesignData from TASK-DM-002."""

    def test_accepts_design_data_elements(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that ProhibitionChecker accepts DesignData.elements format."""
        # Simulate DesignData.elements structure
        design_elements = [
            {
                "name": "LoginForm",
                "type": "component",
                "children": [
                    {"name": "UsernameInput", "type": "input"},
                    {"name": "PasswordInput", "type": "input"},
                ],
            }
        ]

        # Should not raise exception
        checklist = prohibition_checker.generate_checklist(design_elements)
        assert checklist is not None
        assert len(checklist.categories) == 12

    def test_extracts_relevant_design_features(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that relevant features are extracted from design elements."""
        design_elements = [
            {
                "name": "Form",
                "children": [
                    {"name": "Input", "type": "input", "props": {"validation": "email"}},
                    {"name": "LoadingSpinner", "type": "loader"},
                    {"name": "ErrorAlert", "type": "alert"},
                ],
            }
        ]

        checklist = prohibition_checker.generate_checklist(design_elements)

        # Should detect these features from design
        loading_cat = next(c for c in checklist.categories if c.name == "loading_states")
        error_cat = next(c for c in checklist.categories if c.name == "error_states")
        validation_cat = next(c for c in checklist.categories if c.name == "form_validation")

        assert loading_cat.prohibited is False
        assert error_cat.prohibited is False
        assert validation_cat.prohibited is False

    def test_handles_empty_design_elements(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that empty design elements are handled correctly."""
        checklist = prohibition_checker.generate_checklist([])

        # All conditional categories should be prohibited
        # All unconditional categories should be prohibited
        assert all(c.prohibited for c in checklist.categories)

    def test_handles_nested_design_elements(
        self, prohibition_checker: ProhibitionChecker
    ):
        """Test that deeply nested design elements are analyzed."""
        design_elements = [
            {
                "name": "Page",
                "children": [
                    {
                        "name": "Section",
                        "children": [
                            {
                                "name": "Form",
                                "children": [
                                    {"name": "LoadingIndicator", "type": "loader"}
                                ],
                            }
                        ],
                    }
                ],
            }
        ]

        checklist = prohibition_checker.generate_checklist(design_elements)
        loading_cat = next(c for c in checklist.categories if c.name == "loading_states")

        # Should detect loading state even in nested structure
        assert loading_cat.prohibited is False
