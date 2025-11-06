#!/usr/bin/env python3
"""
Demo Script for AI-Powered Codebase Analyzer

Demonstrates the codebase analyzer capabilities by analyzing the taskwright project itself.
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / "installer" / "global"))

from lib.codebase_analyzer import CodebaseAnalyzer, analyze_codebase


def demo_basic_analysis():
    """Demonstrate basic codebase analysis."""
    print("=" * 80)
    print("DEMO: Basic Codebase Analysis")
    print("=" * 80)
    print()

    # Analyze the taskwright project itself
    project_root = Path(__file__).parent

    print(f"Analyzing codebase at: {project_root}")
    print("Using heuristic analysis (agent not available)...")
    print()

    analyzer = CodebaseAnalyzer(use_agent=False, max_files=5)
    analysis = analyzer.analyze_codebase(
        codebase_path=project_root,
        template_context={
            "name": "Taskwright",
            "language": "Polyglot",
            "description": "AI-powered task workflow system"
        }
    )

    # Display summary
    print(analysis.get_summary())
    print()
    print("=" * 80)


def demo_quick_analysis():
    """Demonstrate quick analysis mode."""
    print()
    print("=" * 80)
    print("DEMO: Quick Analysis (Structure Only)")
    print("=" * 80)
    print()

    project_root = Path(__file__).parent

    print(f"Quick analyzing: {project_root}")
    print()

    analyzer = CodebaseAnalyzer()
    analysis = analyzer.quick_analyze(project_root)

    print(f"Primary Language: {analysis.technology.primary_language}")
    print(f"Frameworks: {', '.join(analysis.technology.frameworks) or 'None detected'}")
    print(f"Testing: {', '.join(analysis.technology.testing_frameworks) or 'None detected'}")
    print(f"Architecture: {analysis.architecture.architectural_style}")
    print(f"Overall Score: {analysis.quality.overall_score}/100")
    print(f"Confidence: {analysis.overall_confidence.level.value} ({analysis.overall_confidence.percentage}%)")
    print()
    print("=" * 80)


def demo_save_and_export():
    """Demonstrate saving and exporting results."""
    print()
    print("=" * 80)
    print("DEMO: Save and Export Analysis")
    print("=" * 80)
    print()

    project_root = Path(__file__).parent

    print("Analyzing and saving results...")
    analyzer = CodebaseAnalyzer(use_agent=False, max_files=3)
    analysis, json_path = analyzer.analyze_and_save(
        codebase_path=project_root,
        output_filename="taskwright_analysis.json"
    )

    print(f"Saved to: {json_path}")
    print()

    # Export markdown
    md_path = json_path.parent / "taskwright_analysis.md"
    analyzer.export_markdown_report(analysis, md_path)
    print(f"Markdown report: {md_path}")
    print()
    print("=" * 80)


def demo_technology_detection():
    """Demonstrate detailed technology detection."""
    print()
    print("=" * 80)
    print("DEMO: Technology Stack Detection")
    print("=" * 80)
    print()

    project_root = Path(__file__).parent

    analyzer = CodebaseAnalyzer(use_agent=False, max_files=3)
    analysis = analyzer.analyze_codebase(project_root)

    tech = analysis.technology

    print(f"Primary Language: {tech.primary_language}")
    print()

    if tech.frameworks:
        print("Frameworks:")
        for framework in tech.frameworks:
            print(f"  - {framework}")
        print()

    if tech.testing_frameworks:
        print("Testing Frameworks:")
        for framework in tech.testing_frameworks:
            print(f"  - {framework}")
        print()

    if tech.build_tools:
        print("Build Tools:")
        for tool in tech.build_tools:
            print(f"  - {tool}")
        print()

    print(f"Detection Confidence: {tech.confidence.level.value} ({tech.confidence.percentage}%)")
    print()
    print("=" * 80)


def demo_architecture_detection():
    """Demonstrate architecture pattern detection."""
    print()
    print("=" * 80)
    print("DEMO: Architecture Pattern Detection")
    print("=" * 80)
    print()

    project_root = Path(__file__).parent

    analyzer = CodebaseAnalyzer(use_agent=False, max_files=3)
    analysis = analyzer.analyze_codebase(project_root)

    arch = analysis.architecture

    print(f"Architectural Style: {arch.architectural_style}")
    print()

    if arch.patterns:
        print("Design Patterns Detected:")
        for pattern in arch.patterns:
            print(f"  - {pattern}")
        print()

    if arch.layers:
        print("Architectural Layers:")
        for layer in arch.layers:
            print(f"  - {layer.name}: {layer.description}")
        print()

    print(f"Dependency Flow: {arch.dependency_flow}")
    print()
    print(f"Confidence: {arch.confidence.level.value} ({arch.confidence.percentage}%)")
    print()
    print("=" * 80)


def demo_convenience_function():
    """Demonstrate the convenience function."""
    print()
    print("=" * 80)
    print("DEMO: Convenience Function")
    print("=" * 80)
    print()

    project_root = Path(__file__).parent

    print("Using analyze_codebase() convenience function...")
    print()

    # Simple one-liner
    analysis = analyze_codebase(
        project_root,
        template_context={"name": "Taskwright", "language": "Polyglot"}
    )

    print(f"Language: {analysis.technology.primary_language}")
    print(f"Architecture: {analysis.architecture.architectural_style}")
    print(f"Quality: {analysis.quality.overall_score}/100")
    print()
    print("=" * 80)


def main():
    """Run all demos."""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                               ║")
    print("║                  AI-Powered Codebase Analyzer - Demo Suite                   ║")
    print("║                                                                               ║")
    print("║  This demo analyzes the taskwright project itself to demonstrate the         ║")
    print("║  capabilities of the AI-powered codebase analysis system.                    ║")
    print("║                                                                               ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")
    print()

    try:
        # Run demos
        demo_basic_analysis()
        demo_quick_analysis()
        demo_technology_detection()
        demo_architecture_detection()
        demo_convenience_function()
        demo_save_and_export()

        print()
        print("╔═══════════════════════════════════════════════════════════════════════════════╗")
        print("║                            Demo Complete! ✓                                  ║")
        print("╚═══════════════════════════════════════════════════════════════════════════════╝")
        print()
        print("Check the following files:")
        print("  - ~/.agentecflow/state/codebase_analysis/taskwright_analysis.json")
        print("  - ~/.agentecflow/state/codebase_analysis/taskwright_analysis.md")
        print()

    except Exception as e:
        print()
        print(f"ERROR: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
