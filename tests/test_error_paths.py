"""
Tests for previously uncovered paths: server runners, the forecast branch
of get_weather_details, and generic exception handling in tool handlers.
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch

from mcp.types import TextContent

from src.mcp_weather_server import server as server_module
from src.mcp_weather_server.server import run_server, main, create_starlette_app, app
from src.mcp_weather_server.tools.tools_weather import GetWeatherDetailsToolHandler
from src.mcp_weather_server.tools.tools_air_quality import GetAirQualityToolHandler


class TestRunServer:
    """Tests for the unified server runner."""

    @pytest.mark.asyncio
    async def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown mode"):
            await run_server("carrier-pigeon")

    @pytest.mark.asyncio
    async def test_stdio_mode_runs_app(self):
        streams = (AsyncMock(), AsyncMock())
        stdio_ctx = AsyncMock()
        stdio_ctx.__aenter__.return_value = streams

        with patch("mcp.server.stdio.stdio_server", return_value=stdio_ctx):
            with patch.object(server_module.app, "run", new=AsyncMock()) as mock_run:
                with patch.object(server_module.app, "create_initialization_options", return_value={}):
                    await run_server("stdio")
        mock_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sse_mode_starts_uvicorn(self):
        with patch.object(server_module.uvicorn, "Server") as mock_server_cls:
            mock_server_cls.return_value.serve = AsyncMock()
            await run_server("sse", host="127.0.0.1", port=9999)
            mock_server_cls.return_value.serve.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_streamable_http_mode_starts_uvicorn(self):
        with patch.object(server_module.uvicorn, "Server") as mock_server_cls:
            mock_server_cls.return_value.serve = AsyncMock()
            await run_server("streamable-http", host="127.0.0.1", port=9999, stateless=True)
            mock_server_cls.return_value.serve.assert_awaited_once()


class TestMainEntryPoint:
    """Tests for the CLI entry point."""

    @pytest.mark.asyncio
    async def test_main_uses_port_env_var(self):
        with patch("sys.argv", ["mcp_weather_server", "--mode", "sse"]):
            with patch.dict("os.environ", {"PORT": "9123"}):
                with patch.object(server_module, "run_server", new=AsyncMock()) as mock_run:
                    await main()
        args, kwargs = mock_run.call_args
        assert args[0] == "sse"
        assert args[2] == 9123

    @pytest.mark.asyncio
    async def test_main_cli_port_overrides_env(self):
        with patch("sys.argv", ["mcp_weather_server", "--mode", "sse", "--port", "7000"]):
            with patch.dict("os.environ", {"PORT": "9123"}):
                with patch.object(server_module, "run_server", new=AsyncMock()) as mock_run:
                    await main()
        args, kwargs = mock_run.call_args
        assert args[2] == 7000


class TestCreateStarletteApp:
    """Tests for the SSE Starlette app factory."""

    def test_routes_exist(self):
        starlette_app = create_starlette_app(app)
        paths = [getattr(route, "path", None) for route in starlette_app.routes]
        assert "/sse" in paths
        assert "/messages" in paths or "/messages/" in paths


class TestGetWeatherDetailsForecastBranch:
    """Tests for the include_forecast branch of get_weather_details."""

    @pytest.mark.asyncio
    async def test_forecast_included(self):
        handler = GetWeatherDetailsToolHandler()
        mock_service = Mock()
        mock_service.get_current_weather = AsyncMock(return_value={"city": "Paris", "temperature_c": 20})
        mock_service.get_weather_by_date_range = AsyncMock(
            return_value={"weather_data": [{"time": "2024-01-01T00:00", "temperature_c": 18}]}
        )
        handler.weather_service = mock_service

        result = await handler.run_tool({"city": "Paris", "include_forecast": True})

        payload = json.loads(result[0].text)
        assert payload["forecast"] == [{"time": "2024-01-01T00:00", "temperature_c": 18}]
        mock_service.get_weather_by_date_range.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_forecast_omitted_by_default(self):
        handler = GetWeatherDetailsToolHandler()
        mock_service = Mock()
        mock_service.get_current_weather = AsyncMock(return_value={"city": "Paris"})
        handler.weather_service = mock_service

        result = await handler.run_tool({"city": "Paris"})

        payload = json.loads(result[0].text)
        assert "forecast" not in payload


class TestUnexpectedExceptionPaths:
    """Generic (non-ValueError) exceptions must produce error content, not crash."""

    @pytest.mark.asyncio
    async def test_air_quality_unexpected_error(self):
        handler = GetAirQualityToolHandler()
        handler.weather_service.get_coordinates = AsyncMock(side_effect=RuntimeError("boom"))

        result = await handler.run_tool({"city": "Paris"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unexpected error" in result[0].text or "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_weather_details_unexpected_error(self):
        handler = GetWeatherDetailsToolHandler()
        mock_service = Mock()
        mock_service.get_current_weather = AsyncMock(side_effect=RuntimeError("boom"))
        handler.weather_service = mock_service

        result = await handler.run_tool({"city": "Paris"})

        payload = json.loads(result[0].text)
        assert "error" in payload
