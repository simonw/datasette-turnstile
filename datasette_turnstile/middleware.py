"""ASGI middleware for Turnstile path protection."""
import json
from functools import wraps
from http.cookies import SimpleCookie
from urllib.parse import urlencode

from .utils import url_matches_patterns, is_excluded


class TurnstileMiddleware:
    """ASGI middleware that intercepts requests to protected paths."""

    def __init__(self, app, datasette):
        self.app = app
        self.datasette = datasette

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # Pass through websockets, lifespan events, etc.
            await self.app(scope, receive, send)
            return

        config = self.datasette.plugin_config("datasette-turnstile") or {}
        protected_paths = config.get("protected_paths", [])

        if not protected_paths:
            # No paths configured, pass through
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        query_string = scope.get("query_string", b"").decode("utf-8")

        # Check if this path needs protection
        if not url_matches_patterns(path, query_string, protected_paths):
            await self.app(scope, receive, send)
            return

        # Check if path is excluded
        exclude_patterns = config.get("exclude_patterns", [])
        if is_excluded(path, exclude_patterns):
            await self.app(scope, receive, send)
            return

        # Check if user has already verified
        cookie_name = config.get("cookie_name", "ds_turnstile")
        if self._is_verified(scope, cookie_name):
            await self.app(scope, receive, send)
            return

        # Check if this is a JSON request
        if self._is_json_request(scope):
            await self._send_json_forbidden(send)
            return

        # User needs to complete challenge - redirect to challenge page
        original_url = path
        if query_string:
            original_url += "?" + query_string

        redirect_url = self.datasette.urls.path("/-/turnstile")
        redirect_url += "?" + urlencode({"next": original_url})

        await self._send_redirect(send, redirect_url)

    def _is_verified(self, scope, cookie_name: str) -> bool:
        """Check if the request has a valid verification cookie."""
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode("utf-8")

        if not cookie_header:
            return False

        cookies = SimpleCookie()
        cookies.load(cookie_header)

        if cookie_name not in cookies:
            return False

        cookie_value = cookies[cookie_name].value

        try:
            data = self.datasette.unsign(cookie_value, namespace="turnstile")
            if isinstance(data, dict) and data.get("verified"):
                return True
        except Exception:
            pass

        return False

    def _is_json_request(self, scope) -> bool:
        """Check if the request is a JSON request based on Accept header."""
        headers = dict(scope.get("headers", []))
        accept = headers.get(b"accept", b"").decode("utf-8")
        return "application/json" in accept

    async def _send_redirect(self, send, location: str):
        """Send a 302 redirect response."""
        await send({
            "type": "http.response.start",
            "status": 302,
            "headers": [
                (b"location", location.encode("utf-8")),
                (b"content-type", b"text/html; charset=utf-8"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": b"Redirecting...",
        })

    async def _send_json_forbidden(self, send):
        """Send a 403 JSON response for API requests."""
        body = json.dumps({"error": "turnstile_required"}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"application/json"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
