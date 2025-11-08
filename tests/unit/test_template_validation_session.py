"""
Unit Tests for Template Validation Session Management

Tests for audit session creation, persistence, and state management.
"""

import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "installer"))


# Use importlib to avoid 'global' keyword issue
_audit_session_module = importlib.import_module('global.lib.template_validation.audit_session')
AuditSession = _audit_session_module.AuditSession
_models_module = importlib.import_module('global.lib.template_validation.models')
SectionResult = _models_module.SectionResult
FixLog = _models_module.FixLog
IssueSeverity = _models_module.IssueSeverity
IssueCategory = _models_module.IssueCategory


class TestAuditSessionCreation:
    """Test audit session creation"""

    def test_create_new_session(self):
        """Create a new audit session"""
        template_path = Path("/templates/react")
        session = AuditSession.create(template_path)

        assert session.session_id is not None
        assert len(session.session_id) == 8
        assert session.template_path == template_path
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.sections_completed == []
        assert session.section_results == {}
        assert session.fixes_applied == []

    def test_session_id_format(self):
        """Session ID should be 8 characters"""
        session1 = AuditSession.create(Path("/templates/test1"))
        session2 = AuditSession.create(Path("/templates/test2"))

        assert len(session1.session_id) == 8
        assert len(session2.session_id) == 8
        assert session1.session_id != session2.session_id

    def test_session_timestamps(self):
        """Verify session timestamps are set correctly"""
        before = datetime.now()
        session = AuditSession.create(Path("/templates/test"))
        after = datetime.now()

        assert before <= session.created_at <= after
        assert before <= session.updated_at <= after
        assert session.created_at == session.updated_at


class TestAuditSessionResults:
    """Test adding results to session"""

    def test_add_section_result(self):
        """Add a section result to session"""
        session = AuditSession.create(Path("/templates/test"))
        result = SectionResult(
            section_num=1,
            section_title="Manifest Analysis",
            score=8.5
        )

        session.add_result(1, result)

        assert 1 in session.section_results
        assert session.section_results[1] == result
        assert 1 in session.sections_completed

    def test_add_multiple_results(self):
        """Add multiple section results"""
        session = AuditSession.create(Path("/templates/test"))

        for i in range(1, 4):
            result = SectionResult(
                section_num=i,
                section_title=f"Section {i}",
                score=7.0 + i
            )
            session.add_result(i, result)

        assert len(session.sections_completed) == 3
        assert len(session.section_results) == 3
        assert session.sections_completed == [1, 2, 3]

    def test_sections_completed_sorted(self):
        """Sections completed should be sorted"""
        session = AuditSession.create(Path("/templates/test"))

        # Add sections in non-sequential order
        for i in [5, 2, 8, 1]:
            result = SectionResult(section_num=i, section_title=f"Section {i}", score=7.0)
            session.add_result(i, result)

        assert session.sections_completed == [1, 2, 5, 8]

    def test_update_existing_result(self):
        """Update an existing section result"""
        session = AuditSession.create(Path("/templates/test"))

        result1 = SectionResult(section_num=1, section_title="Section 1", score=7.0)
        session.add_result(1, result1)
        assert session.section_results[1].score == 7.0

        result2 = SectionResult(section_num=1, section_title="Section 1", score=8.5)
        session.add_result(1, result2)
        assert session.section_results[1].score == 8.5
        assert len(session.sections_completed) == 1

    def test_updated_at_changes(self):
        """Updated timestamp should change when adding results"""
        session = AuditSession.create(Path("/templates/test"))
        original_updated = session.updated_at

        import time
        time.sleep(0.01)  # Small delay to ensure timestamp changes

        result = SectionResult(section_num=1, section_title="Section 1", score=7.0)
        session.add_result(1, result)

        assert session.updated_at > original_updated


class TestAuditSessionFixLogs:
    """Test fix log tracking"""

    def test_log_fix(self):
        """Log a fix application"""
        session = AuditSession.create(Path("/templates/test"))
        fix_log = FixLog(
            timestamp=datetime.now(),
            section_num=1,
            issue_description="Missing file",
            fix_description="Created file",
            success=True
        )

        session.log_fix(fix_log)

        assert len(session.fixes_applied) == 1
        assert session.fixes_applied[0] == fix_log

    def test_log_multiple_fixes(self):
        """Log multiple fixes"""
        session = AuditSession.create(Path("/templates/test"))

        for i in range(3):
            fix_log = FixLog(
                timestamp=datetime.now(),
                section_num=i + 1,
                issue_description=f"Issue {i}",
                fix_description=f"Fixed {i}",
                success=True
            )
            session.log_fix(fix_log)

        assert len(session.fixes_applied) == 3

    def test_fix_log_updates_timestamp(self):
        """Fix logging should update session timestamp"""
        session = AuditSession.create(Path("/templates/test"))
        original_updated = session.updated_at

        import time
        time.sleep(0.01)

        fix_log = FixLog(
            timestamp=datetime.now(),
            section_num=1,
            issue_description="Issue",
            fix_description="Fixed",
            success=True
        )
        session.log_fix(fix_log)

        assert session.updated_at > original_updated


class TestProgressTracking:
    """Test progress tracking"""

    def test_get_progress_percentage_empty(self):
        """Get progress for empty session"""
        session = AuditSession.create(Path("/templates/test"))
        progress = session.get_progress_percentage()
        assert progress == 0.0

    def test_get_progress_percentage_partial(self):
        """Get progress for partial completion"""
        session = AuditSession.create(Path("/templates/test"))

        for i in range(1, 9):  # 8 sections out of 16
            result = SectionResult(section_num=i, section_title=f"Section {i}", score=7.0)
            session.add_result(i, result)

        progress = session.get_progress_percentage(total_sections=16)
        assert progress == 50.0

    def test_get_progress_percentage_complete(self):
        """Get progress for complete audit"""
        session = AuditSession.create(Path("/templates/test"))

        for i in range(1, 17):  # All 16 sections
            result = SectionResult(section_num=i, section_title=f"Section {i}", score=7.0)
            session.add_result(i, result)

        progress = session.get_progress_percentage(total_sections=16)
        assert progress == 100.0

    def test_progress_with_custom_total(self):
        """Test progress with custom total sections"""
        session = AuditSession.create(Path("/templates/test"))

        for i in range(1, 4):  # 3 sections
            result = SectionResult(section_num=i, section_title=f"Section {i}", score=7.0)
            session.add_result(i, result)

        progress = session.get_progress_percentage(total_sections=10)
        assert progress == 30.0


class TestSessionPersistence:
    """Test session save and load"""

    def test_save_session(self):
        """Save session to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "session.json"
            session = AuditSession.create(Path("/templates/test"))

            result = SectionResult(
                section_num=1,
                section_title="Test Section",
                score=7.5
            )
            session.add_result(1, result)

            session.save(session_path)

            assert session_path.exists()
            data = json.loads(session_path.read_text())
            assert data["session_id"] == session.session_id
            assert data["template_path"] == str(Path("/templates/test"))
            assert 1 in data["sections_completed"]

    def test_load_session(self):
        """Load session from file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "session.json"
            original = AuditSession.create(Path("/templates/test"))

            result = SectionResult(
                section_num=2,
                section_title="Test Section",
                score=8.0
            )
            original.add_result(2, result)
            original.save(session_path)

            loaded = AuditSession.load(session_path)

            assert loaded.session_id == original.session_id
            assert loaded.template_path == original.template_path
            assert loaded.sections_completed == [2]
            assert 2 in loaded.section_results

    def test_load_nonexistent_session(self):
        """Load non-existent session raises error"""
        with pytest.raises(FileNotFoundError):
            AuditSession.load(Path("/nonexistent/session.json"))

    def test_load_invalid_json(self):
        """Load invalid JSON raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "bad.json"
            session_path.write_text("{ invalid json")

            with pytest.raises(ValueError):
                AuditSession.load(session_path)

    def test_save_creates_directory(self):
        """Save should create parent directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "subdir" / "nested" / "session.json"
            session = AuditSession.create(Path("/templates/test"))

            session.save(session_path)

            assert session_path.exists()
            assert session_path.parent.exists()

    def test_session_roundtrip(self):
        """Save and load session preserves data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "session.json"
            original = AuditSession.create(Path("/templates/react"))

            # Add results
            for i in range(1, 4):
                result = SectionResult(
                    section_num=i,
                    section_title=f"Section {i}",
                    score=7.0 + i * 0.5
                )
                original.add_result(i, result)

            # Add fixes
            for i in range(1, 3):
                fix = FixLog(
                    timestamp=datetime.now(),
                    section_num=i,
                    issue_description=f"Issue {i}",
                    fix_description=f"Fixed {i}",
                    success=True
                )
                original.log_fix(fix)

            original.save(session_path)
            restored = AuditSession.load(session_path)

            assert restored.session_id == original.session_id
            assert restored.template_path == original.template_path
            assert len(restored.sections_completed) == 3
            assert len(restored.fixes_applied) == 2
            assert restored.section_results[1].score == original.section_results[1].score


class TestSessionFilePath:
    """Test session file path generation"""

    def test_get_session_file_path(self):
        """Get expected session file path"""
        session = AuditSession.create(Path("/templates/test"))
        output_dir = Path("/output/reports")

        file_path = session.get_session_file_path(output_dir)

        assert file_path == output_dir / f"audit-session-{session.session_id}.json"


class TestFindSessions:
    """Test finding saved sessions"""

    def test_find_sessions_empty_dir(self):
        """Find sessions in empty directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sessions = AuditSession.find_sessions(
                Path("/templates/test"),
                Path(tmpdir)
            )
            assert sessions == []

    def test_find_sessions_no_dir(self):
        """Find sessions when directory doesn't exist"""
        sessions = AuditSession.find_sessions(
            Path("/templates/test"),
            Path("/nonexistent/dir")
        )
        assert sessions == []

    def test_find_sessions_matching_template(self):
        """Find sessions for specific template"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            template_path = Path("/templates/react")

            # Create sessions
            session1 = AuditSession.create(template_path)
            session2 = AuditSession.create(template_path)

            session1.save(output_dir / f"audit-session-{session1.session_id}.json")
            session2.save(output_dir / f"audit-session-{session2.session_id}.json")

            found = AuditSession.find_sessions(template_path, output_dir)

            assert len(found) == 2
            assert all(s.template_path == template_path for s in found)

    def test_find_sessions_filters_template(self):
        """Find sessions filters by template path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create sessions for different templates
            session1 = AuditSession.create(Path("/templates/react"))
            session2 = AuditSession.create(Path("/templates/python"))

            session1.save(output_dir / f"audit-session-{session1.session_id}.json")
            session2.save(output_dir / f"audit-session-{session2.session_id}.json")

            found = AuditSession.find_sessions(Path("/templates/react"), output_dir)

            assert len(found) == 1
            assert found[0].template_path == Path("/templates/react")

    def test_find_sessions_sorted_by_date(self):
        """Find sessions sorted by most recent first"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            template_path = Path("/templates/test")

            sessions = []
            for i in range(3):
                session = AuditSession.create(template_path)
                session.save(output_dir / f"audit-session-{session.session_id}.json")
                sessions.append(session)
                import time
                time.sleep(0.01)

            found = AuditSession.find_sessions(template_path, output_dir)

            # Most recent should be first
            for i in range(len(found) - 1):
                assert found[i].updated_at >= found[i + 1].updated_at

    def test_find_sessions_skips_invalid(self):
        """Find sessions skips invalid files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            template_path = Path("/templates/test")

            # Create valid session
            session = AuditSession.create(template_path)
            session.save(output_dir / f"audit-session-{session.session_id}.json")

            # Create invalid JSON file
            (output_dir / "audit-session-bad.json").write_text("{ invalid")

            found = AuditSession.find_sessions(template_path, output_dir)

            assert len(found) == 1
            assert found[0].session_id == session.session_id
