"""
Template Validation Library

Comprehensive validation framework for template quality assurance.
"""

from .models import (
    ValidationIssue,
    IssueSeverity,
    SectionResult,
    AuditResult,
    ValidateConfig,
)
from .audit_session import AuditSession
from .comprehensive_auditor import ComprehensiveAuditor, AuditSection
from .audit_report_generator import AuditReportGenerator
from .orchestrator import TemplateValidateOrchestrator
from .progressive_disclosure_validator import (
    validate_agent_split_structure,
    validate_claude_md_split,
    generate_split_validation_report,
    SplitMetrics,
)

__all__ = [
    "ValidationIssue",
    "IssueSeverity",
    "SectionResult",
    "AuditResult",
    "ValidateConfig",
    "AuditSession",
    "ComprehensiveAuditor",
    "AuditSection",
    "AuditReportGenerator",
    "TemplateValidateOrchestrator",
    "validate_agent_split_structure",
    "validate_claude_md_split",
    "generate_split_validation_report",
    "SplitMetrics",
]
