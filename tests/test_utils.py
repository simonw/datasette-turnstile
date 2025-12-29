import pytest
from datasette_turnstile.utils import url_matches_patterns, is_excluded


class TestUrlMatchesPatterns:
    """Tests for url_matches_patterns function (matches path + query string)."""

    def test_exact_match(self):
        assert url_matches_patterns("/admin", "", ["/admin"]) is True

    def test_no_match(self):
        assert url_matches_patterns("/public", "", ["/admin"]) is False

    def test_wildcard_single_segment(self):
        assert url_matches_patterns("/admin/users", "", ["/admin/*"]) is True
        assert url_matches_patterns("/admin/settings", "", ["/admin/*"]) is True

    def test_wildcard_no_match_root(self):
        # /admin/* should NOT match /admin itself
        assert url_matches_patterns("/admin", "", ["/admin/*"]) is False

    def test_multiple_patterns(self):
        patterns = ["/admin/*", "/-/import-*"]
        assert url_matches_patterns("/admin/users", "", patterns) is True
        assert url_matches_patterns("/-/import-csv", "", patterns) is True
        assert url_matches_patterns("/public", "", patterns) is False

    def test_nested_path_match(self):
        # fnmatch's * matches any characters including /
        assert url_matches_patterns("/admin/users/123", "", ["/admin/*"]) is True
        assert url_matches_patterns("/admin/a/b/c/d", "", ["/admin/*"]) is True

    def test_empty_patterns(self):
        assert url_matches_patterns("/admin", "", []) is False

    def test_prefix_pattern(self):
        assert url_matches_patterns("/-/import-csv", "", ["/-/import-*"]) is True
        assert url_matches_patterns("/-/import-json", "", ["/-/import-*"]) is True
        assert url_matches_patterns("/-/export-csv", "", ["/-/import-*"]) is False

    # New tests for query string matching
    def test_query_string_with_multiple_ampersands(self):
        # Match /data with 2+ ampersands in query string
        pattern = "/data?*&*&*"
        # 2 ampersands = 3 params
        assert url_matches_patterns("/data", "a=1&b=2&c=3", [pattern]) is True
        # 3 ampersands = 4 params
        assert url_matches_patterns("/data", "a=1&b=2&c=3&d=4", [pattern]) is True
        # 1 ampersand = 2 params (not enough)
        assert url_matches_patterns("/data", "a=1&b=2", [pattern]) is False
        # No query string
        assert url_matches_patterns("/data", "", [pattern]) is False

    def test_query_string_exact_path_any_query(self):
        # Match /search with any query string
        pattern = "/search?*"
        assert url_matches_patterns("/search", "q=hello", [pattern]) is True
        assert url_matches_patterns("/search", "q=hello&page=2", [pattern]) is True
        assert url_matches_patterns("/search", "", [pattern]) is False

    def test_path_only_pattern_ignores_query_string(self):
        # Pattern without ? should match regardless of query string
        assert url_matches_patterns("/admin", "foo=bar", ["/admin"]) is True
        assert url_matches_patterns("/admin/users", "id=123", ["/admin/*"]) is True


class TestIsExcluded:
    """Tests for is_excluded function."""

    def test_json_exclusion(self):
        assert is_excluded("/admin/data.json", ["*.json"]) is True

    def test_json_not_excluded(self):
        assert is_excluded("/admin/data", ["*.json"]) is False

    def test_empty_exclusions(self):
        assert is_excluded("/admin/data.json", []) is False

    def test_multiple_exclusions(self):
        exclusions = ["*.json", "*.csv"]
        assert is_excluded("/data.json", exclusions) is True
        assert is_excluded("/data.csv", exclusions) is True
        assert is_excluded("/data.html", exclusions) is False

    def test_path_suffix_pattern(self):
        # Match paths ending with .json anywhere
        assert is_excluded("/api/v1/users.json", ["*.json"]) is True
