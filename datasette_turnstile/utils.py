"""Utility functions for path matching and cookie handling."""
import re


def _pattern_to_regex(pattern: str) -> re.Pattern:
    """
    Convert a simple wildcard pattern to a regex.
    Only * is treated as special (matches any characters).
    All other characters are matched literally.
    """
    # Escape all regex special characters, then convert * to .*
    escaped = re.escape(pattern)
    regex_pattern = escaped.replace(r"\*", ".*")
    return re.compile(f"^{regex_pattern}$")


def url_matches_patterns(path: str, query_string: str, patterns: list[str]) -> bool:
    """
    Check if a URL (path + query string) matches any of the given patterns.
    Only * is treated as a wildcard (matches any characters).

    If the pattern contains '?', it matches against path?query_string.
    Otherwise, it matches against path only (ignoring query string).
    """
    for pattern in patterns:
        if "?" in pattern:
            # Pattern includes query string matching
            if query_string:
                full_url = f"{path}?{query_string}"
            else:
                full_url = path
            regex = _pattern_to_regex(pattern)
            if regex.match(full_url):
                return True
        else:
            # Pattern matches path only
            regex = _pattern_to_regex(pattern)
            if regex.match(path):
                return True
    return False


def is_excluded(path: str, exclude_patterns: list[str]) -> bool:
    """
    Check if a path should be excluded based on exclusion patterns.
    Matches against the full path or just the filename.
    Only * is treated as a wildcard.
    """
    if not exclude_patterns:
        return False

    for pattern in exclude_patterns:
        regex = _pattern_to_regex(pattern)
        if regex.match(path):
            return True
        # Also check just the filename portion for patterns like *.json
        filename = path.rsplit("/", 1)[-1]
        if regex.match(filename):
            return True
    return False
