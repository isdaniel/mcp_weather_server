"""
Unit tests for weather tool handlers.
"""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from mcp.types import TextContent
from src.mcp_weather_server.tools.tools_weather import (
    GetCurrentWeatherToolHandler,
    GetWeatherByDateRangeToolHandler,
    GetWeatherDetailsToolHandler
)


class TestGetCurrentWeatherToolHandler:
    """Test cases for GetCurrentWeatherToolHandler."""

    @pytest.fixture
    def handler(self):
        """Create a GetCurrentWeatherToolHandler instance."""
        return GetCurrentWeatherToolHandler()

    def test_tool_description(self, handler):
        """Test the tool description is properly formatted."""
        description = handler.get_tool_description()

        assert description.name == "get_current_weather"
        assert "current weather" in description.description.lower()
        assert description.inputSchema["type"] == "object"
        assert "city" in description.inputSchema["properties"]
        assert description.inputSchema["required"] == ["city"]

    @pytest.mark.asyncio
    async def test_run_tool_success(self, handler, sample_current_weather_data):
        """Test successful tool execution."""
        # Mock the weather service
        mock_service = AsyncMock()
        mock_service.get_current_weather.return_value = sample_current_weather_data
        mock_service.format_current_weather_response.return_value = "Formatted weather response"
        handler.weather_service = mock_service

        args = {"city": "New York"}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].text == "Formatted weather response"
        mock_service.get_current_weather.assert_called_once_with("New York")
        mock_service.format_current_weather_response.assert_called_once_with(sample_current_weather_data)

    @pytest.mark.asyncio
    async def test_run_tool_missing_city(self, handler):
        """Test tool execution with missing city argument."""
        args = {}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Missing required arguments: city" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_weather_service_error(self, handler):
        """Test tool execution when weather service raises ValueError."""
        mock_service = AsyncMock()
        mock_service.get_current_weather.side_effect = ValueError("API error")
        handler.weather_service = mock_service

        args = {"city": "Invalid City"}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error: API error" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_unexpected_error(self, handler):
        """Test tool execution with unexpected error."""
        mock_service = AsyncMock()
        mock_service.get_current_weather.side_effect = Exception("Unexpected error")
        handler.weather_service = mock_service

        args = {"city": "Test City"}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unexpected error occurred: Unexpected error" in result[0].text


class TestGetWeatherByDateRangeToolHandler:
    """Test cases for GetWeatherByDateRangeToolHandler."""

    @pytest.fixture
    def handler(self):
        """Create a GetWeatherByDateRangeToolHandler instance."""
        return GetWeatherByDateRangeToolHandler()

    def test_tool_description(self, handler):
        """Test the tool description is properly formatted."""
        description = handler.get_tool_description()

        assert description.name == "get_weather_byDateTimeRange"
        assert "weather information" in description.description.lower()
        assert description.inputSchema["type"] == "object"
        required_fields = ["city", "start_date", "end_date"]
        for field in required_fields:
            assert field in description.inputSchema["properties"]
        assert set(description.inputSchema["required"]) == set(required_fields)

    @pytest.mark.asyncio
    async def test_run_tool_success(self, handler, sample_weather_range_data):
        """Test successful tool execution."""
        mock_service = AsyncMock()
        mock_service.get_weather_by_date_range.return_value = sample_weather_range_data
        mock_service.format_weather_range_response.return_value = "Formatted range response"
        handler.weather_service = mock_service

        args = {
            "city": "New York",
            "start_date": "2024-01-01",
            "end_date": "2024-01-02"
        }
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert result[0].text == "Formatted range response"
        mock_service.get_weather_by_date_range.assert_called_once_with(
            "New York", "2024-01-01", "2024-01-02"
        )

    @pytest.mark.asyncio
    async def test_run_tool_missing_required_args(self, handler):
        """Test tool execution with missing required arguments."""
        args = {"city": "New York"}  # Missing dates
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Missing required arguments" in result[0].text
        assert "start_date" in result[0].text
        assert "end_date" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_service_error(self, handler):
        """Test tool execution when weather service raises error."""
        mock_service = AsyncMock()
        mock_service.get_weather_by_date_range.side_effect = ValueError("Date range error")
        handler.weather_service = mock_service

        args = {
            "city": "Test City",
            "start_date": "invalid-date",
            "end_date": "2024-01-02"
        }
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error: Date range error" in result[0].text


class TestGetWeatherDetailsToolHandler:
    """Test cases for GetWeatherDetailsToolHandler."""

    @pytest.fixture
    def handler(self):
        """Create a GetWeatherDetailsToolHandler instance."""
        return GetWeatherDetailsToolHandler()

    def test_tool_description(self, handler):
        """Test the tool description is properly formatted."""
        description = handler.get_tool_description()

        assert description.name == "get_weather_details"
        assert "detailed weather information" in description.description.lower()
        assert description.inputSchema["type"] == "object"
        assert "city" in description.inputSchema["properties"]
        assert description.inputSchema["required"] == ["city"]

    @pytest.mark.asyncio
    async def test_run_tool_success(self, handler, sample_current_weather_data):
        """Test successful tool execution."""
        mock_service = AsyncMock()
        mock_service.get_current_weather.return_value = sample_current_weather_data
        handler.weather_service = mock_service

        args = {"city": "New York"}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        # Parse the JSON response to verify structure
        response_data = json.loads(result[0].text)
        assert response_data["city"] == "New York"
        assert response_data["temperature_c"] == 25.0
        assert response_data["weather_description"] == "Mainly clear"

        mock_service.get_current_weather.assert_called_once_with("New York")

    @pytest.mark.asyncio
    async def test_run_tool_missing_city(self, handler):
        """Test tool execution with missing city argument."""
        args = {}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Missing required arguments: city" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_service_error(self, handler):
        """Test tool execution when weather service raises error."""
        mock_service = AsyncMock()
        mock_service.get_current_weather.side_effect = ValueError("Service error")
        handler.weather_service = mock_service

        args = {"city": "Invalid City"}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error: Service error" in result[0].text

    @pytest.mark.asyncio
    async def test_run_tool_json_serialization_error(self, handler):
        """Test tool execution when JSON serialization fails."""
        mock_service = AsyncMock()
        # Create an object that can't be JSON serialized
        invalid_data = {"city": "Test", "invalid": object()}
        mock_service.get_current_weather.return_value = invalid_data
        handler.weather_service = mock_service

        args = {"city": "Test City"}
        result = await handler.run_tool(args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unexpected error occurred" in result[0].text


# Additional integration-style tests for tool handlers
class TestToolHandlerIntegration:
    """Integration tests for tool handlers with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_current_weather_end_to_end(self):
        """Test current weather tool with mocked HTTP responses."""
        handler = GetCurrentWeatherToolHandler()

        # Mock the entire HTTP call chain
        mock_geo_data = {
            "results": [{"latitude": 51.5074, "longitude": -0.1278}]
        }
        mock_weather_data = {
            "hourly": {
                "time": ["2024-01-01T12:00"],
                "temperature_2m": [15.5],
                "relative_humidity_2m": [80],
                "dew_point_2m": [12.0],
                "weather_code": [61]
            }
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()

            # Setup mock responses for geo and weather API calls
            geo_response = Mock()
            geo_response.status_code = 200
            geo_response.json.return_value = mock_geo_data

            weather_response = Mock()
            weather_response.status_code = 200
            weather_response.json.return_value = mock_weather_data

            # Return different responses for different URLs
            def mock_get(url):
                if "geocoding-api" in url:
                    return geo_response
                elif "api.open-meteo.com" in url:
                    return weather_response
                else:
                    raise ValueError(f"Unexpected URL: {url}")

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch('src.mcp_weather_server.utils.get_closest_utc_index', return_value=0):
                result = await handler.run_tool({"city": "London"})

                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert "London" in result[0].text
                assert "15.5°C" in result[0].text
                assert "Slight rain" in result[0].text

    @pytest.mark.asyncio
    async def test_weather_range_end_to_end(self):
        """Test weather range tool with mocked HTTP responses."""
        handler = GetWeatherByDateRangeToolHandler()

        mock_geo_data = {
            "results": [{"latitude": 48.8566, "longitude": 2.3522}]
        }
        mock_weather_data = {
            "hourly": {
                "time": ["2024-01-01T00:00", "2024-01-01T12:00"],
                "temperature_2m": [10.0, 15.0],
                "relative_humidity_2m": [90, 75],
                "dew_point_2m": [8.5, 11.0],
                "weather_code": [3, 1]
            }
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()

            geo_response = Mock()
            geo_response.status_code = 200
            geo_response.json.return_value = mock_geo_data

            weather_response = Mock()
            weather_response.status_code = 200
            weather_response.json.return_value = mock_weather_data

            def mock_get(url):
                if "geocoding-api" in url:
                    return geo_response
                else:
                    return weather_response

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            args = {
                "city": "Paris",
                "start_date": "2024-01-01",
                "end_date": "2024-01-01"
            }
            result = await handler.run_tool(args)

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            # The response should contain analysis prompt with JSON data
            assert "analyze" in result[0].text.lower()
            assert "Paris" in result[0].text
