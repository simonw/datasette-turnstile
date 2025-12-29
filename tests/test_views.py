import pytest
from pytest_httpx import HTTPXMock
from datasette.app import Datasette


@pytest.fixture
def datasette_with_turnstile():
    """Create a Datasette instance with turnstile plugin configured."""
    return Datasette(
        memory=True,
        metadata={
            "plugins": {
                "datasette-turnstile": {
                    "site_key": "test-site-key",
                    "secret_key": "test-secret-key",
                    "protected_paths": ["/admin/*"],
                }
            }
        },
    )


@pytest.mark.asyncio
async def test_challenge_page_renders(datasette_with_turnstile):
    """Test that the challenge page renders correctly."""
    response = await datasette_with_turnstile.client.get("/-/turnstile?next=/admin/")
    assert response.status_code == 200
    html = response.text
    assert "Security Verification" in html
    assert "test-site-key" in html
    assert 'name="next" value="/admin/"' in html
    assert "/-/turnstile/verify" in html


@pytest.mark.asyncio
async def test_challenge_page_shows_error(datasette_with_turnstile):
    """Test that the challenge page shows error messages."""
    response = await datasette_with_turnstile.client.get(
        "/-/turnstile?next=/admin/&error=timeout-or-duplicate"
    )
    assert response.status_code == 200
    html = response.text
    assert "Verification failed" in html
    assert "Token expired" in html


@pytest.mark.asyncio
async def test_challenge_page_missing_site_key():
    """Test error when site_key is not configured."""
    ds = Datasette(
        memory=True,
        metadata={
            "plugins": {
                "datasette-turnstile": {
                    # No site_key
                    "secret_key": "test-secret",
                }
            }
        },
    )
    response = await ds.client.get("/-/turnstile?next=/admin/")
    assert response.status_code == 500
    assert "site_key not configured" in response.text


@pytest.mark.asyncio
async def test_verify_success(datasette_with_turnstile, httpx_mock: HTTPXMock):
    """Test successful verification sets cookie and redirects."""
    httpx_mock.add_response(
        url="https://challenges.cloudflare.com/turnstile/v0/siteverify",
        method="POST",
        json={"success": True, "error-codes": []},
    )

    response = await datasette_with_turnstile.client.post(
        "/-/turnstile/verify",
        data={
            "cf-turnstile-response": "valid-token",
            "next": "/admin/",
            "csrftoken": "test",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/admin/"
    assert "ds_turnstile" in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_verify_failure(datasette_with_turnstile, httpx_mock: HTTPXMock):
    """Test failed verification redirects back with error."""
    httpx_mock.add_response(
        url="https://challenges.cloudflare.com/turnstile/v0/siteverify",
        method="POST",
        json={"success": False, "error-codes": ["invalid-input-response"]},
    )

    response = await datasette_with_turnstile.client.post(
        "/-/turnstile/verify",
        data={
            "cf-turnstile-response": "invalid-token",
            "next": "/admin/",
            "csrftoken": "test",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = response.headers["location"]
    assert "/-/turnstile" in location
    assert "error=" in location


@pytest.mark.asyncio
async def test_verify_missing_token(datasette_with_turnstile):
    """Test verification fails when token is missing."""
    response = await datasette_with_turnstile.client.post(
        "/-/turnstile/verify",
        data={
            "next": "/admin/",
            "csrftoken": "test",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = response.headers["location"]
    assert "error=missing_token" in location


@pytest.mark.asyncio
async def test_verify_method_not_allowed(datasette_with_turnstile):
    """Test GET request to verify endpoint is rejected."""
    response = await datasette_with_turnstile.client.get("/-/turnstile/verify")
    assert response.status_code == 405
