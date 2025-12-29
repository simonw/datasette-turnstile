# datasette-turnstile Specification

A Datasette plugin that protects specified URL paths with Cloudflare Turnstile challenges.

## Configuration

Plugin is configured via `datasette.yaml`:

```yaml
plugins:
  datasette-turnstile:
    site_key: "0x4AAAAAAxxxxxxxxxxxxxxx"
    secret_key:
      $env: TURNSTILE_SECRET_KEY
    protected_paths:
      - "/admin/*"
      - "/-/import-*"
    cookie_max_age: 86400  # Optional, default 24 hours
    exclude_patterns:      # Optional
      - "*.json"
```

## Components

### 1. URL Matching (`utils.py`)
- [x] `url_matches_patterns(path, query_string, patterns)` - wildcard matching (only `*` is special)
- [x] `is_excluded(path, exclude_patterns)` - check exclusions
- [ ] `get_cookie_value(scope, cookie_name)` - extract cookie from ASGI scope
- [ ] `is_verified(scope, datasette, cookie_name)` - check signed cookie validity
- [ ] `create_verified_cookie_value(datasette)` - create signed cookie

### 2. Turnstile Verification (`verification.py`)
- [x] `verify_turnstile_token(secret_key, response_token, remote_ip)` - call Cloudflare API

### 3. Views (`views.py`)
- [x] `turnstile_challenge_page(request, datasette)` - GET `/-/turnstile`
- [x] `turnstile_verify(request, datasette)` - POST `/-/turnstile/verify`

### 4. Middleware (`middleware.py`)
- [ ] `TurnstileMiddleware` class - ASGI wrapper
  - Check if path matches protected_paths
  - Check if path matches exclude_patterns (skip if so)
  - Check for valid verification cookie
  - Redirect to challenge page if not verified
  - Return 403 JSON for API requests without valid cookie

### 5. Hook Registration (`__init__.py`)
- [ ] `asgi_wrapper(datasette)` - register middleware
- [ ] `register_routes()` - register challenge and verify routes

### 6. Template (`templates/turnstile_challenge.html`)
- [ ] Render Turnstile widget with site_key
- [ ] Form posts to `/-/turnstile/verify`
- [ ] Hidden `next` field for redirect after success

## Implementation Progress

- [x] Project skeleton with pyproject.toml
- [x] Path matching utilities with tests
- [x] Cloudflare verification with tests
- [x] Challenge views with tests
- [ ] ASGI middleware with tests
- [ ] Hook registration
- [ ] Template
- [ ] Integration tests
