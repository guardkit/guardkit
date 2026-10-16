"""ETag generation utilities and middleware for HTTP response caching.

Provides deterministic ETag generation based on resource content using
SHA-256 hashing, and an ASGI middleware for validating client ETags
against current resource state per RFC 9110.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING, Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

ETAG_PREFIX = '"'
ETAG_SUFFIX = '"'
HASH_ALGORITHM = "sha256"


def generate_etag(data: Any) -> str:
    """Generate a strong ETag from resource data.

    Serializes the data to a canonical JSON representation, hashes it
    with SHA-256, and wraps the hex digest in double quotes to produce
    a strong ETag per RFC 9110.

    Args:
        data: The resource data to hash. Can be any JSON-serializable
            type (dict, list, str, int, float, bool, None).

    Returns:
        A strong ETag string, e.g. ``"<sha256-hex-digest>"``.

    Raises:
        TypeError: If the data is not JSON-serializable.
    """
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{ETAG_PREFIX}{digest}{ETAG_SUFFIX}"


def etag_matches(etag: str | None, resource_data: Any) -> bool:
    """Check whether a provided ETag matches the current resource state.

    Compares the incoming ETag against the ETag generated from the
    current resource data. Returns True if they match, indicating the
    client's cached copy is still valid.

    Args:
        etag: The ETag sent by the client, or None if absent.
        resource_data: The current resource data to generate a fresh ETag.

    Returns:
        True if the ETags match, False otherwise.
    """
    if etag is None:
        return False
    current_etag = generate_etag(resource_data)
    return etag == current_etag


class ETagMiddleware:
    """ASGI middleware that validates client ETags via If-None-Match header.

    For GET requests carrying an ``If-None-Match`` header, this middleware
    generates an ETag from the response body and compares it against the
    client-supplied value.  When the ETags match a **304 Not Modified**
    response is returned; otherwise the full response is returned with an
    ``ETag`` header attached.

    Malformed ``If-None-Match`` headers are handled gracefully by returning
    the full resource without 304.

    This middleware is intended to be reusable across any endpoint that
    returns JSON-serializable response content.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the ETag middleware.

        Args:
            app: The ASGI application to wrap.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle an ASGI request with ETag validation.

        Args:
            scope: The ASGI scope dictionary.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != "http" or scope["method"] != "GET":
            await self.app(scope, receive, send)
            return

        # Read If-None-Match header
        headers = dict(scope.get("headers", []))
        if_none_match = headers.get(b"if-none-match")

        # Intercept the response to capture body and headers
        # Use local variables (not instance variables) to support concurrent requests
        response_status: int = 0
        response_headers: list[tuple[bytes, bytes]] = []
        response_body_chunks: list[bytes] = []

        async def capture_send(message: Message) -> None:
            """Capture response messages for ETag comparison."""
            if message["type"] == "http.response.start":
                nonlocal response_status, response_headers
                response_status = message.get("status", 200)
                response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                nonlocal response_body_chunks
                body_chunk = message.get("body", b"")
                response_body_chunks.append(body_chunk)
                # If this is the last chunk, process ETag
                if not message.get("more_body", False):
                    await self._handle_etag(
                        scope,
                        receive,
                        send,
                        if_none_match,
                        response_status,
                        response_headers,
                        response_body_chunks,
                    )

        await self.app(scope, receive, capture_send)

    async def _handle_etag(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        if_none_match: bytes | None,
        response_status: int,
        response_headers: list[tuple[bytes, bytes]],
        response_body_chunks: list[bytes],
    ) -> None:
        """Process the captured response for ETag validation.

        Args:
            scope: The ASGI scope dictionary.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
            if_none_match: The If-None-Match header value from the request.
            response_status: The HTTP status code from the response.
            response_headers: The response headers.
            response_body_chunks: The response body chunks.
        """
        # Combine all body chunks
        body_bytes = b"".join(response_body_chunks)

        # Try to parse body as JSON for ETag generation
        resource_data: Any = None
        if body_bytes:
            try:
                resource_data = json.loads(body_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                resource_data = body_bytes.decode("utf-8", errors="replace")

        if resource_data is None:
            # No body to generate ETag from; pass through original response
            await self._send_response(
                send, response_status, response_headers, body_bytes
            )
            return

        # Generate current ETag
        current_etag = generate_etag(resource_data)

        if if_none_match is None:
            # No If-None-Match header; return full response with ETag
            modified_headers = list(response_headers)
            modified_headers.append((b"etag", current_etag.encode("utf-8")))
            await self._send_response(
                send, response_status, modified_headers, body_bytes
            )
            return

        # Parse If-None-Match header
        # Format can be: "*" or a list of ETags like '"etag1", "etag2"'
        try:
            if_none_match_str = if_none_match.decode("utf-8").strip()
            if if_none_match_str == "*":
                match = True
            else:
                # Parse comma-separated list of ETags
                client_etags = [etag.strip() for etag in if_none_match_str.split(",")]
                match = current_etag in client_etags
        except Exception:
            # Malformed If-None-Match; return full resource gracefully
            logger.warning(
                "Malformed If-None-Match header, returning full resource",
                header=if_none_match,
            )
            modified_headers = list(response_headers)
            modified_headers.append((b"etag", current_etag.encode("utf-8")))
            await self._send_response(
                send, response_status, modified_headers, body_bytes
            )
            return

        if match:
            # Return 304 Not Modified
            content_length_key = b"content-length"
            modified_headers = [
                (k, v) for k, v in response_headers if k.lower() != content_length_key
            ]
            modified_headers.append((b"etag", current_etag.encode("utf-8")))
            await send(
                {
                    "type": "http.response.start",
                    "status": 304,
                    "headers": modified_headers,
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"",
                }
            )
        else:
            # No match; return full response with ETag header
            modified_headers = list(response_headers)
            modified_headers.append((b"etag", current_etag.encode("utf-8")))
            await self._send_response(
                send, response_status, modified_headers, body_bytes
            )

    async def _send_response(
        self,
        send: Send,
        status: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        """Send the response through the ASGI send callable.

        Args:
            send: The ASGI send callable.
            status: The HTTP status code.
            headers: The response headers.
            body: The response body.
        """
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
