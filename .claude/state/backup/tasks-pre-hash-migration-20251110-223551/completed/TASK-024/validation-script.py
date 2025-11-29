#!/usr/bin/env python3
"""
TASK-024 Documentation Validation Suite
Validates documentation changes for RequireKit feature removal
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
import json

@dataclass
class ValidationResult:
    """Result of a validation check"""
    category: str
    test_name: str
    passed: bool
    details: str = ""

class DocumentationValidator:
    """Validates documentation changes for TASK-024"""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.results: List[ValidationResult] = []
        self.files_to_validate = [
            "docs/guides/GETTING-STARTED.md",
            "docs/guides/QUICK_REFERENCE.md",
            "docs/guides/taskwright-workflow.md"
        ]

    def validate_all(self) -> Tuple[int, int]:
        """Run all validation checks. Returns (passed, total)"""
        print("=" * 70)
        print("TASK-024 DOCUMENTATION VALIDATION SUITE")
        print("=" * 70)
        print()

        # 1. Markdown Syntax Validation (COMPILATION CHECK)
        print("1. MARKDOWN SYNTAX VALIDATION (Compilation Check)")
        print("-" * 70)
        self.validate_markdown_syntax()
        print()

        # 2. Content Validation
        print("2. CONTENT VALIDATION")
        print("-" * 70)
        self.validate_no_bdd_mode()
        self.validate_no_ears_flag()
        self.validate_no_ears_notation()
        self.validate_requirekit_urls()
        self.validate_command_syntax()
        print()

        # 3. Link Validation
        print("3. LINK VALIDATION")
        print("-" * 70)
        self.validate_internal_links()
        self.validate_external_links()
        print()

        # 4. Syntax Validation
        print("4. SYNTAX VALIDATION")
        print("-" * 70)
        self.validate_code_blocks()
        self.validate_tables()
        self.validate_callout_boxes()
        print()

        # 5. Cross-Reference Validation
        print("5. CROSS-REFERENCE VALIDATION")
        print("-" * 70)
        self.validate_command_consistency()
        self.validate_phase_numbering()
        self.validate_terminology()
        print()

        # 6. Example Validation
        print("6. EXAMPLE VALIDATION")
        print("-" * 70)
        self.validate_taskwright_syntax()
        self.validate_workflow_examples()
        self.validate_no_requirekit_examples()
        print()

        return self.summarize_results()

    def read_file(self, rel_path: str) -> str:
        """Read file contents"""
        file_path = self.base_path / rel_path
        if not file_path.exists():
            return ""
        return file_path.read_text()

    def add_result(self, category: str, test_name: str, passed: bool, details: str = ""):
        """Add validation result"""
        result = ValidationResult(category, test_name, passed, details)
        self.results.append(result)

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if details and not passed:
            print(f"    Details: {details}")

    # ==================== MARKDOWN SYNTAX VALIDATION ====================

    def validate_markdown_syntax(self):
        """Validate markdown files parse correctly"""
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)
            if not content:
                self.add_result("Markdown Syntax", f"{file_path} - File exists", False, "File not found")
                continue

            # Check file is not empty
            self.add_result("Markdown Syntax", f"{file_path} - File not empty", len(content) > 0)

            # Check for basic markdown structure
            has_headers = bool(re.search(r'^#{1,6}\s+', content, re.MULTILINE))
            self.add_result("Markdown Syntax", f"{file_path} - Has headers", has_headers)

            # Check for unmatched code fences
            code_fence_count = len(re.findall(r'^```', content, re.MULTILINE))
            fences_balanced = (code_fence_count % 2) == 0
            self.add_result("Markdown Syntax", f"{file_path} - Code fences balanced",
                          fences_balanced,
                          f"Found {code_fence_count} fences" if not fences_balanced else "")

            # Check for malformed links
            malformed_links = re.findall(r'\[([^\]]*)\]\s+\(([^)]*)\)', content)
            no_malformed = len(malformed_links) == 0
            self.add_result("Markdown Syntax", f"{file_path} - No malformed links",
                          no_malformed,
                          f"Found {len(malformed_links)} malformed links" if not no_malformed else "")

    # ==================== CONTENT VALIDATION ====================

    def validate_no_bdd_mode(self):
        """Validate no instances of --mode=bdd"""
        pattern = r'--mode=bdd'
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)
            matches = re.findall(pattern, content, re.IGNORECASE)
            passed = len(matches) == 0
            self.add_result("Content", f"{file_path} - No --mode=bdd", passed,
                          f"Found {len(matches)} instances" if not passed else "")

    def validate_no_ears_flag(self):
        """Validate no instances of --ears flag"""
        pattern = r'--ears'
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)
            matches = re.findall(pattern, content, re.IGNORECASE)
            passed = len(matches) == 0
            self.add_result("Content", f"{file_path} - No --ears flag", passed,
                          f"Found {len(matches)} instances" if not passed else "")

    def validate_no_ears_notation(self):
        """Validate no EARS notation keywords in requirement examples"""
        # Look for EARS patterns in example/code blocks
        ears_patterns = [
            r'WHEN\s+.*\s+THEN',  # EARS patterns
            r'WHILE\s+.*\s+SHALL',
            r'WHERE\s+.*\s+SHALL',
            r'IF\s+.*\s+THEN\s+.*\s+SHALL',
        ]

        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Extract code blocks
            code_blocks = re.findall(r'```(?:.*?)\n(.*?)```', content, re.DOTALL)

            for pattern in ears_patterns:
                for i, block in enumerate(code_blocks):
                    matches = re.findall(pattern, block, re.IGNORECASE)
                    if matches:
                        passed = False
                        self.add_result("Content",
                                      f"{file_path} - No EARS notation in examples",
                                      False,
                                      f"Found EARS pattern '{pattern}' in code block {i+1}")
                        break
                else:
                    continue
                break
            else:
                self.add_result("Content", f"{file_path} - No EARS notation in examples", True)

    def validate_requirekit_urls(self):
        """Validate all RequireKit GitHub URLs are correct"""
        correct_url = "https://github.com/requirekit/require-kit"
        pattern = r'https://github\.com/[^/\s]+/require-?kit'

        for file_path in self.files_to_validate:
            content = self.read_file(file_path)
            matches = re.findall(pattern, content, re.IGNORECASE)

            all_correct = all(url == correct_url for url in matches)
            self.add_result("Content", f"{file_path} - RequireKit URLs correct", all_correct,
                          f"Found incorrect URLs: {[u for u in matches if u != correct_url]}" if not all_correct else "")

    def validate_command_syntax(self):
        """Validate command syntax matches Taskwright-only capabilities"""
        invalid_patterns = [
            (r'/task-create.*--ears', "task-create with --ears flag"),
            (r'/task-work.*--mode=bdd', "task-work with BDD mode"),
            (r'/requirement-', "RequireKit commands"),
            (r'/epic-', "RequireKit epic commands"),
            (r'/feature-', "RequireKit feature commands"),
        ]

        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            for pattern, description in invalid_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                passed = len(matches) == 0
                self.add_result("Content", f"{file_path} - No {description}", passed,
                              f"Found {len(matches)} instances" if not passed else "")

    # ==================== LINK VALIDATION ====================

    def validate_internal_links(self):
        """Validate internal links resolve correctly"""
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Extract markdown links [text](path)
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

            broken_links = []
            for link_text, link_path in links:
                # Skip external links
                if link_path.startswith('http://') or link_path.startswith('https://'):
                    continue

                # Skip anchors only
                if link_path.startswith('#'):
                    continue

                # Remove anchor from path
                link_path = link_path.split('#')[0]

                # Resolve relative to docs/guides/
                file_dir = Path("docs/guides")
                target_path = (self.base_path / file_dir / link_path).resolve()

                # Also check from base path
                alt_target_path = (self.base_path / link_path).resolve()

                if not target_path.exists() and not alt_target_path.exists():
                    broken_links.append(f"{link_text} -> {link_path}")

            passed = len(broken_links) == 0
            self.add_result("Links", f"{file_path} - Internal links valid", passed,
                          f"Broken: {broken_links}" if not passed else "")

    def validate_external_links(self):
        """Validate external links are accessible (format check only)"""
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Extract external links
            links = re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', content)

            malformed = []
            for link_text, url in links:
                # Basic URL format validation
                if not re.match(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?', url):
                    malformed.append(f"{link_text} -> {url}")

            passed = len(malformed) == 0
            self.add_result("Links", f"{file_path} - External links well-formed", passed,
                          f"Malformed: {malformed}" if not passed else "")

    # ==================== SYNTAX VALIDATION ====================

    def validate_code_blocks(self):
        """Validate code blocks have proper syntax highlighting"""
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Find code blocks without language specifier
            no_lang_blocks = re.findall(r'^```\n', content, re.MULTILINE)

            passed = len(no_lang_blocks) == 0
            self.add_result("Syntax", f"{file_path} - Code blocks have language", passed,
                          f"Found {len(no_lang_blocks)} blocks without language" if not passed else "")

    def validate_tables(self):
        """Validate tables render correctly"""
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Extract tables (header + separator)
            table_pattern = r'\|.*\|\n\|[-:\s|]+\|'
            tables = re.findall(table_pattern, content)

            malformed = []
            for i, table in enumerate(tables):
                lines = table.split('\n')
                if len(lines) < 2:
                    malformed.append(f"Table {i+1}: incomplete")
                    continue

                # Check column count matches
                header_cols = len([c for c in lines[0].split('|') if c.strip()])
                sep_cols = len([c for c in lines[1].split('|') if c.strip()])

                if header_cols != sep_cols:
                    malformed.append(f"Table {i+1}: column mismatch")

            passed = len(malformed) == 0
            self.add_result("Syntax", f"{file_path} - Tables well-formed", passed,
                          f"Issues: {malformed}" if not passed else "")

    def validate_callout_boxes(self):
        """Validate callout boxes use proper markdown format"""
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Find callout boxes (blockquotes)
            callouts = re.findall(r'^>\s*\*\*.*?\*\*', content, re.MULTILINE)

            # Validate RequireKit callouts are present
            requirekit_callouts = [c for c in callouts if 'RequireKit' in c or 'Formal Requirements' in c]

            passed = len(requirekit_callouts) >= 3
            self.add_result("Syntax", f"{file_path} - RequireKit callouts present", passed,
                          f"Found {len(requirekit_callouts)}/3 expected callouts" if not passed else "")

    # ==================== CROSS-REFERENCE VALIDATION ====================

    def validate_command_consistency(self):
        """Validate command syntax is consistent across all guides"""
        # Extract all /task-* commands from all files
        commands = {}
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)
            file_commands = re.findall(r'/task-\w+(?:\s+[^\n]+)?', content)
            commands[file_path] = file_commands

        # Check /task-work flags are consistent
        work_commands = {}
        for file_path, cmds in commands.items():
            work_cmds = [c for c in cmds if c.startswith('/task-work')]
            work_commands[file_path] = work_cmds

        # Valid flags
        valid_flags = ['--mode=standard', '--mode=tdd', '--design-only', '--implement-only']

        for file_path, cmds in work_commands.items():
            for cmd in cmds:
                # Extract flags
                flags = re.findall(r'--[\w-]+=?[\w-]*', cmd)
                invalid = [f for f in flags if f not in valid_flags and not f.startswith('--')]

                if invalid:
                    self.add_result("Cross-Reference", f"{file_path} - Command flags valid", False,
                                  f"Invalid flags: {invalid}")
                    break
            else:
                self.add_result("Cross-Reference", f"{file_path} - Command flags valid", True)

    def validate_phase_numbering(self):
        """Validate phase numbering is consistent"""
        expected_phases = [
            "Phase 1", "Phase 2", "Phase 2.5A", "Phase 2.5B",
            "Phase 2.7", "Phase 2.8", "Phase 3", "Phase 4",
            "Phase 4.5", "Phase 5", "Phase 5.5"
        ]

        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Extract phase references
            phases = re.findall(r'Phase \d+(?:\.\d+)?[AB]?', content)

            invalid = [p for p in set(phases) if p not in expected_phases]

            passed = len(invalid) == 0
            self.add_result("Cross-Reference", f"{file_path} - Phase numbering consistent", passed,
                          f"Unexpected phases: {invalid}" if not passed else "")

    def validate_terminology(self):
        """Validate terminology is uniform"""
        # Check for consistent use of key terms
        terms_to_check = {
            'Taskwright': r'\btaskwright\b',  # Should be capitalized
            'quality gates': r'quality[- ]gates?',  # Should be lowercase
        }

        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Check Taskwright capitalization (outside code blocks)
            non_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
            lowercase_taskwright = re.findall(r'\btaskwright\b', non_code)

            # Allow in commands and code
            valid_lowercase = [m for m in lowercase_taskwright if '`' not in m]

            passed = len(valid_lowercase) == 0
            self.add_result("Cross-Reference", f"{file_path} - Taskwright capitalized", passed,
                          f"Found {len(valid_lowercase)} lowercase instances" if not passed else "")

    # ==================== EXAMPLE VALIDATION ====================

    def validate_taskwright_syntax(self):
        """Validate all command examples use valid Taskwright syntax"""
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Extract code blocks
            code_blocks = re.findall(r'```bash\n(.*?)```', content, re.DOTALL)

            invalid_commands = []
            for block in code_blocks:
                # Check for RequireKit commands
                requirekit_cmds = re.findall(r'/(?:requirement|epic|feature)-', block)
                if requirekit_cmds:
                    invalid_commands.extend(requirekit_cmds)

                # Check for invalid flags
                invalid_flags = re.findall(r'/task-work.*--(?:ears|bdd)', block)
                if invalid_flags:
                    invalid_commands.extend(invalid_flags)

            passed = len(invalid_commands) == 0
            self.add_result("Examples", f"{file_path} - Valid Taskwright syntax", passed,
                          f"Invalid commands: {invalid_commands}" if not passed else "")

    def validate_workflow_examples(self):
        """Validate workflow examples are self-contained"""
        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Find workflow examples (sections with multiple commands)
            workflow_sections = re.findall(r'```bash\n((?:/task-.*?\n)+)```', content, re.DOTALL)

            incomplete = []
            for i, section in enumerate(workflow_sections):
                commands = re.findall(r'/task-\w+', section)

                # Check for complete workflow (create -> work -> complete)
                has_create = any('task-create' in c for c in commands)
                has_work = any('task-work' in c for c in commands)
                has_complete = any('task-complete' in c for c in commands)

                # If it's a multi-command example, it should be complete
                if len(commands) >= 2 and has_create and not (has_work and has_complete):
                    incomplete.append(f"Example {i+1}: incomplete workflow")

            passed = len(incomplete) == 0
            self.add_result("Examples", f"{file_path} - Workflows self-contained", passed,
                          f"Issues: {incomplete}" if not passed else "")

    def validate_no_requirekit_examples(self):
        """Validate no references to RequireKit features in examples"""
        requirekit_features = [
            'EARS notation',
            'BDD scenarios',
            'epic.*hierarchy',
            'feature.*hierarchy',
            'Gherkin',
            'PM tool',
            'Jira integration',
            'Linear integration',
        ]

        for file_path in self.files_to_validate:
            content = self.read_file(file_path)

            # Extract code blocks
            code_blocks = re.findall(r'```.*?\n(.*?)```', content, re.DOTALL)

            found_features = []
            for pattern in requirekit_features:
                for block in code_blocks:
                    if re.search(pattern, block, re.IGNORECASE):
                        found_features.append(pattern)
                        break

            passed = len(found_features) == 0
            self.add_result("Examples", f"{file_path} - No RequireKit examples", passed,
                          f"Found: {found_features}" if not passed else "")

    # ==================== SUMMARY ====================

    def summarize_results(self) -> Tuple[int, int]:
        """Print summary and return (passed, total)"""
        print("=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print()

        # Group by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)

        total_passed = 0
        total_tests = 0

        for category, results in sorted(categories.items()):
            passed = sum(1 for r in results if r.passed)
            total = len(results)
            total_passed += passed
            total_tests += total

            status = "✅" if passed == total else "❌"
            print(f"{status} {category}: {passed}/{total} passed")

        print()
        print(f"TOTAL: {total_passed}/{total_tests} tests passed ({100*total_passed//total_tests}%)")
        print()

        # Show failures
        failures = [r for r in self.results if not r.passed]
        if failures:
            print("=" * 70)
            print("FAILED TESTS DETAIL")
            print("=" * 70)
            print()
            for failure in failures:
                print(f"❌ {failure.category} > {failure.test_name}")
                if failure.details:
                    print(f"   {failure.details}")
            print()

        return (total_passed, total_tests)

def main():
    """Run validation suite"""
    base_path = Path(__file__).parent.parent.parent
    validator = DocumentationValidator(base_path)

    passed, total = validator.validate_all()

    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
