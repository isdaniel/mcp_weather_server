"""
Tests for air quality tool handlers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.mcp_weather_server.tools.tools_air_quality import (
    GetAirQualityToolHandler,
    GetAirQualityDetailsToolHandler
)


@pytest.fixture
def mock_air_quality_data():
    """Mock air quality data."""
    return {
        "hourly": {
            "time": ["2024-10-21T12:00", "2024-10-21T13:00"],
            "pm2_5": [12.3, 13.0],
            "pm10": [25.5, 26.0],
            "ozone": [45.2, 46.0]
        }
    }


@pytest.fixture
def mock_current_aq():
    """Mock current air quality data."""
    return {
        "time": "2024-10-21T12:00",
        "pm2_5": 12.3,
        "pm10": 25.5,
        "ozone": 45.2
    }


class TestGetAirQualityToolHandler:
    """Test suite for GetAirQualityToolHandler."""

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_air_quality_data, mock_current_aq):
        """Test successful air quality retrieval."""
        handler = GetAirQualityToolHandler()

        # Mock the service methods
        handler.air_quality_service.get_air_quality = AsyncMock(return_value=mock_air_quality_data)
        handler.air_quality_service.get_current_air_quality_index = MagicMock(return_value=mock_current_aq)
        handler.weather_service.get_coordinates = AsyncMock(return_value=(35.6762, 139.6503))

        result = await handler.run_tool({"city": "Tokyo"})

        assert len(result) == 1
        # Check for comprehensive format indicators
        assert "Please analyze the following JSON air quality information" in result[0].text
        assert "FIELD DESCRIPTIONS" in result[0].text
        assert "Tokyo" in result[0].text
        assert "pm2_5" in result[0].text
        handler.air_quality_service.get_air_quality.assert_called_once()
        handler.air_quality_service.get_current_air_quality_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_custom_variables(self, mock_air_quality_data, mock_current_aq):
        """Test with custom air quality variables."""
        handler = GetAirQualityToolHandler()

        handler.air_quality_service.get_air_quality = AsyncMock(return_value=mock_air_quality_data)
        handler.air_quality_service.get_current_air_quality_index = MagicMock(return_value=mock_current_aq)
        handler.weather_service.get_coordinates = AsyncMock(return_value=(39.9042, 116.4074))

        variables = ["pm2_5", "pm10", "carbon_monoxide"]
        result = await handler.run_tool({
            "city": "Beijing",
            "variables": variables
        })

        assert len(result) == 1
        # Check for comprehensive format
        assert "Beijing" in result[0].text
        assert "FIELD DESCRIPTIONS" in result[0].text
        handler.air_quality_service.get_air_quality.assert_called_once_with(
            39.9042, 116.4074, variables
        )

    @pytest.mark.asyncio
    async def test_execute_error_handling(self):
        """Test error handling in tool handler."""
        handler = GetAirQualityToolHandler()

        handler.weather_service.get_coordinates = AsyncMock(
            side_effect=ValueError("API Error")
        )

        result = await handler.run_tool({"city": "Tokyo"})

        assert len(result) == 1
        assert "error" in result[0].text.lower()
        assert "API Error" in result[0].text

    def test_tool_definition(self):
        """Test tool definition structure."""
        handler = GetAirQualityToolHandler()
        tool = handler.get_tool_description()

        assert tool.name == "get_air_quality"
        assert "air quality" in tool.description.lower()
        assert "inputSchema" in tool.model_dump()

        schema = tool.inputSchema
        assert "city" in schema["properties"]
        assert "variables" in schema["properties"]

        # Check required fields
        assert "city" in schema["required"]


class TestGetAirQualityDetailsToolHandler:
    """Test suite for GetAirQualityDetailsToolHandler."""

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_air_quality_data, mock_current_aq):
        """Test successful detailed air quality retrieval."""
        handler = GetAirQualityDetailsToolHandler()

        handler.air_quality_service.get_air_quality = AsyncMock(return_value=mock_air_quality_data)
        handler.air_quality_service.get_current_air_quality_index = MagicMock(return_value=mock_current_aq)
        handler.weather_service.get_coordinates = AsyncMock(return_value=(35.6762, 139.6503))

        result = await handler.run_tool({"city": "Tokyo"})

        assert len(result) == 1
        import json
        result_json = json.loads(result[0].text)

        assert result_json["city"] == "Tokyo"
        assert result_json["latitude"] == 35.6762
        assert result_json["longitude"] == 139.6503
        assert "current_air_quality" in result_json
        assert "full_data" in result_json

    @pytest.mark.asyncio
    async def test_execute_json_structure(self, mock_air_quality_data, mock_current_aq):
        """Test JSON structure of detailed output."""
        handler = GetAirQualityDetailsToolHandler()

        handler.air_quality_service.get_air_quality = AsyncMock(return_value=mock_air_quality_data)
        handler.air_quality_service.get_current_air_quality_index = MagicMock(return_value=mock_current_aq)
        handler.weather_service.get_coordinates = AsyncMock(return_value=(39.9042, 116.4074))

        result = await handler.run_tool({"city": "Beijing"})

        import json
        data = json.loads(result[0].text)

        assert "city" in data
        assert "latitude" in data
        assert "longitude" in data
        assert "current_air_quality" in data
        assert "full_data" in data

        assert "time" in data["current_air_quality"]
        assert "pm2_5" in data["current_air_quality"]
        assert "hourly" in data["full_data"]

    @pytest.mark.asyncio
    async def test_execute_with_custom_variables(self, mock_air_quality_data, mock_current_aq):
        """Test detailed output with custom variables."""
        handler = GetAirQualityDetailsToolHandler()

        handler.air_quality_service.get_air_quality = AsyncMock(return_value=mock_air_quality_data)
        handler.air_quality_service.get_current_air_quality_index = MagicMock(return_value=mock_current_aq)
        handler.weather_service.get_coordinates = AsyncMock(return_value=(28.6139, 77.2090))

        variables = ["pm2_5", "pm10"]
        result = await handler.run_tool({
            "city": "Delhi",
            "variables": variables
        })

        handler.air_quality_service.get_air_quality.assert_called_once_with(
            28.6139, 77.2090, variables
        )

        import json
        data = json.loads(result[0].text)
        assert data["city"] == "Delhi"

    @pytest.mark.asyncio
    async def test_execute_error_handling(self):
        """Test error handling in detailed tool handler."""
        handler = GetAirQualityDetailsToolHandler()

        handler.weather_service.get_coordinates = AsyncMock(
            side_effect=Exception("Network error")
        )

        result = await handler.run_tool({"city": "Tokyo"})

        assert len(result) == 1
        assert "error" in result[0].text.lower()
        assert "Network error" in result[0].text

    def test_tool_definition(self):
        """Test detailed tool definition structure."""
        handler = GetAirQualityDetailsToolHandler()
        tool = handler.get_tool_description()

        assert tool.name == "get_air_quality_details"
        assert "air quality" in tool.description.lower()
        assert "json" in tool.description.lower()

        schema = tool.inputSchema
        assert "city" in schema["properties"]
        assert "variables" in schema["properties"]

        # Check that variables is an array
        assert schema["properties"]["variables"]["type"] == "array"
        assert "items" in schema["properties"]["variables"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
