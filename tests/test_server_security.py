"""
Security-focused tests for the HTTP server configuration.

Covers the CORS hardening (no wildcard origin combined with credentials)
and the localhost-by-default bind address.
"""

import inspect
from unittest.mock import patch

from starlette.middleware.cors import CORSMiddleware

from src.mcp_weather_server import server as server_module
from src.mcp_weather_server.server import (
    app,
    build_arg_parser,
    create_streamable_http_app,
    get_allowed_origins,
    run_server,
)


def get_cors_kwargs(starlette_app):
    """Extract the CORSMiddleware kwargs from a Starlette app."""
    for middleware in starlette_app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return middleware.kwargs
    raise AssertionError("CORSMiddleware not found on app")


class TestCorsConfiguration:
    def test_wildcard_origin_disables_credentials(self):
        with patch.dict("os.environ", {}, clear=False):
            starlette_app = create_streamable_http_app(app)
        kwargs = get_cors_kwargs(starlette_app)
        assert kwargs["allow_origins"] == ["*"]
        assert kwargs["allow_credentials"] is False

    def test_restricted_origins_allow_credentials(self):
        env = {"MCP_ALLOWED_ORIGINS": "https://example.com, https://other.example"}
        with patch.dict("os.environ", env):
            starlette_app = create_streamable_http_app(app)
        kwargs = get_cors_kwargs(starlette_app)
        assert kwargs["allow_origins"] == ["https://example.com", "https://other.example"]
        assert kwargs["allow_credentials"] is True

    def test_headers_are_not_wildcarded(self):
        starlette_app = create_streamable_http_app(app)
        kwargs = get_cors_kwargs(starlette_app)
        assert "*" not in kwargs["allow_headers"]


class TestGetAllowedOrigins:
    def test_default_is_wildcard(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("MCP_ALLOWED_ORIGINS", None)
            assert get_allowed_origins() == ["*"]

    def test_parses_comma_separated_list(self):
        with patch.dict("os.environ", {"MCP_ALLOWED_ORIGINS": "https://a.com,https://b.com"}):
            assert get_allowed_origins() == ["https://a.com", "https://b.com"]

    def test_empty_value_falls_back_to_wildcard(self):
        with patch.dict("os.environ", {"MCP_ALLOWED_ORIGINS": " , "}):
            assert get_allowed_origins() == ["*"]


class TestBindDefaults:
    def test_cli_default_host_is_localhost(self):
        args = build_arg_parser().parse_args([])
        assert args.host == "127.0.0.1"

    def test_run_server_default_host_is_localhost(self):
        signature = inspect.signature(run_server)
        assert signature.parameters["host"].default == "127.0.0.1"

    def test_explicit_host_still_supported(self):
        args = build_arg_parser().parse_args(["--host", "0.0.0.0"])
        assert args.host == "0.0.0.0"
