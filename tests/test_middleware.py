import httpx
import pytest
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
                    "protected_paths": ["/admin/*", "/-/import-*"],
                    "exclude_patterns": ["*.json"],
                }
            }
        },
    )


async def get(ds, path, **kwargs):
    """Make a request using httpx.ASGITransport to simulate external traffic."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=ds.app()),
    ) as client:
        url = f"http://localhost{path}"
        return await client.get(url, **kwargs)


@pytest.mark.asyncio
async def test_unprotected_path_passes_through(datasette_with_turnstile):
    """Test that unprotected paths are not blocked."""
    response = await get(datasette_with_turnstile, "/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_path_redirects_to_challenge(datasette_with_turnstile):
    """Test that protected paths redirect to challenge when not verified."""
    response = await get(
        datasette_with_turnstile, "/admin/users", follow_redirects=False
    )
    assert response.status_code == 302
    location = response.headers["location"]
    assert "/-/turnstile" in location
    assert "next=" in location


@pytest.mark.asyncio
async def test_verified_cookie_allows_access(datasette_with_turnstile):
    """Test that valid verification cookie allows access."""
    # Create a valid signed cookie
    cookie_value = datasette_with_turnstile.sign(
        {"verified": True, "timestamp": 9999999999},
        namespace="turnstile",
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=datasette_with_turnstile.app()),
        cookies={"ds_turnstile": cookie_value},
    ) as client:
        response = await client.get("http://localhost/admin/users")
    # Should not redirect - though may 404 since /admin doesn't exist
    assert response.status_code != 302


@pytest.mark.asyncio
async def test_invalid_cookie_redirects(datasette_with_turnstile):
    """Test that invalid cookie still redirects to challenge."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=datasette_with_turnstile.app()),
        cookies={"ds_turnstile": "invalid-cookie-value"},
    ) as client:
        response = await client.get(
            "http://localhost/admin/users", follow_redirects=False
        )
    assert response.status_code == 302
    assert "/-/turnstile" in response.headers["location"]


@pytest.mark.asyncio
async def test_json_excluded_passes_through(datasette_with_turnstile):
    """Test that excluded paths (*.json) are not blocked."""
    response = await get(
        datasette_with_turnstile, "/admin/data.json", follow_redirects=False
    )
    # Should not redirect to challenge (though may 404)
    assert response.status_code != 302


@pytest.mark.asyncio
async def test_preserves_query_string_in_next(datasette_with_turnstile):
    """Test that query string is preserved in next parameter."""
    response = await get(
        datasette_with_turnstile,
        "/admin/users?page=2&sort=name",
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers["location"]
    # The next parameter should contain the full URL with query string
    assert "page=2" in location or "page%3D2" in location  # URL encoded or not


@pytest.mark.asyncio
async def test_no_config_passes_through():
    """Test that plugin does nothing when not configured."""
    ds = Datasette(memory=True)
    response = await get(ds, "/admin/users")
    # Should not redirect (though may 404)
    assert response.status_code != 302


@pytest.mark.asyncio
async def test_empty_protected_paths_passes_through():
    """Test that empty protected_paths means nothing is protected."""
    ds = Datasette(
        memory=True,
        metadata={
            "plugins": {
                "datasette-turnstile": {
                    "site_key": "test-site-key",
                    "secret_key": "test-secret-key",
                    "protected_paths": [],
                }
            }
        },
    )
    response = await get(ds, "/admin/users")
    # Should not redirect
    assert response.status_code != 302


@pytest.mark.asyncio
async def test_json_accept_header_returns_403():
    """Test that JSON requests to protected paths return 403 JSON."""
    ds = Datasette(
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
    response = await get(
        ds,
        "/admin/users",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 403
    data = response.json()
    assert "error" in data
    assert data["error"] == "turnstile_required"


@pytest.mark.asyncio
async def test_query_string_pattern_matching():
    """Test that query string patterns work for protection."""
    ds = Datasette(
        memory=True,
        metadata={
            "plugins": {
                "datasette-turnstile": {
                    "site_key": "test-site-key",
                    "secret_key": "test-secret-key",
                    "protected_paths": ["/data?*&*&*"],  # 2+ ampersands
                }
            }
        },
    )

    # Should be protected (3 params = 2 ampersands)
    response = await get(ds, "/data?a=1&b=2&c=3", follow_redirects=False)
    assert response.status_code == 302

    # Should NOT be protected (2 params = 1 ampersand)
    response = await get(ds, "/data?a=1&b=2", follow_redirects=False)
    assert response.status_code != 302


@pytest.mark.asyncio
async def test_internal_client_requests_bypass_protection():
    """Test that internal datasette.client requests skip turnstile protection."""
    ds = Datasette(
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
    # External request should be blocked
    response = await get(ds, "/admin/users", follow_redirects=False)
    assert response.status_code == 302

    # Internal datasette.client request should bypass protection
    response = await ds.client.get("/admin/users", follow_redirects=False)
    assert response.status_code != 302
