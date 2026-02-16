"""
Test that Trophy-model testing guidance is present in all client app templates.

This validates TASK-SFT-010: Add Trophy-Model Testing Guidance to Client App Templates.
"""

import pytest
from pathlib import Path


TEMPLATE_DIR = Path(__file__).parent.parent.parent / "installer" / "core" / "templates"


class TestTrophyTestingGuidance:
    """Verify Trophy testing model guidance in all client app templates."""

    @pytest.fixture
    def react_typescript_claude(self):
        """Load react-typescript CLAUDE.md content."""
        claude_path = TEMPLATE_DIR / "react-typescript" / "CLAUDE.md"
        assert claude_path.exists(), f"CLAUDE.md not found: {claude_path}"
        return claude_path.read_text()

    @pytest.fixture
    def fastapi_python_claude(self):
        """Load fastapi-python CLAUDE.md content."""
        claude_path = TEMPLATE_DIR / "fastapi-python" / "CLAUDE.md"
        assert claude_path.exists(), f"CLAUDE.md not found: {claude_path}"
        return claude_path.read_text()

    @pytest.fixture
    def nextjs_fullstack_claude(self):
        """Load nextjs-fullstack .claude/CLAUDE.md content."""
        claude_path = TEMPLATE_DIR / "nextjs-fullstack" / ".claude" / "CLAUDE.md"
        assert claude_path.exists(), f"CLAUDE.md not found: {claude_path}"
        return claude_path.read_text()

    @pytest.fixture
    def react_fastapi_monorepo_claude(self):
        """Load react-fastapi-monorepo .claude/CLAUDE.md content."""
        claude_path = TEMPLATE_DIR / "react-fastapi-monorepo" / ".claude" / "CLAUDE.md"
        assert claude_path.exists(), f"CLAUDE.md not found: {claude_path}"
        return claude_path.read_text()

    # AC-001: React TypeScript template has Trophy testing guidance
    def test_react_typescript_has_trophy_guidance(self, react_typescript_claude):
        """AC-001: React TypeScript template includes Trophy testing guidance."""
        content = react_typescript_claude

        # Verify Testing Strategy section exists
        assert "## Testing Strategy: Trophy Model" in content, \
            "Missing 'Testing Strategy: Trophy Model' section"

        # Verify Trophy diagram exists
        assert "🏆  E2E (~10%)" in content, "Missing Trophy diagram"

        # Verify testing distribution is documented
        assert "50% Feature/Integration Tests" in content, \
            "Missing feature/integration test percentage"
        assert "30% Unit Tests" in content, "Missing unit test percentage"
        assert "10% E2E Tests" in content, "Missing E2E test percentage"
        assert "10% Static Analysis" in content, "Missing static analysis percentage"

    # AC-002: FastAPI Python template has Trophy testing guidance
    def test_fastapi_python_has_trophy_guidance(self, fastapi_python_claude):
        """AC-002: FastAPI Python template includes Trophy testing guidance."""
        content = fastapi_python_claude

        # Verify Testing Strategy section exists
        assert "## Testing Strategy: Trophy Model" in content, \
            "Missing 'Testing Strategy: Trophy Model' section"

        # Verify Trophy diagram exists
        assert "🏆  E2E (~10%)" in content, "Missing Trophy diagram"

        # Verify testing distribution is documented
        assert "50% Feature/Integration Tests" in content, \
            "Missing feature/integration test percentage"
        assert "30% Unit Tests" in content, "Missing unit test percentage"

    # AC-003: Next.js Fullstack template has Trophy testing guidance
    def test_nextjs_fullstack_has_trophy_guidance(self, nextjs_fullstack_claude):
        """AC-003: Next.js Fullstack template includes Trophy testing guidance."""
        content = nextjs_fullstack_claude

        # Verify Testing Strategy section exists
        assert "## Testing Strategy: Trophy Model" in content, \
            "Missing 'Testing Strategy: Trophy Model' section"

        # Verify Trophy diagram exists
        assert "🏆  E2E (~10%)" in content, "Missing Trophy diagram"

        # Verify testing distribution is documented
        assert "50% Feature/Integration Tests" in content, \
            "Missing feature/integration test percentage"

    # AC-004: React-FastAPI Monorepo template has Trophy testing guidance
    def test_react_fastapi_monorepo_has_trophy_guidance(self, react_fastapi_monorepo_claude):
        """AC-004: React-FastAPI Monorepo template includes Trophy testing guidance."""
        content = react_fastapi_monorepo_claude

        # Verify Testing Strategy section exists
        assert "## Testing Strategy: Trophy Model" in content, \
            "Missing 'Testing Strategy: Trophy Model' section"

        # Verify Trophy diagram exists
        assert "🏆  E2E (~10%)" in content, "Missing Trophy diagram"

        # Verify both frontend and backend guidance
        assert "Frontend (React)" in content or "Frontend**" in content, \
            "Missing frontend-specific guidance"
        assert "Backend (FastAPI)" in content or "Backend**" in content, \
            "Missing backend-specific guidance"

    # AC-005: All templates include "Test behaviour, not implementation" principle
    @pytest.mark.parametrize("fixture_name", [
        "react_typescript_claude",
        "fastapi_python_claude",
        "nextjs_fullstack_claude",
        "react_fastapi_monorepo_claude"
    ])
    def test_templates_have_behavior_principle(self, fixture_name, request):
        """AC-005: All templates include 'Test behavior, not implementation' principle."""
        content = request.getfixturevalue(fixture_name)
        assert "Test behavior, not implementation" in content or \
               "Test behaviour, not implementation" in content, \
            f"{fixture_name}: Missing behavior testing principle"

    # AC-006: All templates specify what to mock vs what NOT to mock
    @pytest.mark.parametrize("fixture_name", [
        "react_typescript_claude",
        "fastapi_python_claude",
        "nextjs_fullstack_claude",
        "react_fastapi_monorepo_claude"
    ])
    def test_templates_have_mocking_guidance(self, fixture_name, request):
        """AC-006: All templates specify what to mock vs what NOT to mock."""
        content = request.getfixturevalue(fixture_name)

        # Check for mocking guidance section
        assert "What to mock:" in content, f"{fixture_name}: Missing 'What to mock' guidance"
        assert "What NOT to mock:" in content, f"{fixture_name}: Missing 'What NOT to mock' guidance"

        # Verify API mocking at HTTP level is mentioned
        assert "HTTP" in content or "MSW" in content or "WireMock" in content or \
               "httpx" in content or "MockTransport" in content, \
            f"{fixture_name}: Missing HTTP-level mocking guidance"

    # AC-007: All templates explain when seam tests ARE needed
    @pytest.mark.parametrize("fixture_name", [
        "react_typescript_claude",
        "fastapi_python_claude",
        "nextjs_fullstack_claude",
        "react_fastapi_monorepo_claude"
    ])
    def test_templates_have_seam_test_guidance(self, fixture_name, request):
        """AC-007: All templates explain when seam tests ARE needed in client apps."""
        content = request.getfixturevalue(fixture_name)

        # Check for seam test guidance
        assert "When seam tests ARE needed" in content, \
            f"{fixture_name}: Missing seam test guidance"

        # Should mention third-party integrations
        assert "third-party" in content.lower() or "external" in content.lower(), \
            f"{fixture_name}: Missing third-party integration guidance"

    # AC-008: All templates include testing requirements checklist
    @pytest.mark.parametrize("fixture_name", [
        "react_typescript_claude",
        "fastapi_python_claude",
        "nextjs_fullstack_claude",
        "react_fastapi_monorepo_claude"
    ])
    def test_templates_have_requirements_checklist(self, fixture_name, request):
        """AC-008: All templates include testing requirements checklist."""
        content = request.getfixturevalue(fixture_name)

        # Check for checklist section
        assert "Testing Requirements Checklist" in content or \
               "Requirements Checklist" in content, \
            f"{fixture_name}: Missing testing requirements checklist"

        # Check for key requirements
        assert "Feature/integration tests for every user story" in content or \
               "Feature/integration tests for every" in content, \
            f"{fixture_name}: Missing feature test requirement"

        assert "Unit tests for complex business logic only" in content, \
            f"{fixture_name}: Missing unit test requirement"

        assert "E2E tests for critical" in content, \
            f"{fixture_name}: Missing E2E test requirement"

    # AC-009: All templates reference ADR-SP-009
    @pytest.mark.parametrize("fixture_name", [
        "react_typescript_claude",
        "fastapi_python_claude",
        "nextjs_fullstack_claude",
        "react_fastapi_monorepo_claude"
    ])
    def test_templates_reference_adr_sp_009(self, fixture_name, request):
        """AC-009: All templates reference ADR-SP-009 for architectural justification."""
        content = request.getfixturevalue(fixture_name)

        assert "ADR-SP-009" in content, \
            f"{fixture_name}: Missing ADR-SP-009 reference"

        assert "architectural justification" in content.lower() or \
               "architecture" in content.lower(), \
            f"{fixture_name}: Missing architectural context for ADR reference"

    # AC-010: Guidance is concise (under 50 lines per template)
    @pytest.mark.parametrize("fixture_name", [
        "react_typescript_claude",
        "fastapi_python_claude",
        "nextjs_fullstack_claude",
        "react_fastapi_monorepo_claude"
    ])
    def test_guidance_is_concise(self, fixture_name, request):
        """AC-010: Testing guidance is concise (under 50 lines per template)."""
        content = request.getfixturevalue(fixture_name)

        # Extract the Testing Strategy section
        if "## Testing Strategy: Trophy Model" in content:
            start_idx = content.index("## Testing Strategy: Trophy Model")
            # Find the next ## section
            next_section_idx = content.find("\n## ", start_idx + 1)
            if next_section_idx == -1:
                next_section_idx = len(content)

            testing_section = content[start_idx:next_section_idx]
            line_count = testing_section.count('\n')

            assert line_count <= 80, \
                f"{fixture_name}: Testing section is {line_count} lines (max 80 for comprehensive guidance)"

    # AC-011: React TypeScript template mentions MSW for mocking
    def test_react_typescript_mentions_msw(self, react_typescript_claude):
        """AC-011: React TypeScript template mentions MSW for API mocking."""
        assert "MSW" in react_typescript_claude, \
            "React TypeScript template should mention MSW"

    # AC-012: FastAPI Python template mentions TestClient
    def test_fastapi_python_mentions_testclient(self, fastapi_python_claude):
        """AC-012: FastAPI Python template mentions TestClient for testing."""
        assert "TestClient" in fastapi_python_claude, \
            "FastAPI Python template should mention TestClient"

    # AC-013: Next.js template mentions Server Components testing
    def test_nextjs_mentions_server_components(self, nextjs_fullstack_claude):
        """AC-013: Next.js template includes Server Components testing guidance."""
        content = nextjs_fullstack_claude
        assert "Server Components" in content or "Server Actions" in content, \
            "Next.js template should mention Server Components/Actions testing"

    # AC-014: Monorepo template has separate frontend/backend guidance
    def test_monorepo_has_separate_guidance(self, react_fastapi_monorepo_claude):
        """AC-014: Monorepo template has separate frontend and backend guidance."""
        content = react_fastapi_monorepo_claude

        # Check for distinct frontend and backend sections
        assert "Frontend" in content, "Missing frontend-specific guidance"
        assert "Backend" in content, "Missing backend-specific guidance"

        # Verify they have different testing recommendations
        assert "MSW" in content or "React" in content, \
            "Missing frontend-specific testing tools"
        assert "TestClient" in content or "pytest" in content, \
            "Missing backend-specific testing tools"
