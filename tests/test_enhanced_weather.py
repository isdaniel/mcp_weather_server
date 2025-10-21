"""
Tests for enhanced weather service functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.mcp_weather_server.tools.weather_service import WeatherService


@pytest.fixture
def weather_service():
    """Create a WeatherService instance for testing."""
    return WeatherService()


@pytest.fixture
def mock_enhanced_weather_response():
    """Mock enhanced weather API response."""
    return {
        "hourly": {
            "time": ["2024-10-21T12:00", "2024-10-21T13:00", "2024-10-21T14:00"],
            "temperature_2m": [22.5, 23.0, 23.5],
            "relative_humidity_2m": [65, 63, 61],
            "dew_point_2m": [15.5, 15.2, 15.0],
            "weather_code": [1, 1, 2],
            "wind_speed_10m": [12.5, 13.2, 14.0],
            "wind_direction_10m": [45, 50, 55],
            "wind_gusts_10m": [18.5, 19.0, 20.0],
            "precipitation": [0.0, 0.0, 0.2],
            "rain": [0.0, 0.0, 0.2],
            "snowfall": [0.0, 0.0, 0.0],
            "precipitation_probability": [10, 15, 25],
            "pressure_msl": [1013.2, 1013.0, 1012.8],
            "cloud_cover": [25, 30, 40],
            "uv_index": [5.5, 6.0, 5.8],
            "apparent_temperature": [23.0, 23.5, 24.0],
            "visibility": [10000, 9800, 9500]
        }
    }


class TestEnhancedWeatherService:
    """Test suite for enhanced weather service functionality."""

    @pytest.mark.asyncio
    async def test_get_current_weather_enhanced(self, weather_service, mock_enhanced_weather_response):
        """Test getting current weather with enhanced variables."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock geocoding response
            mock_geo_response = MagicMock()
            mock_geo_response.status_code = 200
            mock_geo_response.json.return_value = {
                "results": [{"latitude": 35.6762, "longitude": 139.6503}]
            }

            # Mock weather response
            mock_weather_response = MagicMock()
            mock_weather_response.status_code = 200
            mock_weather_response.json.return_value = mock_enhanced_weather_response

            # Setup async client mock
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.get = AsyncMock(side_effect=[mock_geo_response, mock_weather_response])

            # Test the method
            result = await weather_service.get_current_weather("Tokyo")

            # Verify all enhanced fields are present
            assert "city" in result
            assert result["city"] == "Tokyo"
            assert "temperature_c" in result
            assert "wind_speed_kmh" in result
            assert "wind_direction_degrees" in result
            assert "wind_gusts_kmh" in result
            assert "precipitation_mm" in result
            assert "rain_mm" in result
            assert "snowfall_cm" in result
            assert "precipitation_probability_percent" in result
            assert "pressure_hpa" in result
            assert "cloud_cover_percent" in result
            assert "uv_index" in result
            assert "apparent_temperature_c" in result
            assert "visibility_m" in result

    def test_degrees_to_compass(self, weather_service):
        """Test wind direction conversion from degrees to compass."""
        assert weather_service._degrees_to_compass(0) == "N"
        assert weather_service._degrees_to_compass(45) == "NE"
        assert weather_service._degrees_to_compass(90) == "E"
        assert weather_service._degrees_to_compass(135) == "SE"
        assert weather_service._degrees_to_compass(180) == "S"
        assert weather_service._degrees_to_compass(225) == "SW"
        assert weather_service._degrees_to_compass(270) == "W"
        assert weather_service._degrees_to_compass(315) == "NW"
        assert weather_service._degrees_to_compass(360) == "N"

    def test_get_uv_warning(self, weather_service):
        """Test UV index warning level."""
        assert weather_service._get_uv_warning(2) == "Low"
        assert weather_service._get_uv_warning(4) == "Moderate"
        assert weather_service._get_uv_warning(7) == "High"
        assert weather_service._get_uv_warning(9) == "Very High"
        assert weather_service._get_uv_warning(12) == "Extreme"

    def test_format_current_weather_enhanced(self, weather_service):
        """Test formatting of enhanced weather data."""
        weather_data = {
            "city": "Tokyo",
            "temperature_c": 22.5,
            "apparent_temperature_c": 23.0,
            "relative_humidity_percent": 65,
            "dew_point_c": 15.5,
            "weather_description": "Partly cloudy",
            "wind_speed_kmh": 12.5,
            "wind_direction_degrees": 45,
            "wind_gusts_kmh": 18.5,
            "precipitation_mm": 0.0,
            "rain_mm": 0.0,
            "snowfall_cm": 0.0,
            "precipitation_probability_percent": 10,
            "pressure_hpa": 1013.2,
            "cloud_cover_percent": 25,
            "uv_index": 5.5,
            "visibility_m": 10000
        }

        result = weather_service.format_current_weather_response(weather_data)

        # Check that all important info is in the response
        assert "Tokyo" in result
        assert "Partly cloudy" in result
        assert "22.5°C" in result
        assert "NE" in result  # 45 degrees = NE
        assert "12.5 km/h" in result
        assert "1013.2 hPa" in result
        assert "25% cloud cover" in result
        assert "UV index" in result
        assert "Moderate" in result  # UV 5.5 = Moderate
        assert "10.0 km" in result  # Visibility

    def test_format_weather_with_precipitation(self, weather_service):
        """Test formatting weather data with precipitation."""
        weather_data = {
            "city": "London",
            "temperature_c": 15.0,
            "apparent_temperature_c": 14.5,
            "relative_humidity_percent": 85,
            "dew_point_c": 12.5,
            "weather_description": "Light rain",
            "wind_speed_kmh": 20.0,
            "wind_direction_degrees": 270,
            "wind_gusts_kmh": 30.0,
            "precipitation_mm": 2.5,
            "rain_mm": 2.5,
            "snowfall_cm": 0.0,
            "precipitation_probability_percent": 80,
            "pressure_hpa": 1005.0,
            "cloud_cover_percent": 90,
            "uv_index": 1.0,
            "visibility_m": 5000
        }

        result = weather_service.format_current_weather_response(weather_data)

        assert "London" in result
        assert "Light rain" in result
        assert "2.5 mm" in result  # Rain amount
        assert "80%" in result  # Precipitation probability
        assert "W" in result  # 270 degrees = W

    def test_format_weather_with_snow(self, weather_service):
        """Test formatting weather data with snowfall."""
        weather_data = {
            "city": "Moscow",
            "temperature_c": -5.0,
            "apparent_temperature_c": -8.0,
            "relative_humidity_percent": 75,
            "dew_point_c": -7.0,
            "weather_description": "Snow",
            "wind_speed_kmh": 15.0,
            "wind_direction_degrees": 180,
            "wind_gusts_kmh": 22.0,
            "precipitation_mm": 3.0,
            "rain_mm": 0.0,
            "snowfall_cm": 3.0,
            "precipitation_probability_percent": 90,
            "pressure_hpa": 1020.0,
            "cloud_cover_percent": 100,
            "uv_index": 0.5,
            "visibility_m": 2000
        }

        result = weather_service.format_current_weather_response(weather_data)

        assert "Moscow" in result
        assert "Snow" in result
        assert "3.0 cm" in result  # Snowfall amount
        assert "feels like -8.0°C" in result  # Apparent temp significantly different
        assert "S" in result  # 180 degrees = S

    @pytest.mark.asyncio
    async def test_get_weather_by_date_range_enhanced(self, weather_service, mock_enhanced_weather_response):
        """Test getting weather by date range with enhanced variables."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock geocoding response
            mock_geo_response = MagicMock()
            mock_geo_response.status_code = 200
            mock_geo_response.json.return_value = {
                "results": [{"latitude": 40.7128, "longitude": -74.0060}]
            }

            # Mock weather response
            mock_weather_response = MagicMock()
            mock_weather_response.status_code = 200
            mock_weather_response.json.return_value = mock_enhanced_weather_response

            # Setup async client mock
            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.get = AsyncMock(side_effect=[mock_geo_response, mock_weather_response])

            # Test the method
            result = await weather_service.get_weather_by_date_range(
                "New York", "2024-10-21", "2024-10-22"
            )

            # Verify structure
            assert "city" in result
            assert "weather_data" in result
            assert len(result["weather_data"]) > 0

            # Check enhanced fields in weather data
            first_entry = result["weather_data"][0]
            assert "wind_speed_kmh" in first_entry
            assert "wind_direction_degrees" in first_entry
            assert "precipitation_mm" in first_entry
            assert "uv_index" in first_entry
            assert "visibility_m" in first_entry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
