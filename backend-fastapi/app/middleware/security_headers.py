"""
security_headers.py — REL-14
=============================
Starlette middleware that injects security-critical HTTP response headers on
every outgoing response from the FastAPI service.

Headers applied
---------------
Strict-Transport-Security
    Instructs browsers and TLS clients to use HTTPS exclusively for the domain.
    max-age=31536000 (1 year), includeSubDomains, preload.

X-Content-Type-Options
    Prevents MIME-type sniffing; forces the declared Content-Type.

X-Frame-Options
    Disallows embedding the service in <iframe> / <frame> tags (clickjacking).

Referrer-Policy
    Sends the full URL only to same-origin requests; uses origin-only for
    cross-origin HTTPS targets; sends nothing over HTTP.

Content-Security-Policy
    Baseline CSP for an API service (no inline scripts / styles need to be
    loaded by browsers).  Adjust if you ever serve HTML.

Permissions-Policy
    Disables browser features the API has no reason to access.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ---------------------------------------------------------------------------
# Security header values
# ---------------------------------------------------------------------------

_HSTS = "max-age=31536000; includeSubDomains; preload"
_CONTENT_TYPE_OPTIONS = "nosniff"
_FRAME_OPTIONS = "DENY"
_REFERRER_POLICY = "strict-origin-when-cross-origin"
_CSP = "default-src 'none'; frame-ancestors 'none'"
_PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Appends transport-security and content-security headers to every response.

    Register this middleware **after** any authentication / routing middleware
    so it applies uniformly regardless of whether the route matched.

    Example::

        from app.middleware.security_headers import SecurityHeadersMiddleware

        app.add_middleware(SecurityHeadersMiddleware)
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response: Response = await call_next(request)

        # HSTS — force HTTPS for 1 year, include sub-domains, add to preload list.
        response.headers["Strict-Transport-Security"] = _HSTS

        # Prevent MIME-type confusion attacks.
        response.headers["X-Content-Type-Options"] = _CONTENT_TYPE_OPTIONS

        # Block the response from being framed (clickjacking defence).
        response.headers["X-Frame-Options"] = _FRAME_OPTIONS

        # Limit referrer data sent to third parties.
        response.headers["Referrer-Policy"] = _REFERRER_POLICY

        # Restrictive CSP for a pure JSON API service.
        response.headers["Content-Security-Policy"] = _CSP

        # Disable browser features that the API doesn't need.
        response.headers["Permissions-Policy"] = _PERMISSIONS_POLICY

        return response
