"""
Pytest configuration and fixtures for MCP weather server tests.
"""

import pytest
import asyncio
import subprocess
import json
import time
import sys
import os
from pathlib import Path
import httpx
from typing import Any, Dict, List




class MCPServerProcess:
    """Helper class to manage MCP server process for testing."""

    def __init__(self):
        self.process = None
        self.port = 8000
        self.base_url = f"http://localhost:{self.port}"

    async def start(self):
        """Start the MCP server process."""
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        server_script = project_root / "test_server.py"

        # Start the server process
        self.process = subprocess.Popen([
            sys.executable, str(server_script)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Wait for server to start up
        max_retries = 30
        for _ in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/health")
                    if response.status_code == 200:
                        break
            except (httpx.RequestError, httpx.HTTPStatusError):
                pass
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("MCP server failed to start")

    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Call a tool on the MCP server."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/call_tool",
                json={"name": name, "arguments": arguments}
            )
            response.raise_for_status()
            return response.json()["result"]

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools on the MCP server."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/list_tools")
            response.raise_for_status()
            return response.json()["tools"]


@pytest.fixture(scope="session")
async def mcp_server():
    """Fixture that provides a running MCP server process for testing."""
    server = MCPServerProcess()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
def mock_datetime():
    """Fixture to provide controlled datetime mocking."""
    from unittest.mock import patch
    from datetime import datetime
    from zoneinfo import ZoneInfo

    class MockDateTime:
        def __init__(self):
            self.fixed_time = None
            self.patches = []

        def set_fixed_time(self, dt: datetime):
            """Set a fixed time to return from datetime.now()."""
            self.fixed_time = dt

        def start_mocking(self):
            """Start datetime mocking."""
            if self.patches:
                self.stop_mocking()

            def mock_now(tz=None):
                if self.fixed_time and tz:
                    return self.fixed_time.astimezone(tz)
                elif self.fixed_time:
                    return self.fixed_time
                else:
                    return datetime.now(tz)

            patch_obj = patch('src.mcp_weather_server.tools.tools_time.datetime')
            mock_datetime = patch_obj.start()
            mock_datetime.now = mock_now
            self.patches.append(patch_obj)

        def stop_mocking(self):
            """Stop datetime mocking."""
            for patch_obj in self.patches:
                patch_obj.stop()
            self.patches.clear()

    mock_dt = MockDateTime()
    yield mock_dt
    mock_dt.stop_mocking()


@pytest.fixture
def mock_timezone():
    """Fixture to provide controlled timezone mocking."""
    from unittest.mock import patch
    from zoneinfo import ZoneInfo

    class MockTimezone:
        def __init__(self):
            self.patches = []
            self.zone_mapping = {}

        def add_zone(self, name: str, zone: ZoneInfo):
            """Add a timezone mapping."""
            self.zone_mapping[name] = zone

        def start_mocking(self):
            """Start timezone mocking."""
            if self.patches:
                self.stop_mocking()

            def mock_get_zoneinfo(name: str):
                if name in self.zone_mapping:
                    return self.zone_mapping[name]
                return ZoneInfo(name)

            patch_obj = patch('src.mcp_weather_server.utils.get_zoneinfo', side_effect=mock_get_zoneinfo)
            patch_obj.start()
            self.patches.append(patch_obj)

        def stop_mocking(self):
            """Stop timezone mocking."""
            for patch_obj in self.patches:
                patch_obj.stop()
            self.patches.clear()

    mock_tz = MockTimezone()
    yield mock_tz
    mock_tz.stop_mocking()


# Weather service fixtures
@pytest.fixture
def weather_service():
    """Create a WeatherService instance for testing."""
    from src.mcp_weather_server.tools.weather_service import WeatherService
    return WeatherService()


@pytest.fixture
def mock_geo_response():
    """Mock geocoding API response."""
    return {
        "results": [
            {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        ]
    }


@pytest.fixture
def mock_empty_geo_response():
    """Mock empty geocoding API response."""
    return {"results": []}


@pytest.fixture
def mock_weather_response():
    """Mock weather API response with all enhanced variables."""
    return {
        "hourly": {
            "time": [
                "2024-01-01T12:00",
                "2024-01-01T13:00"
            ],
            "temperature_2m": [20.0, 21.0],
            "relative_humidity_2m": [65, 66],
            "dew_point_2m": [13.0, 14.0],
            "weather_code": [0, 1],
            # Wind data
            "wind_speed_10m": [15.0, 16.0],
            "wind_direction_10m": [180, 185],
            "wind_gusts_10m": [25.0, 26.0],
            # Precipitation data
            "precipitation": [0.0, 0.1],
            "rain": [0.0, 0.1],
            "snowfall": [0.0, 0.0],
            "precipitation_probability": [10, 15],
            # Atmospheric data
            "pressure_msl": [1013.25, 1013.5],
            "cloud_cover": [25, 30],
            # Comfort & safety
            "uv_index": [5.0, 5.5],
            "apparent_temperature": [19.0, 20.0],
            "visibility": [10000, 9500]
        }
    }


@pytest.fixture
def mock_weather_range_response():
    """Mock weather range API response with all enhanced variables."""
    return {
        "hourly": {
            "time": [
                "2024-01-01T12:00",
                "2024-01-01T13:00",
                "2024-01-02T12:00",
                "2024-01-02T13:00"
            ],
            "temperature_2m": [20.0, 21.0, 22.0, 23.0],
            "relative_humidity_2m": [65, 66, 67, 68],
            "dew_point_2m": [13.0, 14.0, 15.0, 16.0],
            "weather_code": [0, 1, 0, 1],
            # Wind data
            "wind_speed_10m": [15.0, 16.0, 17.0, 18.0],
            "wind_direction_10m": [180, 185, 190, 195],
            "wind_gusts_10m": [25.0, 26.0, 27.0, 28.0],
            # Precipitation data
            "precipitation": [0.0, 0.1, 0.2, 0.0],
            "rain": [0.0, 0.1, 0.2, 0.0],
            "snowfall": [0.0, 0.0, 0.0, 0.0],
            "precipitation_probability": [10, 15, 20, 10],
            # Atmospheric data
            "pressure_msl": [1013.25, 1013.5, 1013.75, 1014.0],
            "cloud_cover": [25, 30, 35, 40],
            # Comfort & safety
            "uv_index": [5.0, 5.5, 6.0, 6.5],
            "apparent_temperature": [19.0, 20.0, 21.0, 22.0],
            "visibility": [10000, 9500, 9000, 8500]
        }
    }


@pytest.fixture
def sample_current_weather_data():
    """Sample current weather data for testing with all enhanced variables."""
    return {
        "city": "New York",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "time": "2024-01-01T12:00",
        "temperature_c": 25.0,
        "relative_humidity_percent": 70,
        "dew_point_c": 16.0,
        "weather_code": 1,
        "weather_description": "Mainly clear",
        # Wind data
        "wind_speed_kmh": 15.0,
        "wind_direction_degrees": 180,
        "wind_gusts_kmh": 25.0,
        # Precipitation data
        "precipitation_mm": 0.0,
        "rain_mm": 0.0,
        "snowfall_cm": 0.0,
        "precipitation_probability_percent": 10,
        # Atmospheric data
        "pressure_hpa": 1013.25,
        "cloud_cover_percent": 25,
        # Comfort & safety
        "uv_index": 5.0,
        "apparent_temperature_c": 24.0,
        "visibility_m": 10000
    }


@pytest.fixture
def sample_weather_range_data():
    """Sample weather range data for testing."""
    return {
        "city": "New York",
        "start_date": "2024-01-01",
        "end_date": "2024-01-02",
        "weather_data": [
            {
                "datetime": "2024-01-01T12:00:00",
                "temperature_c": 20.0,
                "relative_humidity_percent": 65,
                "dew_point_c": 13.0,
                "weather_code": 0,
                "weather_description": "Clear sky"
            },
            {
                "datetime": "2024-01-01T13:00:00",
                "temperature_c": 21.0,
                "relative_humidity_percent": 66,
                "dew_point_c": 14.0,
                "weather_code": 1,
                "weather_description": "Mainly clear"
            }
        ]
    }


# HTTP client mock fixtures
@pytest.fixture
def mock_successful_geo_client():
    """Mock successful geocoding client with enhanced weather data."""
    from unittest.mock import AsyncMock, Mock
    client = AsyncMock()

    def mock_get(url):
        response = Mock()
        response.status_code = 200

        if "geocoding-api" in url:
            response.json.return_value = {
                "results": [
                    {
                        "latitude": 40.7128,
                        "longitude": -74.0060
                    }
                ]
            }
        else:
            # Weather API response with enhanced variables
            response.json.return_value = {
                "hourly": {
                    "time": ["2024-01-01T12:00"],
                    "temperature_2m": [20.0],
                    "relative_humidity_2m": [65],
                    "dew_point_2m": [13.0],
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

    client.get.side_effect = mock_get
    return client


@pytest.fixture
def mock_failed_client():
    """Mock failed HTTP client."""
    from unittest.mock import AsyncMock, Mock
    client = AsyncMock()
    response = Mock()
    response.status_code = 500
    client.get.return_value = response
    return client


@pytest.fixture
def mock_network_error_client():
    """Mock network error HTTP client."""
    from unittest.mock import AsyncMock
    import httpx
    client = AsyncMock()
    client.get.side_effect = httpx.RequestError("Network error")
    return client
