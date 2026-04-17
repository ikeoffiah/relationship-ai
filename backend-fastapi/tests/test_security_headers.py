"""
test_security_headers.py — REL-14
==================================
Validates that every response from the FastAPI service carries the required
transport-security and content-security headers (HSTS, X-Content-Type-Options,
X-Frame-Options, Referrer-Policy, CSP, Permissions-Policy).

Run with:
    cd backend-fastapi && pytest tests/test_security_headers.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client wired directly to the FastAPI ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# HSTS
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_hsts_header_present(client):
    response = await client.get("/health")
    assert "strict-transport-security" in response.headers, (
        "Strict-Transport-Security header is missing"
    )


@pytest.mark.anyio
async def test_hsts_max_age_one_year(client):
    response = await client.get("/health")
    hsts = response.headers["strict-transport-security"]
    assert "max-age=31536000" in hsts, f"Expected 1-year max-age, got: {hsts}"


@pytest.mark.anyio
async def test_hsts_includes_subdomains(client):
    response = await client.get("/health")
    hsts = response.headers["strict-transport-security"]
    assert "includeSubDomains" in hsts, f"includeSubDomains missing from HSTS: {hsts}"


@pytest.mark.anyio
async def test_hsts_preload(client):
    response = await client.get("/health")
    hsts = response.headers["strict-transport-security"]
    assert "preload" in hsts, f"preload directive missing from HSTS: {hsts}"


# ---------------------------------------------------------------------------
# X-Content-Type-Options
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_x_content_type_options(client):
    response = await client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff", (
        "X-Content-Type-Options must be 'nosniff'"
    )


# ---------------------------------------------------------------------------
# X-Frame-Options
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_x_frame_options(client):
    response = await client.get("/health")
    assert response.headers.get("x-frame-options") == "DENY", (
        "X-Frame-Options must be 'DENY'"
    )


# ---------------------------------------------------------------------------
# Referrer-Policy
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_referrer_policy(client):
    response = await client.get("/health")
    assert (
        response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    ), "Referrer-Policy header has unexpected value"


# ---------------------------------------------------------------------------
# Content-Security-Policy
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_content_security_policy_present(client):
    response = await client.get("/health")
    assert "content-security-policy" in response.headers, (
        "Content-Security-Policy header is missing"
    )


@pytest.mark.anyio
async def test_content_security_policy_default_none(client):
    response = await client.get("/health")
    csp = response.headers["content-security-policy"]
    assert "default-src 'none'" in csp, f"CSP should deny by default, got: {csp}"


# ---------------------------------------------------------------------------
# Permissions-Policy
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_permissions_policy_present(client):
    response = await client.get("/health")
    assert "permissions-policy" in response.headers, (
        "Permissions-Policy header is missing"
    )


# ---------------------------------------------------------------------------
# Header presence on non-health routes
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_headers_present_on_root(client):
    """Security headers must appear on every route, not just /health."""
    response = await client.get("/")
    assert "strict-transport-security" in response.headers
    assert "x-content-type-options" in response.headers
    assert "x-frame-options" in response.headers


@pytest.mark.anyio
async def test_headers_present_on_404(client):
    """Security headers must appear even on 404 responses."""
    response = await client.get("/this-route-does-not-exist")
    assert "strict-transport-security" in response.headers
    assert "x-content-type-options" in response.headers
