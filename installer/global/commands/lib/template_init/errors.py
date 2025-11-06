"""
Error classes for template-init command
"""


class TemplateInitError(Exception):
    """Base exception for template-init errors"""
    pass


class QASessionCancelledError(TemplateInitError):
    """User cancelled Q&A session"""
    pass


class TemplateGenerationError(TemplateInitError):
    """AI template generation failed"""
    pass


class TemplateSaveError(TemplateInitError):
    """Failed to save template to disk"""
    pass


class AgentSetupError(TemplateInitError):
    """Failed to set up agents for template"""
    pass
