"""Views for the Turnstile challenge page and verification endpoint."""
import time
from urllib.parse import urlencode
from datasette import Response
from .verification import verify_turnstile_token


async def turnstile_challenge_page(request, datasette):
    """Display the Turnstile challenge page."""
    config = datasette.plugin_config("datasette-turnstile") or {}
    site_key = config.get("site_key")

    if not site_key:
        return Response.html(
            "<h1>Configuration Error</h1><p>Turnstile site_key not configured</p>",
            status=500,
        )

    # Get the 'next' URL from query params (where to redirect after success)
    next_url = request.args.get("next", "/")
    error = request.args.get("error")

    html = await datasette.render_template(
        "turnstile_challenge.html",
        {
            "site_key": site_key,
            "next_url": next_url,
            "error": error,
            "verify_url": datasette.urls.path("/-/turnstile/verify"),
        },
        request=request,
    )
    return Response.html(html)


async def turnstile_verify(request, datasette):
    """Verify the Turnstile token and set cookie on success."""
    if request.method != "POST":
        return Response.html("Method not allowed", status=405)

    config = datasette.plugin_config("datasette-turnstile") or {}
    secret_key = config.get("secret_key")

    if not secret_key:
        return Response.html(
            "<h1>Configuration Error</h1><p>Turnstile secret_key not configured</p>",
            status=500,
        )

    # Get form data
    form_data = await request.post_vars()
    turnstile_response = form_data.get("cf-turnstile-response", "")
    next_url = form_data.get("next", "/")

    if not turnstile_response:
        # No token - redirect back to challenge with error
        redirect_url = datasette.urls.path("/-/turnstile")
        redirect_url += "?" + urlencode({"next": next_url, "error": "missing_token"})
        return Response.redirect(redirect_url)

    # Get client IP (optional but recommended)
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.scope.get("client", ("", 0))[0] if request.scope.get("client") else None

    # Verify token with Cloudflare
    success, error_codes = await verify_turnstile_token(
        secret_key=secret_key,
        response_token=turnstile_response,
        remote_ip=client_ip,
    )

    if not success:
        # Verification failed - redirect back with error
        error = ",".join(error_codes) if error_codes else "verification_failed"
        redirect_url = datasette.urls.path("/-/turnstile")
        redirect_url += "?" + urlencode({"next": next_url, "error": error})
        return Response.redirect(redirect_url)

    # Success! Set signed cookie and redirect to original URL
    cookie_name = config.get("cookie_name", "ds_turnstile")
    cookie_max_age = config.get("cookie_max_age", 86400)  # 24 hours default

    # Create signed cookie value with timestamp
    cookie_value = datasette.sign(
        {"verified": True, "timestamp": int(time.time())},
        namespace="turnstile",
    )

    response = Response.redirect(next_url)
    response.set_cookie(
        key=cookie_name,
        value=cookie_value,
        max_age=cookie_max_age,
        path="/",
        httponly=True,
        samesite="lax",
    )
    return response
