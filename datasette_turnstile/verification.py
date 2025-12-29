"""Cloudflare Turnstile token verification."""
import httpx

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(
    secret_key: str,
    response_token: str,
    remote_ip: str | None = None,
) -> tuple[bool, list[str]]:
    """
    Verify a Turnstile token with Cloudflare's API.

    Args:
        secret_key: Your widget's secret key from Cloudflare dashboard
        response_token: The token from the client-side widget (cf-turnstile-response)
        remote_ip: Optional visitor's IP address

    Returns:
        tuple of (success: bool, error_codes: list[str])
    """
    data = {
        "secret": secret_key,
        "response": response_token,
    }
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data=data,  # application/x-www-form-urlencoded
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()

            success = result.get("success", False)
            error_codes = result.get("error-codes", [])

            return success, error_codes

    except httpx.HTTPError as e:
        return False, ["network_error", str(e)]
    except Exception as e:
        return False, ["unexpected_error", str(e)]
