from datasette import hookimpl
from .views import turnstile_challenge_page, turnstile_verify
from .middleware import TurnstileMiddleware


@hookimpl
def register_routes():
    """Register routes for challenge page and verification."""
    return [
        (r"^/-/turnstile$", turnstile_challenge_page),
        (r"^/-/turnstile/verify$", turnstile_verify),
    ]


@hookimpl
def asgi_wrapper(datasette):
    """Wrap ASGI app with Turnstile middleware for path protection."""
    def wrap(app):
        return TurnstileMiddleware(app, datasette)
    return wrap
