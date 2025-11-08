"""
Audit Session Management

Handles session state persistence for save/resume functionality.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import SectionResult, FixLog


@dataclass
class AuditSession:
    """Audit session state"""
    session_id: str
    template_path: Path
    created_at: datetime
    updated_at: datetime
    sections_completed: List[int] = field(default_factory=list)
    section_results: Dict[int, SectionResult] = field(default_factory=dict)
    fixes_applied: List[FixLog] = field(default_factory=list)

    @staticmethod
    def create(template_path: Path) -> 'AuditSession':
        """Create a new audit session"""
        now = datetime.now()
        return AuditSession(
            session_id=str(uuid.uuid4())[:8],
            template_path=template_path,
            created_at=now,
            updated_at=now,
        )

    def add_result(self, section_num: int, result: SectionResult):
        """Add a section result to the session"""
        self.section_results[section_num] = result
        if section_num not in self.sections_completed:
            self.sections_completed.append(section_num)
        self.sections_completed.sort()
        self.updated_at = datetime.now()

    def log_fix(self, fix_log: FixLog):
        """Log an applied fix"""
        self.fixes_applied.append(fix_log)
        self.updated_at = datetime.now()

    def get_progress_percentage(self, total_sections: int = 16) -> float:
        """Calculate progress percentage"""
        return (len(self.sections_completed) / total_sections) * 100

    def save(self, path: Path):
        """Save session to JSON file"""
        session_data = {
            'session_id': self.session_id,
            'template_path': str(self.template_path),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'sections_completed': self.sections_completed,
            'section_results': {
                str(k): v.to_dict()
                for k, v in self.section_results.items()
            },
            'fixes_applied': [f.to_dict() for f in self.fixes_applied]
        }

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write with atomic operation
        temp_path = path.with_suffix('.tmp')
        temp_path.write_text(json.dumps(session_data, indent=2))
        temp_path.rename(path)

    @staticmethod
    def load(path: Path) -> 'AuditSession':
        """Load session from JSON file"""
        if not path.exists():
            raise FileNotFoundError(f"Session file not found: {path}")

        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid session file format: {e}")

        # Reconstruct session
        session = AuditSession(
            session_id=data['session_id'],
            template_path=Path(data['template_path']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            sections_completed=data['sections_completed'],
            section_results={
                int(k): SectionResult.from_dict(v)
                for k, v in data['section_results'].items()
            },
            fixes_applied=[
                FixLog.from_dict(f)
                for f in data.get('fixes_applied', [])
            ]
        )

        return session

    def get_session_file_path(self, output_dir: Path) -> Path:
        """Get path for session file"""
        return output_dir / f"audit-session-{self.session_id}.json"

    @staticmethod
    def find_sessions(template_path: Path, output_dir: Path) -> List['AuditSession']:
        """Find all saved sessions for a template"""
        sessions = []
        if not output_dir.exists():
            return sessions

        for session_file in output_dir.glob("audit-session-*.json"):
            try:
                session = AuditSession.load(session_file)
                if session.template_path == template_path:
                    sessions.append(session)
            except (ValueError, FileNotFoundError):
                # Skip invalid session files
                continue

        # Sort by updated time (most recent first)
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions
