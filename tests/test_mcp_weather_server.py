"""
Comprehensive test suite for MCP Weather Server.
This file imports and runs all test modules to ensure complete coverage.
"""

import pytest
from tests.test_weather_service import *
from tests.test_weather_tools import *
from tests.test_time_tools import *
from tests.test_utils import *
from tests.test_server import *
from tests.test_integration import *

# Additional legacy tests for backward compatibility
import httpx
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.asyncio
async def test_legacy_get_weather_functionality():
    """Legacy test to ensure backward compatibility."""
    # This test ensures that any legacy get_weather function (if it exists) still works
    try:
        from src.mcp_weather_server.server import get_weather

        # Mock HTTP client for legacy function
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 500
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await get_weather("InvalidCity")
            assert "Error" in str(result) or "error" in str(result).lower()

    except ImportError:
        # get_weather function doesn't exist, which is fine
        # The new architecture uses tool handlers instead
        pytest.skip("Legacy get_weather function not found - using new tool handler architecture")


# Smoke tests to verify all components work together
class TestSmokeTests:
    """Smoke tests to verify basic functionality."""

    @pytest.mark.asyncio
    async def test_can_import_all_modules(self):
        """Test that all modules can be imported without errors."""
        from src.mcp_weather_server import server
        from src.mcp_weather_server import utils
        from src.mcp_weather_server.tools import toolhandler
        from src.mcp_weather_server.tools import weather_service
        from src.mcp_weather_server.tools import tools_weather
        from src.mcp_weather_server.tools import tools_time

        # Basic assertions to ensure imports worked
        assert hasattr(server, 'register_all_tools')
        assert hasattr(utils, 'get_zoneinfo')
        assert hasattr(toolhandler, 'ToolHandler')
        assert hasattr(weather_service, 'WeatherService')

    @pytest.mark.asyncio
    async def test_server_starts_without_errors(self):
        """Test that server initialization doesn't raise errors."""
        from src.mcp_weather_server.server import register_all_tools, list_tools

        # Clear any existing handlers
        from src.mcp_weather_server.server import tool_handlers
        tool_handlers.clear()

        # Register tools and list them
        register_all_tools()
        tools = await list_tools()

        # Verify we have the expected number of tools
        assert len(tools) >= 6
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "get_current_weather",
            "get_weather_byDateTimeRange",
            "get_weather_details",
            "get_current_datetime",
            "get_timezone_info",
            "convert_time"
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names
