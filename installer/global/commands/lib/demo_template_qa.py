#!/usr/bin/env python3
"""
Demo script for Template Q&A Session.

Shows how to use the TemplateQASession class in practice.
Part of TASK-001B: Interactive Q&A Session for /template-init (Greenfield)
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from template_qa_session import TemplateQASession, GreenfieldAnswers
from template_qa_display import print_banner, print_info, print_success, print_error


def demo_interactive_mode():
    """
    Demo: Interactive Q&A mode.

    Run this to see the full Q&A flow.
    """
    print_banner("Demo: Interactive Q&A Mode")
    print_info("This will run the complete Q&A session interactively.")
    print_info("Press Ctrl+C to save and exit at any time.\n")

    try:
        session = TemplateQASession()
        result = session.run()

        if result:
            print_success("Q&A completed successfully!")
            print_info(f"\nTemplate Name: {result.template_name}")
            print_info(f"Language: {result.primary_language}")
            print_info(f"Framework: {result.framework}")
            print_info(f"Architecture: {result.architecture_pattern}")

            # Show full result
            print("\n" + "=" * 60)
            print("Complete Result:")
            print("=" * 60)
            import json
            print(json.dumps(result.to_dict(), indent=2))

    except KeyboardInterrupt:
        print_info("\n\nSession interrupted. Progress saved.")
        print_info("Run this script again to resume.")
    except Exception as e:
        print_error(f"Error during Q&A: {e}")
        raise


def demo_skip_mode():
    """
    Demo: Skip Q&A mode (uses all defaults).

    Useful for testing or when defaults are acceptable.
    """
    print_banner("Demo: Skip Q&A Mode (Defaults)")
    print_info("Using default values for all questions.\n")

    try:
        session = TemplateQASession(skip_qa=True)

        # Simulate minimal setup
        session.answers = {
            "template_name": "demo-template",
            "template_purpose": "quick_start",
            "primary_language": "python",
            "framework": "fastapi",
            "framework_version": "latest",
            "architecture_pattern": "clean",
            "domain_modeling": "rich",
            "layer_organization": "single",
            "standard_folders": ["src", "tests"],
            "unit_testing_framework": "auto",
            "testing_scope": ["unit", "integration"],
            "test_pattern": "aaa",
            "error_handling": "result",
            "validation_approach": "fluent",
            "dependency_injection": "builtin",
            "configuration_approach": "both",
        }

        # Build result
        result = session._build_result()

        print_success("Result generated using defaults!")
        print_info(f"\nTemplate Name: {result.template_name}")
        print_info(f"Language: {result.primary_language}")
        print_info(f"Framework: {result.framework}")

    except Exception as e:
        print_error(f"Error: {e}")
        raise


def demo_resume_session():
    """
    Demo: Resume from saved session.

    Shows how to load and continue from a saved session.
    """
    print_banner("Demo: Resume Session")
    print_info("Attempting to resume from saved session.\n")

    from template_qa_persistence import session_exists, get_session_summary

    if not session_exists():
        print_info("No saved session found.")
        print_info("Run demo_interactive_mode() and press Ctrl+C to create one.")
        return

    # Show session summary
    summary = get_session_summary()
    print_info(f"Found session saved at: {summary.get('saved_at', 'unknown')}")
    print_info(f"Progress: {summary.get('sections_completed', 0)} sections completed")
    print_info(f"Total answers: {summary.get('total_answers', 0)}\n")

    try:
        session = TemplateQASession()
        result = session.run()

        if result:
            print_success("Q&A completed successfully!")

    except KeyboardInterrupt:
        print_info("\n\nSession interrupted again. Progress saved.")


def demo_validation():
    """
    Demo: Input validation examples.

    Shows how validators work.
    """
    print_banner("Demo: Input Validation")

    from template_qa_validator import (
        validate_template_name,
        validate_url,
        validate_version_string,
        ValidationError,
    )

    # Test template name validation
    print_info("Testing template name validation:\n")

    test_names = [
        ("my-template", True),
        ("dotnet-maui-mvvm-template", True),
        ("ab", False),  # Too short
        ("my template", False),  # Contains space
        ("-my-template", False),  # Starts with hyphen
    ]

    for name, should_pass in test_names:
        try:
            result = validate_template_name(name)
            if should_pass:
                print_success(f"✓ '{name}' → Valid")
            else:
                print_error(f"✗ '{name}' → Should have failed but passed")
        except ValidationError as e:
            if not should_pass:
                print_info(f"✓ '{name}' → Correctly rejected: {e}")
            else:
                print_error(f"✗ '{name}' → Should have passed but failed: {e}")

    # Test URL validation
    print_info("\n\nTesting URL validation:\n")

    test_urls = [
        ("https://example.com", True),
        ("http://localhost:8080", True),
        ("not-a-url", False),
        ("ftp://example.com", False),
    ]

    for url, should_pass in test_urls:
        try:
            result = validate_url(url)
            if should_pass:
                print_success(f"✓ '{url}' → Valid")
            else:
                print_error(f"✗ '{url}' → Should have failed but passed")
        except ValidationError as e:
            if not should_pass:
                print_info(f"✓ '{url}' → Correctly rejected: {e}")
            else:
                print_error(f"✗ '{url}' → Should have passed but failed: {e}")


def demo_persistence():
    """
    Demo: Session persistence.

    Shows save/load functionality.
    """
    print_banner("Demo: Session Persistence")

    from template_qa_persistence import save_session, load_session, session_exists
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        session_file = Path(tmpdir) / "demo-session.json"

        # Create sample answers
        answers = {
            "template_name": "demo-template",
            "primary_language": "python",
            "framework": "fastapi",
            "testing_scope": ["unit", "integration"],
        }

        # Save
        print_info("Saving session...")
        save_session(answers, session_file)
        print_success(f"Session saved to: {session_file}")

        # Check exists
        print_info("\nChecking if session exists...")
        exists = session_exists(session_file)
        print_success(f"Session exists: {exists}")

        # Load
        print_info("\nLoading session...")
        loaded = load_session(session_file)
        print_success("Session loaded successfully!")

        # Verify
        print_info("\nVerifying data integrity:")
        for key, value in answers.items():
            loaded_value = loaded.get(key)
            if value == loaded_value:
                print_success(f"  ✓ {key}: {value}")
            else:
                print_error(f"  ✗ {key}: Expected {value}, got {loaded_value}")


def main():
    """Main demo menu."""
    print_banner("Template Q&A Session Demo")
    print_info("Choose a demo to run:")
    print_info("  1. Interactive Q&A mode (full flow)")
    print_info("  2. Skip mode (use defaults)")
    print_info("  3. Resume session")
    print_info("  4. Validation examples")
    print_info("  5. Persistence examples")
    print_info("  q. Quit")

    choice = input("\nEnter choice (1-5, q): ").strip().lower()

    if choice == "1":
        demo_interactive_mode()
    elif choice == "2":
        demo_skip_mode()
    elif choice == "3":
        demo_resume_session()
    elif choice == "4":
        demo_validation()
    elif choice == "5":
        demo_persistence()
    elif choice == "q":
        print_info("Goodbye!")
    else:
        print_error("Invalid choice")


if __name__ == "__main__":
    main()
