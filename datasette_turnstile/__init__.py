from datasette import hookimpl
from .views import turnstile_challenge_page, turnstile_verify


@hookimpl
def register_routes():
    """Register routes for challenge page and verification."""
    return [
        (r"^/-/turnstile$", turnstile_challenge_page),
        (r"^/-/turnstile/verify$", turnstile_verify),
    ]
