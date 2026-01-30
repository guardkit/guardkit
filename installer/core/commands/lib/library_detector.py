#!/usr/bin/env python3
"""Library detection module for identifying external library/package mentions in task text.

This module provides functions to detect library and package names mentioned in task
titles and descriptions. It helps identify which external APIs may require documentation
lookup during task implementation.

Key Features:
    - Fast O(1) lookup against known library registry
    - Pattern-based detection for usage phrases (e.g., "using X", "with Y")
    - False positive filtering to exclude common English words
    - Normalized output for consistent API queries

Module Design:
    - No external dependencies beyond standard library (re, typing)
    - Pre-compiled regex patterns for performance (<50ms)
    - Case-insensitive matching with normalized output
    - Extensible registry for adding new libraries

Extension Points:
    - KNOWN_LIBRARIES: Add new library names to the registry set
    - USAGE_PATTERNS: Add new regex patterns for detection
    - EXCLUDE_WORDS: Add common words that cause false positives

Example:
    >>> from installer.core.commands.lib.library_detector import detect_library_mentions
    >>> detect_library_mentions("Implement search with graphiti-core", "")
    ['graphiti-core']
    >>> detect_library_mentions("Use FastAPI with Pydantic validation", "")
    ['fastapi', 'pydantic']

Part of: Library Knowledge Gap Detection System
Author: Claude (Anthropic)
Created: 2026-01-30
"""

import re
from typing import List, Set

# Known library registry for O(1) lookup
# Organized by category for maintainability
KNOWN_LIBRARIES: Set[str] = {
    # Python - Web Frameworks
    "fastapi", "flask", "django", "starlette", "litestar", "sanic",

    # Python - Data/Validation
    "pydantic", "pandas", "numpy", "scipy", "polars", "dask",

    # Python - Async/HTTP
    "requests", "httpx", "aiohttp", "urllib3", "httpcore",

    # Python - Testing
    "pytest", "unittest", "hypothesis", "coverage", "tox", "nox",

    # Python - ORM/Database
    "sqlalchemy", "alembic", "tortoise-orm", "peewee", "sqlmodel",

    # Python - Task Queues
    "celery", "rq", "dramatiq", "huey", "arq",

    # Python - Caching
    "redis", "memcached", "aiocache", "cachetools",

    # Python - AI/ML
    "langchain", "langsmith", "langgraph", "openai", "anthropic",
    "transformers", "torch", "pytorch", "tensorflow", "keras",
    "scikit-learn", "sklearn", "xgboost", "lightgbm",

    # Python - Graph/Knowledge
    "graphiti-core", "graphiti", "neo4j", "networkx", "igraph",

    # JavaScript/TypeScript - Frameworks
    "react", "next.js", "nextjs", "vue", "nuxt", "angular", "svelte",
    "solid-js", "solidjs", "qwik", "astro", "remix",

    # JavaScript/TypeScript - Backend
    "express", "fastify", "koa", "hono", "elysia", "nest.js", "nestjs",

    # JavaScript/TypeScript - ORM/Database
    "prisma", "typeorm", "drizzle", "sequelize", "knex", "mongoose",

    # JavaScript/TypeScript - Validation
    "zod", "yup", "joi", "superstruct", "valibot",

    # JavaScript/TypeScript - Testing
    "jest", "vitest", "mocha", "cypress", "playwright", "puppeteer",

    # JavaScript/TypeScript - State/Data
    "redux", "zustand", "jotai", "recoil", "mobx", "tanstack-query",
    "react-query", "swr", "axios", "lodash", "ramda",

    # JavaScript/TypeScript - UI
    "tailwind", "tailwindcss", "chakra-ui", "chakra", "material-ui",
    "mui", "shadcn", "radix", "headless-ui", "ant-design", "antd",

    # JavaScript/TypeScript - Build
    "webpack", "vite", "esbuild", "rollup", "parcel", "turbopack",

    # Auth/Security
    "pyjwt", "jwt", "jose", "oauth", "passlib", "bcrypt", "argon2",
    "auth0", "clerk", "nextauth", "lucia", "supertokens",

    # Databases
    "postgres", "postgresql", "mongodb", "mysql", "sqlite", "mariadb",
    "cockroachdb", "planetscale", "supabase", "firebase", "dynamodb",

    # Cloud/Infrastructure
    "boto3", "aws-sdk", "azure", "gcp", "docker", "kubernetes", "k8s",
    "terraform", "pulumi", "cloudflare", "vercel", "netlify",

    # Messaging/Events
    "kafka", "rabbitmq", "nats", "zeromq", "mqtt", "socketio",

    # Monitoring/Logging
    "sentry", "datadog", "prometheus", "grafana", "opentelemetry",
    "structlog", "loguru", "pino", "winston",
}

# Compiled regex patterns for usage phrase detection
# Each pattern captures the library name as group 1
USAGE_PATTERNS: List[re.Pattern] = [
    re.compile(r'\busing\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bwith\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bvia\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bintegrate\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bintegrating\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bimplement\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bimplementing\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\badd\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\badding\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\buse\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bconnect\s+to\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bconnecting\s+to\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bmigrate\s+to\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bswitch\s+to\s+([a-z][\w.-]*)', re.IGNORECASE),
    re.compile(r'\bupgrade\s+to\s+([a-z][\w.-]*)', re.IGNORECASE),
]

# Words to exclude from detection (common English words, generic terms)
EXCLUDE_WORDS: Set[str] = {
    # Articles and conjunctions
    "the", "a", "an", "and", "or", "but", "nor", "yet", "so",

    # Prepositions
    "with", "for", "to", "in", "on", "at", "by", "from", "of",
    "into", "onto", "upon", "about", "through", "during", "before",
    "after", "above", "below", "between", "under", "over",

    # Pronouns and demonstratives
    "this", "that", "these", "those", "it", "its", "they", "them",
    "we", "us", "our", "you", "your", "i", "my", "me",

    # Common verbs (base forms)
    "add", "adding", "create", "creating", "delete", "deleting",
    "update", "updating", "fix", "fixing", "implement", "implementing",
    "build", "building", "make", "making", "get", "getting",
    "set", "setting", "run", "running", "test", "testing",
    "check", "checking", "validate", "validating", "verify", "verifying",
    "use", "using", "call", "calling", "handle", "handling",
    "process", "processing", "change", "changing", "move", "moving",
    "remove", "removing", "integrate", "integrating",

    # Generic tech terms
    "tests", "test", "testing", "code", "file", "files", "function",
    "functions", "method", "methods", "class", "classes", "module",
    "modules", "feature", "features", "bug", "bugs", "issue", "issues",
    "api", "apis", "endpoint", "endpoints", "service", "services",
    "component", "components", "system", "systems", "data", "database",
    "user", "users", "app", "application", "applications",
    "error", "errors", "exception", "exceptions", "response", "responses",
    "request", "requests", "query", "queries", "result", "results",
    "config", "configuration", "settings", "options", "parameters",
    "input", "inputs", "output", "outputs", "value", "values",
    "type", "types", "interface", "interfaces", "schema", "schemas",
    "model", "models", "entity", "entities", "object", "objects",
    "array", "arrays", "list", "lists", "dict", "dictionary",
    "string", "strings", "number", "numbers", "boolean", "booleans",
    "null", "none", "true", "false", "yes", "no",

    # Adjectives and modifiers
    "new", "old", "current", "previous", "next", "first", "last",
    "all", "some", "any", "many", "few", "more", "less", "most",
    "other", "another", "same", "different", "similar", "related",
    "main", "primary", "secondary", "default", "custom", "basic",
    "simple", "complex", "existing", "missing", "broken", "working",

    # Time-related
    "now", "then", "when", "while", "before", "after", "during",

    # State and status
    "status", "state", "pending", "active", "inactive", "enabled",
    "disabled", "valid", "invalid", "success", "failure", "failed",

    # Actions results
    "done", "complete", "completed", "incomplete", "finished", "started",

    # Project terms
    "task", "tasks", "project", "projects", "repo", "repository",
    "branch", "branches", "commit", "commits", "pr", "pull",
    "merge", "merged", "review", "reviewed", "deploy", "deployed",
}


def _normalize_library_name(name: str) -> str:
    """Normalize library name for consistent comparison.

    Applies transformations to ensure library names match registry format:
    - Strips whitespace
    - Converts to lowercase
    - Replaces underscores with hyphens

    Args:
        name: Raw library name from text

    Returns:
        Normalized library name

    Examples:
        >>> _normalize_library_name("FastAPI")
        'fastapi'
        >>> _normalize_library_name("graphiti_core")
        'graphiti-core'
    """
    return name.strip().lower().replace("_", "-")


def _tokenize_text(text: str) -> List[str]:
    """Tokenize text into potential library name tokens.

    Extracts word-like tokens that could be library names, preserving
    hyphens and dots which are common in package names.

    Args:
        text: Input text to tokenize

    Returns:
        List of potential library name tokens

    Examples:
        >>> _tokenize_text("Use graphiti-core for search")
        ['use', 'graphiti-core', 'for', 'search']
    """
    # Match word characters, hyphens, and dots (common in package names)
    pattern = r'[a-zA-Z][a-zA-Z0-9._-]*'
    tokens = re.findall(pattern, text)
    return [t.lower() for t in tokens]


def _is_valid_library_candidate(name: str) -> bool:
    """Check if a name is a valid library candidate.

    Filters out tokens that are too short or are excluded words.

    Args:
        name: Normalized library name to validate

    Returns:
        True if name could be a library, False otherwise
    """
    # Must be at least 3 characters
    if len(name) < 3:
        return False

    # Must not be in exclusion list
    if name in EXCLUDE_WORDS:
        return False

    return True


def detect_library_mentions(title: str, description: str) -> List[str]:
    """Detect library/package names that will require API knowledge.

    Scans task title and description for mentions of external libraries
    or packages. Uses two detection strategies:

    1. Direct lookup: Tokenizes text and checks each token against
       the KNOWN_LIBRARIES registry (O(1) per token).

    2. Pattern-based: Applies USAGE_PATTERNS regex to find libraries
       mentioned in context phrases like "using X" or "with Y".

    Results are deduplicated, filtered for false positives, and returned
    in sorted order for consistent output.

    Args:
        title: Task title text
        description: Task description text

    Returns:
        List of detected library names (lowercase, normalized, sorted).
        Empty list if no libraries detected.

    Examples:
        >>> detect_library_mentions("Implement search with graphiti-core", "")
        ['graphiti-core']

        >>> detect_library_mentions("Add caching using Redis", "")
        ['redis']

        >>> detect_library_mentions("Build auth with PyJWT", "")
        ['pyjwt']

        >>> detect_library_mentions("Use FastAPI with Pydantic validation", "")
        ['fastapi', 'pydantic']

        >>> detect_library_mentions("Fix the login bug", "")
        []

        >>> detect_library_mentions("Using REDIS for caching", "")
        ['redis']
    """
    # Combine title and description
    combined_text = f"{title} {description}".strip()

    if not combined_text:
        return []

    detected: Set[str] = set()

    # Strategy 1: Direct lookup via tokenization
    tokens = _tokenize_text(combined_text)
    for token in tokens:
        normalized = _normalize_library_name(token)
        if normalized in KNOWN_LIBRARIES:
            detected.add(normalized)

    # Strategy 2: Pattern-based detection
    for pattern in USAGE_PATTERNS:
        matches = pattern.findall(combined_text)
        for match in matches:
            normalized = _normalize_library_name(match)
            # Only add if it's a known library (avoids false positives)
            if normalized in KNOWN_LIBRARIES:
                detected.add(normalized)
            # Also check without trailing version-like suffixes
            # e.g., "redis-5" -> "redis"
            base_name = re.sub(r'-\d+(\.\d+)*$', '', normalized)
            if base_name in KNOWN_LIBRARIES:
                detected.add(base_name)

    # Filter out false positives and sort
    result = [
        lib for lib in detected
        if _is_valid_library_candidate(lib)
    ]

    return sorted(result)


def get_library_registry() -> Set[str]:
    """Get a copy of the known library registry.

    Returns a copy to prevent external modification of the registry.

    Returns:
        Set of known library names

    Example:
        >>> len(get_library_registry()) > 100
        True
    """
    return KNOWN_LIBRARIES.copy()


def add_library_to_registry(library_name: str) -> bool:
    """Add a library to the known library registry.

    Allows runtime extension of the library registry for project-specific
    libraries not included in the default set.

    Args:
        library_name: Library name to add (will be normalized)

    Returns:
        True if library was added, False if already existed

    Example:
        >>> add_library_to_registry("my-custom-lib")
        True
        >>> add_library_to_registry("my-custom-lib")
        False
    """
    normalized = _normalize_library_name(library_name)
    if normalized in KNOWN_LIBRARIES:
        return False
    KNOWN_LIBRARIES.add(normalized)
    return True


# Public API
__all__ = [
    # Core detection function
    "detect_library_mentions",

    # Registry management
    "get_library_registry",
    "add_library_to_registry",

    # Constants (for extension)
    "KNOWN_LIBRARIES",
    "USAGE_PATTERNS",
    "EXCLUDE_WORDS",
]
