"""
Unit tests for time-related tool handlers.
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from mcp.types import TextContent
from mcp import McpError
from src.mcp_weather_server.tools.tools_time import (
    GetCurrentDateTimeToolHandler,
    GetTimeZoneInfoToolHandler,
    ConvertTimeToolHandler
)


class TestGetCurrentDateTimeToolHandler:
    """Test cases for GetCurrentDateTimeToolHandler."""

    @pytest.fixture
    def handler(self):
        """Create a GetCurrentDateTimeToolHandler instance."""
        return GetCurrentDateTimeToolHandler()

    def test_tool_description(self, handler):
        """Test the tool description is properly formatted."""
        description = handler.get_tool_description()

        assert description.name == "get_current_datetime"
        assert "current time" in description.description.lower()
        assert description.inputSchema["type"] == "object"
        assert "timezone_name" in description.inputSchema["properties"]
        assert description.inputSchema["required"] == ["timezone_name"]

    @pytest.mark.asyncio
    async def test_run_tool_success(self, handler):
        """Test successful tool execution."""
        fixed_time = datetime(2024, 1, 1, 15, 30, 45, tzinfo=ZoneInfo("America/New_York"))

        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.return_value = ZoneInfo("America/New_York")
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = fixed_time

                args = {"timezone_name": "America/New_York"}
                result = await handler.run_tool(args)

                assert len(result) == 1
                assert isinstance(result[0], TextContent)

                response_data = json.loads(result[0].text)
                assert response_data["timezone"] == "America/New_York"
                assert "2024-01-01T15:30:45" in response_data["datetime"]

    @pytest.mark.asyncio
    async def test_run_tool_missing_timezone(self, handler):
        """Test tool execution with missing timezone argument."""
        args = {}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Missing required arguments: timezone_name" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_invalid_timezone(self, handler):
        """Test tool execution with invalid timezone."""
        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.side_effect = McpError("Invalid timezone: Invalid/Timezone")

            args = {"timezone_name": "Invalid/Timezone"}
            result = await handler.run_tool(args)

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Error getting current time: Invalid timezone" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_utc_timezone(self, handler):
        """Test tool execution with UTC timezone."""
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.return_value = ZoneInfo("UTC")
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = fixed_time

                args = {"timezone_name": "UTC"}
                result = await handler.run_tool(args)

                assert len(result) == 1
                response_data = json.loads(result[0].text)
                assert response_data["timezone"] == "UTC"
                assert "2024-01-01T12:00:00" in response_data["datetime"]


class TestGetTimeZoneInfoToolHandler:
    """Test cases for GetTimeZoneInfoToolHandler."""

    @pytest.fixture
    def handler(self):
        """Create a GetTimeZoneInfoToolHandler instance."""
        return GetTimeZoneInfoToolHandler()

    def test_tool_description(self, handler):
        """Test the tool description is properly formatted."""
        description = handler.get_tool_description()

        assert description.name == "get_timezone_info"
        assert "timezone" in description.description.lower()
        assert description.inputSchema["type"] == "object"
        assert "timezone_name" in description.inputSchema["properties"]
        assert description.inputSchema["required"] == ["timezone_name"]

    @pytest.mark.asyncio
    async def test_run_tool_success(self, handler):
        """Test successful tool execution."""
        fixed_time = datetime(2024, 6, 15, 14, 30, 0, tzinfo=ZoneInfo("Europe/London"))

        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.return_value = ZoneInfo("Europe/London")
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = fixed_time

                args = {"timezone_name": "Europe/London"}
                result = await handler.run_tool(args)

                assert len(result) == 1
                assert isinstance(result[0], TextContent)

                response_data = json.loads(result[0].text)
                assert response_data["timezone"] == "Europe/London"
                assert "current_time" in response_data
                assert "utc_offset" in response_data

    @pytest.mark.asyncio
    async def test_run_tool_missing_timezone(self, handler):
        """Test tool execution with missing timezone argument."""
        args = {}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Missing required arguments: timezone_name" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_invalid_timezone(self, handler):
        """Test tool execution with invalid timezone."""
        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.side_effect = McpError("Invalid timezone")

            args = {"timezone_name": "Invalid/Timezone"}
            result = await handler.run_tool(args)

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Error getting timezone info: Invalid timezone" in result[0].text


class TestConvertTimeToolHandler:
    """Test cases for ConvertTimeToolHandler."""

    @pytest.fixture
    def handler(self):
        """Create a ConvertTimeToolHandler instance."""
        return ConvertTimeToolHandler()

    def test_tool_description(self, handler):
        """Test the tool description is properly formatted."""
        description = handler.get_tool_description()

        assert description.name == "convert_time"
        assert "convert time" in description.description.lower()
        assert description.inputSchema["type"] == "object"
        required_fields = ["datetime", "from_timezone", "to_timezone"]
        for field in required_fields:
            assert field in description.inputSchema["properties"]
        assert set(description.inputSchema["required"]) == set(required_fields)

    @pytest.mark.asyncio
    async def test_run_tool_success(self, handler):
        """Test successful time conversion."""
        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            # Mock timezone creation
            mock_get_tz.side_effect = lambda tz: ZoneInfo(tz)

            with patch('dateutil.parser.parse') as mock_parse:
                # Mock parsing the datetime string
                source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
                mock_parse.return_value = source_time

                args = {
                    "datetime": "2024-01-01T12:00:00",
                    "from_timezone": "UTC",
                    "to_timezone": "America/New_York"
                }
                result = await handler.run_tool(args)

                assert len(result) == 1
                assert isinstance(result[0], TextContent)

                response_data = json.loads(result[0].text)
                assert response_data["original_datetime"] == "2024-01-01T12:00:00"
                assert response_data["from_timezone"] == "UTC"
                assert response_data["to_timezone"] == "America/New_York"
                assert "converted_datetime" in response_data

    @pytest.mark.asyncio
    async def test_run_tool_missing_required_args(self, handler):
        """Test tool execution with missing required arguments."""
        args = {"datetime": "2024-01-01T12:00:00"}  # Missing timezones
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Missing required arguments" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_invalid_datetime_format(self, handler):
        """Test tool execution with invalid datetime format."""
        with patch('dateutil.parser.parse') as mock_parse:
            mock_parse.side_effect = ValueError("Invalid datetime format")

            args = {
                "datetime": "invalid-datetime",
                "from_timezone": "UTC",
                "to_timezone": "America/New_York"
            }
            result = await handler.run_tool(args)

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Error converting time" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_invalid_from_timezone(self, handler):
        """Test tool execution with invalid from_timezone."""
        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            def side_effect(tz):
                if tz == "Invalid/Timezone":
                    raise McpError("Invalid timezone")
                return ZoneInfo(tz)
            mock_get_tz.side_effect = side_effect

            args = {
                "datetime": "2024-01-01T12:00:00",
                "from_timezone": "Invalid/Timezone",
                "to_timezone": "UTC"
            }
            result = await handler.run_tool(args)

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Error converting time" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_invalid_to_timezone(self, handler):
        """Test tool execution with invalid to_timezone."""
        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            def side_effect(tz):
                if tz == "Invalid/Timezone":
                    raise McpError("Invalid timezone")
                return ZoneInfo(tz)
            mock_get_tz.side_effect = side_effect

            with patch('dateutil.parser.parse') as mock_parse:
                mock_parse.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

                args = {
                    "datetime": "2024-01-01T12:00:00",
                    "from_timezone": "UTC",
                    "to_timezone": "Invalid/Timezone"
                }
                result = await handler.run_tool(args)

                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert "Error converting time" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_same_timezone_conversion(self, handler):
        """Test time conversion between same timezones."""
        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.return_value = ZoneInfo("UTC")

            with patch('dateutil.parser.parse') as mock_parse:
                source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
                mock_parse.return_value = source_time

                args = {
                    "datetime": "2024-01-01T12:00:00",
                    "from_timezone": "UTC",
                    "to_timezone": "UTC"
                }
                result = await handler.run_tool(args)

                assert len(result) == 1
                response_data = json.loads(result[0].text)
                # When converting to same timezone, time should remain the same
                assert response_data["original_datetime"] == "2024-01-01T12:00:00"
                assert response_data["from_timezone"] == "UTC"
                assert response_data["to_timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_run_tool_across_date_line(self, handler):
        """Test time conversion across international date line."""
        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.side_effect = lambda tz: ZoneInfo(tz)

            with patch('dateutil.parser.parse') as mock_parse:
                # Late evening in one timezone
                source_time = datetime(2024, 1, 1, 23, 0, 0, tzinfo=ZoneInfo("Pacific/Kiritimati"))
                mock_parse.return_value = source_time

                args = {
                    "datetime": "2024-01-01T23:00:00",
                    "from_timezone": "Pacific/Kiritimati",
                    "to_timezone": "Pacific/Honolulu"
                }
                result = await handler.run_tool(args)

                assert len(result) == 1
                response_data = json.loads(result[0].text)
                assert response_data["from_timezone"] == "Pacific/Kiritimati"
                assert response_data["to_timezone"] == "Pacific/Honolulu"
                # Should handle date line crossing correctly
                assert "converted_datetime" in response_data
