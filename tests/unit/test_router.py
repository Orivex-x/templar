"""Unit tests for Router module."""

import pytest
from templar.core.Exceptions import (
    InvalidRoutePatternError,
    RouteNotFoundError,
    DuplicateRouteError
)


@pytest.mark.unit
class TestRouter:
    """Tests for Router class."""
    
    def test_router_add_simple_route(self, router):
        """Test adding a simple route."""
        router.add("/test", "test")

        assert len(router.routes) == 5  # includes default routes
    
    def test_router_match_exact_path(self, router):
        """Test matching an exact path."""
        template, params = router.match("/")

        assert template == "index.templar.py"
        assert params == {}
    
    def test_router_match_with_params(self, router):
        """Test matching a path with parameters."""
        template, params = router.match("/user/42")

        assert template == "user.templar.py"
        assert params == {"id": "42"}
    
    def test_router_match_with_multiple_params(self, router):
        """Test matching a path with multiple parameters."""
        template, params = router.match("/product/electronics/12345")

        assert template == "product.templar.py"
        assert params == {"category": "electronics", "pid": "12345"}
    
    def test_router_match_not_found(self, router):
        """Test that non-matching paths return None."""
        template, params = router.match("/nonexistent")

        assert template is None
        assert params == {}
    
    def test_router_trailing_slash_handling(self, router):
        """Test that trailing slashes are handled."""
        template, params = router.match("/about/")

        assert template == "about.templar.py"
    
    def test_router_param_not_empty(self, router):
        """Test that params cannot be empty (no slashes)."""
        template, params = router.match("/user/")

        assert template is None
    
    def test_router_duplicate_route_error(self, router):
        """Test that duplicate routes raise error."""
        # First route already added in fixture
        with pytest.raises(ValueError):
            router.add("/", "index")

    def test_router_escapes_literal_regex_characters(self, router):
        router.add("/files.v1", "files")

        template, _ = router.match("/files.v1")

        assert template == "files.templar.py"

        template, _ = router.match("/filesXv1")

        assert template is None

    def test_static_routes_take_precedence_over_parameter_routes(self, router):
        router.add("/<page>", "generic")
        router.add("/contact", "contact-static")

        template, params = router.match("/contact")

        assert template == "contact-static.templar.py"
        assert params == {}
