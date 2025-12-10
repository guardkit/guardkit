"""
Ambiguity detection algorithms for clarifying questions phase.

This module provides detection functions that analyze task context to identify
areas of ambiguity requiring clarification before implementation planning.
Each detection function looks for specific types of missing information or
unclear requirements that could lead to incorrect assumptions.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import re


@dataclass
class TaskContext:
    """Context information about the task being analyzed.

    Attributes:
        task_id: Unique task identifier (e.g., TASK-CLQ-002)
        title: Task title
        description: Detailed task description
        acceptance_criteria: List of acceptance criteria
        complexity: Complexity score (0-10)
        tags: List of task tags
        metadata: Additional task metadata
    """
    task_id: str
    title: str
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)
    complexity: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodebaseContext:
    """Context information about the codebase.

    Attributes:
        detected_stack: Detected technology stack (python, react, etc.)
        existing_patterns: Design patterns found in codebase
        external_services: External APIs/services in use
        file_structure: Key file paths and organization
        tech_inventory: Technologies/libraries in use
    """
    detected_stack: str = "unknown"
    existing_patterns: List[str] = field(default_factory=list)
    external_services: List[str] = field(default_factory=list)
    file_structure: Dict[str, Any] = field(default_factory=dict)
    tech_inventory: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ScopeAmbiguity:
    """Detected ambiguity in task scope boundaries.

    Attributes:
        feature: Base feature mentioned in task (e.g., "auth", "user")
        unmentioned_extensions: Common extensions not explicitly included/excluded
        confidence: Confidence level of detection (0.0-1.0)
    """
    feature: str
    unmentioned_extensions: List[str]
    confidence: float


@dataclass
class TechChoice:
    """Single technology choice that needs clarification.

    Attributes:
        domain: Technology domain (e.g., "data_fetching", "state_management")
        existing: Technology already in use (if any)
        alternatives: List of alternative technologies to choose from
        recommendation: Suggested approach ("extend_existing", "needs_decision")
    """
    domain: str
    existing: Optional[str]
    alternatives: List[str]
    recommendation: str


@dataclass
class TechChoices:
    """Collection of technology choices requiring clarification.

    Attributes:
        choices: List of technology choice decisions
    """
    choices: List[TechChoice]


@dataclass
class IntegrationPoint:
    """Detected external system integration point.

    Attributes:
        system: Name of external system (API, database, service)
        integration_type: Type of integration ("extend", "replace", "new")
        confidence: Confidence level of detection (0.0-1.0)
    """
    system: str
    integration_type: str  # "extend", "replace", "new"
    confidence: float


@dataclass
class UserAmbiguity:
    """Detected ambiguity about target users or personas.

    Attributes:
        possible_users: List of possible user types
        requires_permissions: Whether permission levels are needed
        confidence: Confidence level of detection (0.0-1.0)
    """
    possible_users: List[str]
    requires_permissions: bool
    confidence: float


@dataclass
class TradeoffNeed:
    """Detected need for trade-off decision.

    Attributes:
        tradeoff_type: Type of trade-off (performance, security, simplicity, etc.)
        options: Available options for the trade-off
        context: Additional context about why this trade-off matters
        confidence: Confidence level of detection (0.0-1.0)
    """
    tradeoff_type: str
    options: List[str]
    context: str
    confidence: float


@dataclass
class EdgeCase:
    """Detected unhandled edge case.

    Attributes:
        scenario: Description of edge case scenario
        category: Category of edge case (validation, error_handling, etc.)
        suggested_handling: Suggested approach to handle this case
        confidence: Confidence level of detection (0.0-1.0)
    """
    scenario: str
    category: str  # "validation", "error_handling", "timeout", "retry", etc.
    suggested_handling: str
    confidence: float


# Feature extension patterns - common features that users often forget to specify
FEATURE_EXTENSIONS = {
    "auth": ["password reset", "2FA", "OAuth", "session management", "account lockout", "remember me"],
    "authentication": ["password reset", "2FA", "OAuth", "session management", "account lockout"],
    "user": ["profile", "settings", "preferences", "avatar", "account deletion", "notifications"],
    "api": ["pagination", "filtering", "sorting", "caching", "rate limiting", "versioning"],
    "form": ["validation", "error handling", "auto-save", "draft support", "file upload"],
    "list": ["pagination", "search", "filtering", "sorting", "export", "bulk actions"],
    "upload": ["progress tracking", "resume capability", "validation", "preview", "max file size"],
    "payment": ["refunds", "receipts", "fraud detection", "payment methods", "currency support"],
    "notification": ["preferences", "delivery channels", "templates", "batching", "unsubscribe"],
    "search": ["filters", "sorting", "pagination", "autocomplete", "saved searches", "relevance"],
    "dashboard": ["widgets", "customization", "export", "refresh rate", "mobile view"],
    "report": ["scheduling", "export formats", "filters", "charts", "email delivery"],
    "admin": ["user management", "permissions", "audit logs", "bulk operations", "impersonation"],
}

# Technology alternatives by domain and stack
TECH_ALTERNATIVES = {
    "data_fetching": {
        "react": ["React Query", "SWR", "Apollo Client", "RTK Query", "fetch API"],
        "vue": ["Vue Query", "Pinia", "VueUse", "fetch API"],
        "python": ["requests", "httpx", "aiohttp"],
    },
    "state_management": {
        "react": ["Redux", "Zustand", "Jotai", "Recoil", "Context API", "MobX"],
        "vue": ["Pinia", "Vuex", "Composition API"],
        "python": ["dataclasses", "Pydantic"],
    },
    "form_handling": {
        "react": ["React Hook Form", "Formik", "React Final Form", "Zod + RHF", "native"],
        "vue": ["VeeValidate", "FormKit", "Vuelidate", "native"],
    },
    "auth": {
        "any": ["JWT", "Session-based", "OAuth 2.0", "Passkey/WebAuthn", "SAML"],
    },
    "database": {
        "any": ["PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis"],
        "python": ["SQLAlchemy", "Tortoise ORM", "Peewee", "raw SQL"],
    },
    "testing": {
        "react": ["Vitest", "Jest", "Testing Library", "Playwright", "Cypress"],
        "vue": ["Vitest", "Jest", "Vue Test Utils"],
        "python": ["pytest", "unittest", "pytest-asyncio"],
    },
    "styling": {
        "react": ["Tailwind CSS", "styled-components", "CSS Modules", "Emotion", "vanilla CSS"],
        "vue": ["Tailwind CSS", "Vuetify", "PrimeVue", "CSS Modules", "vanilla CSS"],
    },
}

# Keywords that suggest user/permission complexity
USER_KEYWORDS = ["user", "admin", "role", "permission", "access", "authorization", "owner", "member"]

# Keywords that suggest security/compliance requirements
SECURITY_KEYWORDS = [
    "authentication", "authorization", "auth", "security", "password", "token",
    "jwt", "oauth", "encryption", "crypto", "compliance", "gdpr", "hipaa", "pci"
]

# Keywords that suggest integration with external systems
INTEGRATION_KEYWORDS = [
    "api", "webhook", "integration", "third-party", "external", "service",
    "stripe", "paypal", "twilio", "sendgrid", "aws", "gcp", "azure"
]

# CRUD operations that commonly need error handling
CRUD_OPERATIONS = ["create", "read", "update", "delete", "save", "fetch", "load"]

# Network/IO operations that need timeout/retry handling
NETWORK_OPS = ["request", "fetch", "download", "upload", "api call", "http"]


def detect_scope_ambiguity(task_context: TaskContext) -> Optional[ScopeAmbiguity]:
    """
    Detect if task scope has ambiguous boundaries.

    Looks for:
    - Feature + common extensions not explicitly included/excluded
    - Vague scope words ("implement", "add" without specifics)
    - Missing acceptance criteria

    Args:
        task_context: Context information about the task

    Returns:
        ScopeAmbiguity if detected, None otherwise
    """
    # Check if task mentions a feature without clarifying extensions
    title_lower = task_context.title.lower()
    desc_lower = task_context.description.lower()
    combined_text = f"{title_lower} {desc_lower}"

    # Prioritize features found in the title over description
    # For multiple features in title, prefer the one appearing last (primary feature)
    detected_features = []

    for feature, extensions in FEATURE_EXTENSIONS.items():
        in_title = feature in title_lower
        in_desc = feature in desc_lower

        if in_title or in_desc:
            # Add to candidates with priority score
            # Priority factors:
            # 1. Title matches get higher base priority than description
            # 2. For title matches, position in title (later = more specific)
            # 3. Feature name length (longer = more specific)
            title_priority = 100 if in_title else 50
            position = title_lower.rfind(feature) if in_title else desc_lower.rfind(feature)
            specificity = len(feature)

            # Combine into a single priority score
            priority = title_priority + position + (specificity * 0.1)
            detected_features.append((feature, extensions, priority))

    # Sort by priority (higher priority first)
    detected_features.sort(key=lambda x: x[2], reverse=True)

    # Process the highest priority feature
    for feature, extensions, _ in detected_features:
        # Check which extensions are mentioned
        mentioned_extensions = [
            ext for ext in extensions
            if ext.lower() in combined_text
        ]

        # Find extensions not mentioned
        unmentioned = [
            ext for ext in extensions
            if ext not in mentioned_extensions
        ]

        # If there are common extensions not mentioned, there's scope ambiguity
        if unmentioned:
            # Higher confidence if no acceptance criteria or very short description
            confidence = 0.8
            if not task_context.acceptance_criteria:
                confidence = 0.9
            elif len(task_context.description) < 100:
                confidence = 0.85

            return ScopeAmbiguity(
                feature=feature,
                unmentioned_extensions=unmentioned[:4],  # Limit to top 4
                confidence=confidence
            )

    # Check for vague implementation words without specifics
    vague_patterns = [
        r'\b(implement|add|create)\s+\w+\s*$',  # Just "implement X" without details
        r'\b(basic|simple)\s+\w+',  # "basic auth" - how basic?
    ]

    for pattern in vague_patterns:
        if re.search(pattern, title_lower):
            if len(task_context.description) < 50:  # Very short description
                return ScopeAmbiguity(
                    feature="unspecified",
                    unmentioned_extensions=["detailed requirements", "edge cases", "error handling"],
                    confidence=0.7
                )

    return None


def detect_technology_choices(
    task_context: TaskContext,
    codebase_context: Optional[CodebaseContext] = None
) -> Optional[TechChoices]:
    """
    Detect if there are technology decisions to be made.

    Looks for:
    - Multiple libraries for same purpose in ecosystem
    - Existing patterns vs new approach
    - Stack-specific alternatives

    Args:
        task_context: Context information about the task
        codebase_context: Optional codebase context for pattern detection

    Returns:
        TechChoices if technology decisions detected, None otherwise
    """
    choices: List[TechChoice] = []

    title_lower = task_context.title.lower()
    desc_lower = task_context.description.lower()
    combined_text = f"{title_lower} {desc_lower}"

    # Determine stack from context or task tags
    stack = "any"
    if codebase_context:
        stack = codebase_context.detected_stack
    elif "react" in task_context.tags or "react" in combined_text:
        stack = "react"
    elif "vue" in task_context.tags or "vue" in combined_text:
        stack = "vue"
    elif "python" in task_context.tags or "python" in combined_text:
        stack = "python"

    # Check each technology domain
    for domain, stack_options in TECH_ALTERNATIVES.items():
        # Check if this domain is relevant to the task
        if _domain_mentioned_in_task(domain, combined_text):
            # Get alternatives for this stack
            alternatives = stack_options.get(stack, stack_options.get("any", []))

            if not alternatives:
                continue

            # Check if there's an existing technology in use
            existing = None
            if codebase_context and codebase_context.tech_inventory:
                domain_tech = codebase_context.tech_inventory.get(domain, [])
                if domain_tech:
                    existing = domain_tech[0]  # Use first found

            # Determine recommendation
            if existing:
                recommendation = "extend_existing"
            elif len(alternatives) > 1:
                recommendation = "needs_decision"
            else:
                recommendation = "use_default"

            if len(alternatives) > 1 or existing:
                choices.append(TechChoice(
                    domain=domain,
                    existing=existing,
                    alternatives=alternatives,
                    recommendation=recommendation
                ))

    return TechChoices(choices=choices) if choices else None


def detect_integration_points(
    task_context: TaskContext,
    codebase_context: Optional[CodebaseContext] = None
) -> List[IntegrationPoint]:
    """
    Detect external system connections.

    Looks for:
    - Import statements for external services
    - API client patterns in codebase
    - Configuration for external services

    Args:
        task_context: Context information about the task
        codebase_context: Optional codebase context

    Returns:
        List of detected integration points
    """
    integration_points: List[IntegrationPoint] = []

    title_lower = task_context.title.lower()
    desc_lower = task_context.description.lower()
    combined_text = f"{title_lower} {desc_lower}"

    # Check for integration keywords
    for keyword in INTEGRATION_KEYWORDS:
        if keyword in combined_text:
            # Determine integration type based on context
            integration_type = "new"
            confidence = 0.7

            if "extend" in combined_text or "add to" in combined_text:
                integration_type = "extend"
                confidence = 0.8
            elif "replace" in combined_text or "migrate" in combined_text:
                integration_type = "replace"
                confidence = 0.8

            # Check if this service exists in codebase
            if codebase_context and codebase_context.external_services:
                if any(keyword in service.lower() for service in codebase_context.external_services):
                    integration_type = "extend"
                    confidence = 0.9

            integration_points.append(IntegrationPoint(
                system=keyword,
                integration_type=integration_type,
                confidence=confidence
            ))

    # Look for specific service mentions
    services = [
        "stripe", "paypal", "twilio", "sendgrid", "mailchimp",
        "aws", "gcp", "azure", "firebase", "supabase",
        "auth0", "okta", "clerk"
    ]

    for service in services:
        if service in combined_text:
            integration_points.append(IntegrationPoint(
                system=service,
                integration_type="new",
                confidence=0.8
            ))

    return integration_points


def detect_user_ambiguity(task_context: TaskContext) -> Optional[UserAmbiguity]:
    """
    Detect ambiguity about target users or personas.

    Looks for:
    - Multiple user types mentioned
    - Permission/role keywords without specification
    - Features that typically need user segmentation

    Args:
        task_context: Context information about the task

    Returns:
        UserAmbiguity if detected, None otherwise
    """
    title_lower = task_context.title.lower()
    desc_lower = task_context.description.lower()
    combined_text = f"{title_lower} {desc_lower}"

    # Check for user-related keywords
    user_keyword_count = sum(1 for keyword in USER_KEYWORDS if keyword in combined_text)

    if user_keyword_count == 0:
        return None

    # Detect possible user types
    possible_users = []
    user_types = {
        "end user": ["user", "customer", "client"],
        "admin": ["admin", "administrator", "superuser"],
        "developer": ["developer", "api user", "integration"],
        "moderator": ["moderator", "manager", "supervisor"],
    }

    for user_type, keywords in user_types.items():
        if any(keyword in combined_text for keyword in keywords):
            possible_users.append(user_type)

    # Check if permissions are needed
    requires_permissions = any(
        keyword in combined_text
        for keyword in ["permission", "role", "access", "authorization", "rbac"]
    )

    # Higher confidence if multiple user types or permission keywords
    confidence = 0.6
    if len(possible_users) > 1:
        confidence = 0.8
    if requires_permissions:
        confidence = min(0.9, confidence + 0.2)

    if possible_users or requires_permissions:
        return UserAmbiguity(
            possible_users=possible_users if possible_users else ["user"],
            requires_permissions=requires_permissions,
            confidence=confidence
        )

    return None


def detect_tradeoff_needs(task_context: TaskContext) -> List[TradeoffNeed]:
    """
    Detect need for trade-off decisions.

    Looks for:
    - Performance vs maintainability decisions
    - Security vs usability decisions
    - Complexity score indicating difficult choices

    Args:
        task_context: Context information about the task

    Returns:
        List of detected trade-off needs
    """
    tradeoffs: List[TradeoffNeed] = []

    title_lower = task_context.title.lower()
    desc_lower = task_context.description.lower()
    combined_text = f"{title_lower} {desc_lower}"

    # Performance trade-offs
    if any(keyword in combined_text for keyword in ["performance", "speed", "fast", "optimize", "cache"]):
        tradeoffs.append(TradeoffNeed(
            tradeoff_type="performance",
            options=["Optimize for speed", "Optimize for maintainability", "Balanced approach"],
            context="Performance optimization may introduce complexity",
            confidence=0.7
        ))

    # Security trade-offs
    if any(keyword in combined_text for keyword in SECURITY_KEYWORDS):
        tradeoffs.append(TradeoffNeed(
            tradeoff_type="security",
            options=["Maximum security", "Balanced security/UX", "Focus on UX"],
            context="Security measures may impact user experience",
            confidence=0.8
        ))

    # Complexity-based trade-offs
    if task_context.complexity >= 5:
        tradeoffs.append(TradeoffNeed(
            tradeoff_type="implementation_approach",
            options=["Simple/pragmatic", "Comprehensive/robust", "Iterative approach"],
            context=f"Task complexity ({task_context.complexity}/10) suggests multiple valid approaches",
            confidence=0.7
        ))

    # Error handling trade-offs
    if any(keyword in combined_text for keyword in ["error", "failure", "exception", "retry"]):
        tradeoffs.append(TradeoffNeed(
            tradeoff_type="error_handling",
            options=["Fail fast", "Graceful degradation", "Retry with backoff", "Let caller handle"],
            context="Error handling strategy affects reliability and UX",
            confidence=0.75
        ))

    return tradeoffs


def detect_unhandled_edge_cases(task_context: TaskContext) -> List[EdgeCase]:
    """
    Detect obvious edge cases not addressed in task description.

    Looks for:
    - CRUD operations without error handling mentioned
    - Network/IO operations without timeout/retry
    - User input without validation

    Args:
        task_context: Context information about the task

    Returns:
        List of detected unhandled edge cases
    """
    edge_cases: List[EdgeCase] = []

    title_lower = task_context.title.lower()
    desc_lower = task_context.description.lower()
    combined_text = f"{title_lower} {desc_lower}"

    # Check for CRUD operations without error handling
    has_crud = any(op in combined_text for op in CRUD_OPERATIONS)
    has_error_handling = any(
        keyword in combined_text
        for keyword in ["error", "exception", "failure", "handle", "catch"]
    )

    if has_crud and not has_error_handling:
        edge_cases.append(EdgeCase(
            scenario="What should happen when the operation fails?",
            category="error_handling",
            suggested_handling="Define error handling strategy (retry, fallback, user notification)",
            confidence=0.8
        ))

    # Check for network operations without timeout/retry
    has_network = any(op in combined_text for op in NETWORK_OPS)
    has_timeout = any(keyword in combined_text for keyword in ["timeout", "retry", "backoff"])

    if has_network and not has_timeout:
        edge_cases.append(EdgeCase(
            scenario="What should happen when network request times out or fails?",
            category="timeout_retry",
            suggested_handling="Define timeout duration and retry strategy",
            confidence=0.75
        ))

    # Check for input/form without validation
    has_input = any(keyword in combined_text for keyword in ["input", "form", "field", "data entry"])
    has_validation = any(keyword in combined_text for keyword in ["validation", "validate", "sanitize"])

    if has_input and not has_validation:
        edge_cases.append(EdgeCase(
            scenario="How should invalid user input be handled?",
            category="validation",
            suggested_handling="Define validation rules and error messages",
            confidence=0.7
        ))

    # Check for data operations without empty state handling
    has_list_display = any(keyword in combined_text for keyword in ["list", "table", "grid", "display"])
    has_empty_state = any(keyword in combined_text for keyword in ["empty", "no data", "no results"])

    if has_list_display and not has_empty_state:
        edge_cases.append(EdgeCase(
            scenario="What should be displayed when the list is empty?",
            category="empty_state",
            suggested_handling="Define empty state message and possible actions",
            confidence=0.65
        ))

    # Check for authentication without account recovery
    if "auth" in combined_text and "password" in combined_text:
        has_recovery = any(
            keyword in combined_text
            for keyword in ["reset", "recovery", "forgot password"]
        )
        if not has_recovery:
            edge_cases.append(EdgeCase(
                scenario="How do users recover access if they forget credentials?",
                category="account_recovery",
                suggested_handling="Include password reset/recovery mechanism",
                confidence=0.8
            ))

    return edge_cases


def _domain_mentioned_in_task(domain: str, text: str) -> bool:
    """
    Check if a technology domain is mentioned in task text.

    Args:
        domain: Technology domain (e.g., "data_fetching")
        text: Combined task text (title + description)

    Returns:
        True if domain is mentioned, False otherwise
    """
    domain_keywords = {
        "data_fetching": ["fetch", "api", "request", "http", "data", "query"],
        "state_management": ["state", "store", "context", "global", "shared"],
        "form_handling": ["form", "input", "validation", "submit"],
        "auth": ["auth", "login", "signup", "authentication", "session"],
        "database": ["database", "db", "sql", "query", "model", "schema"],
        "testing": ["test", "testing", "spec", "unit test", "integration test"],
        "styling": ["style", "css", "theme", "design", "ui"],
    }

    keywords = domain_keywords.get(domain, [])
    return any(keyword in text for keyword in keywords)
