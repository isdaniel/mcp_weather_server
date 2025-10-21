"""
Performance and load tests for MCP Weather Server.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
from src.mcp_weather_server.server import (
    register_all_tools,
    call_tool,
    tool_handlers
)


class TestPerformance:
    """Performance tests for the weather server."""

    def setup_method(self):
        """Setup for each test."""
        global tool_handlers
        tool_handlers.clear()
        register_all_tools()

    @pytest.mark.asyncio
    async def test_weather_request_performance(self):
        """Test that weather requests complete within reasonable time."""
        mock_geo_response = {
            "results": [{"latitude": 40.7128, "longitude": -74.0060}]
        }
        mock_weather_response = {
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
                start_time = time.time()
                result = await call_tool("get_current_weather", {"city": "New York"})
                end_time = time.time()

                # Request should complete in less than 1 second (mocked)
                assert end_time - start_time < 1.0
                assert len(result) == 1
                assert not result[0].text.startswith("Error:")

    @pytest.mark.asyncio
    async def test_concurrent_request_performance(self):
        """Test performance with multiple concurrent requests."""
        mock_geo_response = {
            "results": [{"latitude": 40.7128, "longitude": -74.0060}]
        }
        mock_weather_response = {
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
                # Create 10 concurrent requests
                tasks = [
                    call_tool("get_current_weather", {"city": f"City{i}"})
                    for i in range(10)
                ]

                start_time = time.time()
                results = await asyncio.gather(*tasks)
                end_time = time.time()

                # All requests should complete in reasonable time
                assert end_time - start_time < 2.0
                assert len(results) == 10

                # All requests should succeed
                for result in results:
                    assert len(result) == 1
                    assert not result[0].text.startswith("Error:")

    @pytest.mark.asyncio
    async def test_time_tool_performance(self):
        """Test performance of time-related tools."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

        with patch('src.mcp_weather_server.utils.get_zoneinfo') as mock_get_tz:
            mock_get_tz.return_value = ZoneInfo("UTC")
            with patch('src.mcp_weather_server.tools.tools_time.datetime') as mock_datetime:
                mock_datetime.now.return_value = fixed_time

                start_time = time.time()
                result = await call_tool("get_current_datetime", {"timezone_name": "UTC"})
                end_time = time.time()

                # Time tools should be very fast
                assert end_time - start_time < 0.1
                assert len(result) == 1
                assert not result[0].text.startswith("Error:")

    @pytest.mark.asyncio
    async def test_memory_usage_with_many_requests(self):
        """Test that memory usage doesn't grow excessively with many requests."""
        import gc
        import sys

        # Get initial memory usage (approximation)
        gc.collect()
        initial_objects = len(gc.get_objects())

        mock_geo_response = {
            "results": [{"latitude": 40.7128, "longitude": -74.0060}]
        }
        mock_weather_response = {
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
                # Make many sequential requests
                for i in range(50):
                    result = await call_tool("get_current_weather", {"city": f"City{i}"})
                    assert len(result) == 1
                    assert not result[0].text.startswith("Error:")

                # Force garbage collection and check memory
                gc.collect()
                final_objects = len(gc.get_objects())

                # Object count shouldn't grow dramatically
                # Allow some growth but not excessive (factor of 2)
                assert final_objects < initial_objects * 2


class TestLoadTesting:
    """Load testing scenarios."""

    def setup_method(self):
        """Setup for each test."""
        global tool_handlers
        tool_handlers.clear()
        register_all_tools()

    @pytest.mark.asyncio
    async def test_burst_load_handling(self):
        """Test handling of burst load (many requests at once)."""
        mock_geo_response = {
            "results": [{"latitude": 40.7128, "longitude": -74.0060}]
        }
        mock_weather_response = {
            "hourly": {
                "time": ["2024-01-01T12:00"],
                "temperature_2m": [20.0],
                "relative_humidity_2m": [60],
                "dew_point_2m": [12.0],
                "weather_code": [0]
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
                # Create a large burst of requests (simulate high load)
                burst_size = 25
                tasks = [
                    call_tool("get_current_weather", {"city": f"BurstCity{i}"})
                    for i in range(burst_size)
                ]

                start_time = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()

                # Check that most requests succeeded
                successful_results = [r for r in results if not isinstance(r, Exception)]
                error_results = [r for r in results if isinstance(r, Exception)]

                # At least 80% should succeed under load
                success_rate = len(successful_results) / len(results)
                assert success_rate >= 0.8, f"Success rate {success_rate} too low"

                # Total time should be reasonable even under load
                assert end_time - start_time < 5.0

    @pytest.mark.asyncio
    async def test_mixed_tool_load(self):
        """Test load with mixed tool types."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        # Setup weather mocks
        mock_geo_response = {
            "results": [{"latitude": 40.7128, "longitude": -74.0060}]
        }
        mock_weather_response = {
            "hourly": {
                "time": ["2024-01-01T12:00"],
                "temperature_2m": [20.0],
                "relative_humidity_2m": [60],
                "dew_point_2m": [12.0],
                "weather_code": [0]
            }
        }

        # Setup time mocks
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

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
                mock_get_tz.return_value = ZoneInfo("UTC")
                with patch('src.mcp_weather_server.tools.tools_time.datetime') as mock_datetime:
                    mock_datetime.now.return_value = fixed_time
                    with patch('src.mcp_weather_server.utils.get_closest_utc_index', return_value=0):

                        # Create mixed requests
                        tasks = []
                        for i in range(20):
                            if i % 3 == 0:
                                tasks.append(call_tool("get_current_weather", {"city": f"City{i}"}))
                            elif i % 3 == 1:
                                tasks.append(call_tool("get_current_datetime", {"timezone_name": "UTC"}))
                            else:
                                tasks.append(call_tool("get_timezone_info", {"timezone_name": "UTC"}))

                        start_time = time.time()
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        end_time = time.time()

                        # Check results
                        successful_results = [r for r in results if not isinstance(r, Exception)]
                        success_rate = len(successful_results) / len(results)

                        assert success_rate >= 0.9, f"Mixed load success rate {success_rate} too low"
                        assert end_time - start_time < 3.0
                        assert len(results) == 20


class TestStressConditions:
    """Stress testing under adverse conditions."""

    def setup_method(self):
        """Setup for each test."""
        global tool_handlers
        tool_handlers.clear()
        register_all_tools()

    @pytest.mark.asyncio
    async def test_high_error_rate_resilience(self):
        """Test resilience when external APIs have high error rates."""
        error_count = 0
        success_count = 0

        def mock_get_with_errors(url):
            nonlocal error_count, success_count
            response = Mock()

            # Simulate 30% error rate
            if (error_count + success_count) % 10 < 3:
                error_count += 1
                response.status_code = 500
            else:
                success_count += 1
                response.status_code = 200
                if "geocoding-api" in url:
                    response.json.return_value = {
                        "results": [{"latitude": 40.7128, "longitude": -74.0060}]
                    }
                else:
                    response.json.return_value = {
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
            return response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = mock_get_with_errors
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch('src.mcp_weather_server.utils.get_closest_utc_index', return_value=0):
                # Make requests despite high error rate
                tasks = [
                    call_tool("get_current_weather", {"city": f"ErrorTestCity{i}"})
                    for i in range(20)
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count successes and errors
                successful_results = []
                error_results = []

                for result in results:
                    if isinstance(result, Exception):
                        error_results.append(result)
                    else:
                        if result[0].text.startswith("Error:"):
                            error_results.append(result)
                        else:
                            successful_results.append(result)

                # Should handle errors gracefully without crashing
                assert len(results) == 20
                # Some should succeed despite errors
                assert len(successful_results) > 0
                # Error handling should be proper
                for error_result in error_results:
                    if not isinstance(error_result, Exception):
                        assert "Error:" in error_result[0].text
