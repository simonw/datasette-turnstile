import pytest
from pytest_httpx import HTTPXMock
from datasette_turnstile.verification import verify_turnstile_token

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


@pytest.mark.asyncio
async def test_successful_verification(httpx_mock: HTTPXMock):
    """Test successful token verification."""
    httpx_mock.add_response(
        url=TURNSTILE_VERIFY_URL,
        method="POST",
        json={
            "success": True,
            "challenge_ts": "2024-01-01T00:00:00Z",
            "hostname": "example.com",
            "error-codes": [],
        },
    )

    success, error_codes = await verify_turnstile_token(
        secret_key="test-secret",
        response_token="test-token",
    )

    assert success is True
    assert error_codes == []


@pytest.mark.asyncio
async def test_failed_verification(httpx_mock: HTTPXMock):
    """Test failed token verification."""
    httpx_mock.add_response(
        url=TURNSTILE_VERIFY_URL,
        method="POST",
        json={
            "success": False,
            "error-codes": ["invalid-input-response"],
        },
    )

    success, error_codes = await verify_turnstile_token(
        secret_key="test-secret",
        response_token="invalid-token",
    )

    assert success is False
    assert "invalid-input-response" in error_codes


@pytest.mark.asyncio
async def test_verification_with_remote_ip(httpx_mock: HTTPXMock):
    """Test that remote IP is passed to the API."""
    httpx_mock.add_response(
        url=TURNSTILE_VERIFY_URL,
        method="POST",
        json={"success": True, "error-codes": []},
    )

    await verify_turnstile_token(
        secret_key="test-secret",
        response_token="test-token",
        remote_ip="192.168.1.1",
    )

    # Verify the request was made with correct form data
    request = httpx_mock.get_request()
    body = request.content.decode("utf-8")
    assert "secret=test-secret" in body
    assert "response=test-token" in body
    assert "remoteip=192.168.1.1" in body


@pytest.mark.asyncio
async def test_expired_token(httpx_mock: HTTPXMock):
    """Test handling of expired/duplicate token."""
    httpx_mock.add_response(
        url=TURNSTILE_VERIFY_URL,
        method="POST",
        json={
            "success": False,
            "error-codes": ["timeout-or-duplicate"],
        },
    )

    success, error_codes = await verify_turnstile_token(
        secret_key="test-secret",
        response_token="expired-token",
    )

    assert success is False
    assert "timeout-or-duplicate" in error_codes


@pytest.mark.asyncio
async def test_network_error(httpx_mock: HTTPXMock):
    """Test handling of network errors."""
    httpx_mock.add_exception(Exception("Connection failed"))

    success, error_codes = await verify_turnstile_token(
        secret_key="test-secret",
        response_token="test-token",
    )

    assert success is False
    assert len(error_codes) > 0  # Should contain error info
