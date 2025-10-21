"""
Integration tests for the MCP Weather Server.
These tests verify end-to-end functionality with real-world scenarios.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch
from mcp.types import ErrorData
from mcp import McpError
from src.mcp_weather_server.server import (
    register_all_tools,
    list_tools,
    call_tool,
    tool_handlers
)


class TestWeatherIntegration:
    """Integration tests for weather functionality."""

    def setup_method(self):
        """Setup for each test."""
        global tool_handlers
        tool_handlers.clear()
        register_all_tools()

    @pytest.mark.asyncio
    async def test_current_weather_integration(self):
        """Test complete current weather workflow."""
        # Mock HTTP responses
        mock_geo_response = {
            "results": [{"latitude": 40.7128, "longitude": -74.0060}]
        }
        mock_weather_response = {
            "hourly": {
                "time": ["2024-01-01T12:00"],
                "temperature_2m": [22.5],
                "relative_humidity_2m": [65],
                "dew_point_2m": [15.2],
                "weather_code": [1],
                "wind_speed_10m": [15.0],
                "wind_direction_10m": [180],
                "wind_gusts_10m": [25.0],
                "precipitation": [0.0],
                "rain": [0.0],
                "snowfall": [0.0],
                "precipitation_probability": [10],
                "pressure_msl": [1013.25],
                "cloud_cover": [25],
                "uv_index": [5.0],
                "apparent_temperature": [21.0],
                "visibility": [10000]
            }
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()

            def mock_get(url):
                response = Mock()
                response.status_code = 200
                if "geocoding-api" in url:
                    response.json.return_value = mock_geo_response
                else:
                    response.json.return_value = mock_weather_response
                return response

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch('src.mcp_weather_server.utils.get_closest_utc_index', return_value=0):
                # Test the complete workflow
                tools = await list_tools()
                assert any(tool.name == "get_current_weather" for tool in tools)

                result = await call_tool("get_current_weather", {"city": "New York"})

                assert len(result) == 1
                response_text = result[0].text
                assert "New York" in response_text
                assert "22.5°C" in response_text
                assert "Mainly clear" in response_text

    @pytest.mark.asyncio
    async def test_weather_range_integration(self):
        """Test complete weather range workflow."""
        mock_geo_response = {
            "results": [{"latitude": 51.5074, "longitude": -0.1278}]
        }
        mock_weather_response = {
            "hourly": {
                "time": ["2024-01-01T00:00", "2024-01-01T12:00", "2024-01-02T00:00"],
                "temperature_2m": [8.0, 12.0, 6.0],
                "relative_humidity_2m": [85, 70, 90],
                "dew_point_2m": [6.0, 7.0, 4.5],
                "weather_code": [3, 1, 61],
                "wind_speed_10m": [12.0, 15.0, 18.0],
                "wind_direction_10m": [190, 180, 170],
                "wind_gusts_10m": [20.0, 25.0, 30.0],
                "precipitation": [0.0, 0.1, 1.5],
                "rain": [0.0, 0.1, 1.5],
                "snowfall": [0.0, 0.0, 0.0],
                "precipitation_probability": [20, 30, 70],
                "pressure_msl": [1012.0, 1013.0, 1010.0],
                "cloud_cover": [50, 30, 80],
                "uv_index": [1.0, 3.0, 2.0],
                "apparent_temperature": [7.0, 11.0, 5.0],
                "visibility": [7000, 9000, 5000]
            }
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()

            def mock_get(url):
                response = Mock()
                response.status_code = 200
                if "geocoding-api" in url:
                    response.json.return_value = mock_geo_response
                else:
                    response.json.return_value = mock_weather_response
                return response

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await call_tool("get_weather_byDateTimeRange", {
                "city": "London",
                "start_date": "2024-01-01",
                "end_date": "2024-01-02"
            })

            assert len(result) == 1
            response_text = result[0].text
            assert "London" in response_text
            assert "analyze" in response_text.lower()
            assert "2024-01-01" in response_text

    @pytest.mark.asyncio
    async def test_weather_details_integration(self):
        """Test weather details JSON output."""
        mock_geo_response = {
            "results": [{"latitude": 48.8566, "longitude": 2.3522}]
        }
        mock_weather_response = {
            "hourly": {
                "time": ["2024-01-01T14:00"],
                "temperature_2m": [18.5],
                "relative_humidity_2m": [72],
                "dew_point_2m": [13.8],
                "weather_code": [2],
                "wind_speed_10m": [14.0],
                "wind_direction_10m": [200],
                "wind_gusts_10m": [22.0],
                "precipitation": [0.0],
                "rain": [0.0],
                "snowfall": [0.0],
                "precipitation_probability": [15],
                "pressure_msl": [1015.0],
                "cloud_cover": [50],
                "uv_index": [4.0],
                "apparent_temperature": [17.5],
                "visibility": [9000]
            }
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()

            def mock_get(url):
                response = Mock()
                response.status_code = 200
                if "geocoding-api" in url:
                    response.json.return_value = mock_geo_response
                else:
                    response.json.return_value = mock_weather_response
                return response

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch('src.mcp_weather_server.utils.get_closest_utc_index', return_value=0):
                result = await call_tool("get_weather_details", {"city": "Paris"})

                assert len(result) == 1

                # Parse the JSON response
                weather_data = json.loads(result[0].text)
                assert weather_data["city"] == "Paris"
                assert weather_data["latitude"] == 48.8566
                assert weather_data["longitude"] == 2.3522
                assert weather_data["temperature_c"] == 18.5
                assert weather_data["weather_description"] == "Partly cloudy"


class TestTimeIntegration:
    """Integration tests for time functionality."""

    def setup_method(self):
        """Setup for each test."""
        global tool_handlers
        tool_handlers.clear()
        register_all_tools()

    @pytest.mark.asyncio
    async def test_current_datetime_integration(self):
        """Test complete current datetime workflow."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        fixed_time = datetime(2024, 6, 15, 10, 30, 45, tzinfo=ZoneInfo("America/New_York"))

        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.return_value = ZoneInfo("America/New_York")
            with patch('src.mcp_weather_server.tools.tools_time.datetime') as mock_datetime:
                mock_datetime.now.return_value = fixed_time

                result = await call_tool("get_current_datetime", {
                    "timezone_name": "America/New_York"
                })

                assert len(result) == 1
                time_data = json.loads(result[0].text)
                assert time_data["timezone"] == "America/New_York"
                assert "2024-06-15T10:30:45" in time_data["datetime"]

    @pytest.mark.asyncio
    async def test_timezone_info_integration(self):
        """Test complete timezone info workflow."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        fixed_time = datetime(2024, 12, 25, 15, 0, 0, tzinfo=ZoneInfo("Europe/London"))
        fixed_utc_time = datetime(2024, 12, 25, 15, 0, 0)  # UTC time without timezone

        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.return_value = ZoneInfo("Europe/London")
            with patch('src.mcp_weather_server.tools.tools_time.datetime') as mock_datetime:
                mock_datetime.now.return_value = fixed_time
                mock_datetime.utcnow.return_value = fixed_utc_time

                result = await call_tool("get_timezone_info", {
                    "timezone_name": "Europe/London"
                })

                assert len(result) == 1
                tz_data = json.loads(result[0].text)
                assert tz_data["timezone_name"] == "Europe/London"
                assert "current_local_time" in tz_data
                assert "utc_offset_hours" in tz_data

    @pytest.mark.asyncio
    async def test_time_conversion_integration(self):
        """Test complete time conversion workflow."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.side_effect = lambda tz: ZoneInfo(tz)

            with patch('dateutil.parser.parse') as mock_parse:
                source_time = datetime(2024, 7, 4, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
                mock_parse.return_value = source_time

                result = await call_tool("convert_time", {
                    "datetime_str": "2024-07-04T12:00:00",
                    "from_timezone": "UTC",
                    "to_timezone": "America/Los_Angeles"
                })

                assert len(result) == 1
                conversion_data = json.loads(result[0].text)
                assert "2024-07-04T12:00:00" in conversion_data["original_datetime"]
                assert conversion_data["original_timezone"] == "UTC"
                assert conversion_data["converted_timezone"] == "America/Los_Angeles"
                assert "converted_datetime" in conversion_data


class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""

    def setup_method(self):
        """Setup for each test."""
        global tool_handlers
        tool_handlers.clear()
        register_all_tools()

    @pytest.mark.asyncio
    async def test_invalid_city_error_handling(self):
        """Test error handling for invalid city names."""
        # Mock empty geocoding response
        mock_geo_response = {"results": []}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_geo_response
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await call_tool("get_current_weather", {"city": "NonexistentCity"})

            assert len(result) == 1
            assert "Error:" in result[0].text
            assert "coordinates" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test handling of API errors."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 500  # Server error
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await call_tool("get_current_weather", {"city": "TestCity"})

            assert len(result) == 1
            assert "Error:" in result[0].text
            assert "500" in result[0].text

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network errors."""
        import httpx

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Network unavailable")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await call_tool("get_current_weather", {"city": "TestCity"})

            assert len(result) == 1
            assert "Error:" in result[0].text
            assert "Network" in result[0].text or "network" in result[0].text

    @pytest.mark.asyncio
    async def test_invalid_timezone_error_handling(self):
        """Test error handling for invalid timezones."""
        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.side_effect = McpError(ErrorData(code=-1, message="Invalid timezone: BadTimezone"))

            result = await call_tool("get_current_datetime", {
                "timezone_name": "BadTimezone"
            })

            assert len(result) == 1
            assert "Error getting current time" in result[0].text

    @pytest.mark.asyncio
    async def test_missing_arguments_error_handling(self):
        """Test error handling for missing required arguments."""
        # Test weather tool without city
        result = await call_tool("get_current_weather", {})
        assert len(result) == 1
        assert "Missing required arguments: city" in result[0].text

        # Test time conversion without required fields
        result = await call_tool("convert_time", {"datetime": "2024-01-01T12:00:00"})
        assert len(result) == 1
        assert "Missing required arguments" in result[0].text


class TestConcurrentOperations:
    """Integration tests for concurrent operations."""

    def setup_method(self):
        """Setup for each test."""
        global tool_handlers
        tool_handlers.clear()
        register_all_tools()

    @pytest.mark.asyncio
    async def test_concurrent_weather_requests(self):
        """Test concurrent weather requests."""
        mock_responses = {
            "New York": {
                "geo": {"results": [{"latitude": 40.7128, "longitude": -74.0060}]},
                "weather": {
                    "hourly": {
                        "time": ["2024-01-01T12:00"],
                        "temperature_2m": [20.0],
                        "relative_humidity_2m": [60],
                        "dew_point_2m": [12.0],
                        "weather_code": [0],
                        "wind_speed_10m": [15.0],
                        "wind_direction_10m": [180],
                        "wind_gusts_10m": [25.0],
                        "precipitation": [0.0],
                        "rain": [0.0],
                        "snowfall": [0.0],
                        "precipitation_probability": [10],
                        "pressure_msl": [1013.25],
                        "cloud_cover": [25],
                        "uv_index": [5.0],
                        "apparent_temperature": [19.0],
                        "visibility": [10000]
                    }
                }
            },
            "London": {
                "geo": {"results": [{"latitude": 51.5074, "longitude": -0.1278}]},
                "weather": {
                    "hourly": {
                        "time": ["2024-01-01T12:00"],
                        "temperature_2m": [15.0],
                        "relative_humidity_2m": [80],
                        "dew_point_2m": [11.5],
                        "weather_code": [3],
                        "wind_speed_10m": [12.0],
                        "wind_direction_10m": [190],
                        "wind_gusts_10m": [20.0],
                        "precipitation": [0.0],
                        "rain": [0.0],
                        "snowfall": [0.0],
                        "precipitation_probability": [20],
                        "pressure_msl": [1012.0],
                        "cloud_cover": [50],
                        "uv_index": [2.0],
                        "apparent_temperature": [14.0],
                        "visibility": [8000]
                    }
                }
            }
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()

            def mock_get(url):
                response = Mock()
                response.status_code = 200

                # Default to New York for any unmapped requests
                default_geo = mock_responses["New York"]["geo"]
                default_weather = mock_responses["New York"]["weather"]

                # Determine which city based on the URL parameters
                if "name=New%20York" in url or "name=New+York" in url:
                    if "geocoding-api" in url:
                        response.json.return_value = mock_responses["New York"]["geo"]
                    else:
                        response.json.return_value = mock_responses["New York"]["weather"]
                elif "name=London" in url:
                    if "geocoding-api" in url:
                        response.json.return_value = mock_responses["London"]["geo"]
                    else:
                        response.json.return_value = mock_responses["London"]["weather"]
                elif "geocoding-api" in url:
                    # Default geocoding response
                    response.json.return_value = default_geo
                else:
                    # Default weather response based on coordinates
                    if "latitude=40.7128" in url:
                        response.json.return_value = mock_responses["New York"]["weather"]
                    elif "latitude=51.5074" in url:
                        response.json.return_value = mock_responses["London"]["weather"]
                    else:
                        response.json.return_value = default_weather
                return response

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch('src.mcp_weather_server.utils.get_closest_utc_index', return_value=0):
                # Run concurrent requests
                tasks = [
                    call_tool("get_current_weather", {"city": "New York"}),
                    call_tool("get_current_weather", {"city": "London"}),
                ]

                results = await asyncio.gather(*tasks)

                assert len(results) == 2

                # Check that both requests completed successfully
                for result in results:
                    assert len(result) == 1
                    assert not result[0].text.startswith("Error:")

                # Verify different cities returned different results
                result_texts = [result[0].text for result in results]
                assert any("New York" in text for text in result_texts)
                assert any("London" in text for text in result_texts)

    @pytest.mark.asyncio
    async def test_mixed_tool_concurrent_requests(self):
        """Test concurrent requests to different types of tools."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        # Setup mocks for weather
        mock_geo_response = {
            "results": [{"latitude": 35.6762, "longitude": 139.6503}]
        }
        mock_weather_response = {
            "hourly": {
                "time": ["2024-01-01T12:00"],
                "temperature_2m": [25.0],
                "relative_humidity_2m": [70],
                "dew_point_2m": [18.0],
                "weather_code": [1],
                "wind_speed_10m": [10.0],
                "wind_direction_10m": [170],
                "wind_gusts_10m": [18.0],
                "precipitation": [0.0],
                "rain": [0.0],
                "snowfall": [0.0],
                "precipitation_probability": [5],
                "pressure_msl": [1015.0],
                "cloud_cover": [20],
                "uv_index": [7.0],
                "apparent_temperature": [24.5],
                "visibility": [12000]
            }
        }

        # Setup mocks for time
        fixed_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()

            def mock_get(url):
                response = Mock()
                response.status_code = 200
                if "geocoding-api" in url:
                    response.json.return_value = mock_geo_response
                else:
                    response.json.return_value = mock_weather_response
                return response

            mock_client.get.side_effect = mock_get
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
                mock_get_tz.return_value = ZoneInfo("Asia/Tokyo")
                with patch('src.mcp_weather_server.tools.tools_time.datetime') as mock_datetime:
                    mock_datetime.now.return_value = fixed_time
                    with patch('src.mcp_weather_server.utils.get_closest_utc_index', return_value=0):

                        # Run concurrent requests to different tools
                        tasks = [
                            call_tool("get_current_weather", {"city": "Tokyo"}),
                            call_tool("get_current_datetime", {"timezone_name": "Asia/Tokyo"}),
                        ]

                        results = await asyncio.gather(*tasks)

                        assert len(results) == 2

                        # Verify weather result
                        weather_result = results[0]
                        assert len(weather_result) == 1
                        assert "Tokyo" in weather_result[0].text
                        assert "25.0°C" in weather_result[0].text

                        # Verify time result
                        time_result = results[1]
                        assert len(time_result) == 1
                        time_data = json.loads(time_result[0].text)
                        assert time_data["timezone"] == "Asia/Tokyo"
