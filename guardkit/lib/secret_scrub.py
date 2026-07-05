"""Secret scrubbing at the evidence→publication boundary (TASK-AB-SECRETSCRUB01).

ABL-001 run 3 (2026-07-04): a failing assertion printed the live NAS store DSN
from the loop's ambient environment, and that output travelled the standard
publication path — pytest output → Coach evidence JSON (gitignored) → task-md
frontmatter turn history (TRACKED) → chore commit → public GitHub. The retro
invariant this module implements: *turn-tracking is a publication path — treat
evidence-file content as publish-equivalent.*

The boundary is PUBLICATION, never verification: the Coach must see real,
unscrubbed output (the oracle verdicts on raw evidence in the gitignored
``.guardkit/autobuild/`` dirs). Scrubbing applies only in orchestrator writers
that produce TRACKED or operator-copyable artifacts:

- the task-md frontmatter turn-history writer
  (``AutoBuildOrchestrator._serialize_turn_history``), and
- the review-summary writer (``ReviewSummaryGenerator.generate``).

Relationship to ``guardkit.orchestrator.instrumentation.redaction``: that
module redacts instrumentation *events* with blanket ``[REDACTED]`` semantics
(both user and password masked, no localhost exemption) and is pinned by its
own tests. This module is the publication-boundary sibling with different,
AC-driven semantics: user preserved, localhost fixture DSNs preserved,
deterministic shaped masks. Both keep their own scope; do not merge them
without revisiting both contracts.

Determinism: the same input always produces the same scrubbed output (fixed
masks, pure regex), so repeated writes and honesty comparisons stay stable.

Known residual channel: text truncated UPSTREAM of a publication writer
(e.g. a ``[:500]`` applied while composing feedback) can cut a DSN before
its ``@host`` anchor, leaving a shape the regexes cannot match. The primary
defence for that channel is operational (never run agent loops with live
credentials in the ambient environment — see TASK-AB-HERMETICTEST01 and the
instrumentation guide), with this scrubber as the publication backstop.
Note also that a RESUMED task deserialises the scrubbed turn history, so the
Player sees masked values in prior feedback on resume — acceptable: prior
feedback should never need a live credential.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

__all__ = [
    "SecretMatch",
    "REDACTION_FAILURE_MARKER",
    "find_secret_matches",
    "iter_hazards",
    "scrub_secrets",
    "scrub_for_publication",
]


# Written in place of an embedded content block when scrubbing itself fails.
# Fail-closed: never write the unscrubbed content, never crash the loop.
REDACTION_FAILURE_MARKER = (
    "[REDACTED: secret scrubbing failed; embedded content withheld from"
    " publication]"
)

_MASK = "***"

# Hosts whose URL credentials are the documented, legitimate fixture-DSN
# pattern (AC-001: localhost credentials MAY be preserved).
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})

# Placeholder credentials/hosts used in documentation examples. These are
# NOT exempt from scrubbing (over-masking published output is safe), but the
# repo lint treats them as benign so docs examples don't fail CI.
_PLACEHOLDER_PASSWORDS = frozenset(
    {
        "pass",
        "password",
        "passwd",
        "pwd",
        "secret",
        "changeme",
        "example",
        "redacted",
        "mypassword",
        "yourpassword",
        "xxx",
    }
)
_PLACEHOLDER_HOSTS = frozenset(
    {"host", "hostname", "host:port", "example.com", "example.org", "db", "server"}
)

# Substrings that mark a credential value as a documentation placeholder
# (``sk-your-key-here``, ``Bearer YOUR_TOKEN``, ``sk-1234567890``,
# AWS's ``AKIAIOSFODNN7EXAMPLE``). Checked case-insensitively.
_PLACEHOLDER_MARKERS = (
    "your",
    "example",
    "placeholder",
    "mock",
    "dummy",
    "changeme",
    "1234567890",
    "xxx",
)


def _looks_placeholder(value: str) -> bool:
    """True when ``value`` is a documentation placeholder, not a secret.

    Template interpolation (``{password}``, ``$PASSWORD``, ``<password>``,
    ``***``) and the well-known placeholder markers all qualify.
    """
    if any(ch in value for ch in "{$<*"):
        return True
    lowered = value.lower()
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)

# URL userinfo credentials: scheme://user:pass@host → scheme://user:***@host.
# The user/password classes exclude ``/``, ``?`` and ``#`` (RFC 3986 userinfo
# must percent-encode those), so a credential-free URL whose PATH or QUERY
# contains an ``@`` (e.g. ``…/notify?email=a@b.com``) can never be misparsed
# as userinfo and rewritten. Known accepted gap: a doubled userinfo like
# ``u:p@localhost@evil.host`` parses its first ``@`` as the boundary and the
# localhost exemption then applies — adversarially-formatted output can
# always print a bare password anyway; the scrubber targets the accidental
# leak shape, not a hostile Player.
_URL_CREDENTIAL_RE = re.compile(
    r"(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*)://"
    r"(?P<user>[^/@:?#\s]+):(?P<password>[^@/?#\s]+)@"
    r"(?P<host>\[[^\]]+\]|[^/@:?#\s]+)"
)

# Common token shapes. Masks preserve the (non-secret) recognisable prefix so
# published output stays readable and deterministic.
_AWS_KEY_RE = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{12,}\b")
_SK_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}\b")
_GITHUB_TOKEN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{10,}|github_pat_[A-Za-z0-9_]{10,})\b"
)
_BEARER_RE = re.compile(r"\b(?i:bearer)\s+[A-Za-z0-9._\-]{10,}\b")


@dataclass(frozen=True)
class SecretMatch:
    """A secret-shaped span found in text.

    ``safe_label`` is printable everywhere (lint failure messages, CI logs)
    and MUST never contain secret material — a CI log is also a publication
    path.
    """

    kind: str
    start: int
    end: int
    replacement: str
    safe_label: str
    # True when the credential looks like a documentation placeholder
    # (password/host drawn from the well-known placeholder sets). The
    # scrubber still masks these; the repo lint skips them.
    placeholder: bool = False


def _normalise_host(host: str) -> str:
    return host.strip("[]").lower()


def _url_credential_matches(text: str) -> Iterator[SecretMatch]:
    for match in _URL_CREDENTIAL_RE.finditer(text):
        host = match.group("host")
        if _normalise_host(host) in _LOCAL_HOSTS:
            continue  # documented, legitimate fixture-DSN pattern
        password = match.group("password")
        placeholder = (
            password.lower() in _PLACEHOLDER_PASSWORDS
            or _looks_placeholder(password)
            or _looks_placeholder(match.group("user"))
            or _looks_placeholder(host)
            or _normalise_host(host) in _PLACEHOLDER_HOSTS
        )
        replacement = (
            f"{match.group('scheme')}://{match.group('user')}:{_MASK}@{host}"
        )
        yield SecretMatch(
            kind="url-credential",
            start=match.start(),
            end=match.end(),
            replacement=replacement,
            safe_label=f"url-credential host={host}",
            placeholder=placeholder,
        )


def _token_matches(text: str) -> Iterator[SecretMatch]:
    for match in _AWS_KEY_RE.finditer(text):
        prefix = match.group(0)[:4]
        yield SecretMatch(
            kind="aws-access-key-id",
            start=match.start(),
            end=match.end(),
            replacement=f"{prefix}{_MASK}",
            safe_label=f"aws-access-key-id prefix={prefix}",
            placeholder=_looks_placeholder(match.group(0)),
        )
    for match in _SK_KEY_RE.finditer(text):
        yield SecretMatch(
            kind="api-key",
            start=match.start(),
            end=match.end(),
            replacement=f"sk-{_MASK}",
            safe_label="api-key prefix=sk-",
            placeholder=_looks_placeholder(match.group(0)),
        )
    for match in _GITHUB_TOKEN_RE.finditer(text):
        prefix = match.group(0).split("_", 1)[0] + "_"
        if match.group(0).startswith("github_pat_"):
            prefix = "github_pat_"
        yield SecretMatch(
            kind="github-token",
            start=match.start(),
            end=match.end(),
            replacement=f"{prefix}{_MASK}",
            safe_label=f"github-token prefix={prefix}",
            placeholder=_looks_placeholder(match.group(0)),
        )
    for match in _BEARER_RE.finditer(text):
        bearer_word, token = match.group(0).split(None, 1)
        yield SecretMatch(
            kind="bearer-token",
            start=match.start(),
            end=match.end(),
            replacement=f"{bearer_word} {_MASK}",
            safe_label="bearer-token",
            # Prose like "bearer responsibility" is a pure-alphabetic
            # "token": still masked at publication (over-masking is safe)
            # but not lint-failing. Real tokens carry digits/./_/-.
            placeholder=token.isalpha() or _looks_placeholder(token),
        )


def find_secret_matches(text: str) -> List[SecretMatch]:
    """Find all secret-shaped spans in ``text``, sorted, non-overlapping.

    Localhost URL credentials are never reported (fixture DSNs are the
    documented, legitimate pattern). When spans overlap (e.g. an ``sk-`` token
    used as a URL password), the earlier/longer match wins.
    """
    if not text:
        return []
    candidates = sorted(
        list(_url_credential_matches(text)) + list(_token_matches(text)),
        key=lambda m: (m.start, -(m.end - m.start)),
    )
    selected: List[SecretMatch] = []
    last_end = -1
    for candidate in candidates:
        if candidate.start < last_end:
            continue
        selected.append(candidate)
        last_end = candidate.end
    return selected


def iter_hazards(text: str) -> Iterator[Tuple[int, SecretMatch]]:
    """Yield ``(line_number, match)`` for lint-grade hazards in ``text``.

    Placeholder-shaped credentials (documentation examples) are skipped —
    this is the filter the tracked-artifact repo lint applies on top of
    :func:`find_secret_matches`.
    """
    for match in find_secret_matches(text):
        if match.placeholder:
            continue
        lineno = text.count("\n", 0, match.start) + 1
        yield lineno, match


def scrub_secrets(text: str) -> str:
    """Deterministically mask secret-shaped substrings in ``text``.

    URL userinfo credentials become ``scheme://user:***@host`` (localhost
    preserved); token shapes keep their recognisable prefix with the secret
    body masked. Same input → same output.
    """
    if not text:
        return text
    matches = find_secret_matches(text)
    if not matches:
        return text
    parts: List[str] = []
    cursor = 0
    for match in matches:
        parts.append(text[cursor : match.start])
        parts.append(match.replacement)
        cursor = match.end
    parts.append(text[cursor:])
    return "".join(parts)


def scrub_for_publication(value: Optional[str]) -> Optional[str]:
    """Fail-closed scrub for content crossing the publication boundary.

    ``None`` stays ``None`` (absence must survive — never turn an absent
    field into a present one, or vice versa). Non-string values pass through
    untouched. If scrubbing raises, the whole block is replaced with
    :data:`REDACTION_FAILURE_MARKER` and a WARNING is logged — never the
    unscrubbed content, never a crash.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    try:
        return scrub_secrets(value)
    except Exception:
        logger.warning(
            "TASK-AB-SECRETSCRUB01: secret scrubbing failed; withholding the"
            " embedded content block from publication",
            exc_info=True,
        )
        return REDACTION_FAILURE_MARKER
