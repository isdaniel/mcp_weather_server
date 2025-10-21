"""
Tests for air quality service functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.mcp_weather_server.tools.air_quality_service import AirQualityService


@pytest.fixture
def air_quality_service():
    """Create an AirQualityService instance for testing."""
    return AirQualityService()


@pytest.fixture
def mock_air_quality_response():
    """Mock air quality API response."""
    return {
        "hourly": {
            "time": ["2024-10-21T12:00", "2024-10-21T13:00", "2024-10-21T14:00"],
            "pm10": [25.5, 26.0, 24.8],
            "pm2_5": [12.3, 13.0, 11.8],
            "carbon_monoxide": [250.0, 255.0, 248.0],
            "nitrogen_dioxide": [18.5, 19.0, 17.8],
            "ozone": [45.2, 46.0, 44.8],
            "sulphur_dioxide": [2.5, 2.6, 2.4],
            "ammonia": [1.2, 1.3, 1.1],
            "dust": [8.5, 9.0, 8.2],
            "aerosol_optical_depth": [0.15, 0.16, 0.14]
        }
    }


class TestAirQualityService:
    """Test suite for air quality service functionality."""

    @pytest.mark.asyncio
    async def test_get_air_quality(self, air_quality_service, mock_air_quality_response):
        """Test getting air quality data."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_air_quality_response

            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.get = AsyncMock(return_value=mock_response)

            result = await air_quality_service.get_air_quality(
                35.6762, 139.6503, ["pm10", "pm2_5", "ozone"]
            )

            assert "hourly" in result
            assert "pm10" in result["hourly"]
            assert "pm2_5" in result["hourly"]
            assert "ozone" in result["hourly"]

    @pytest.mark.asyncio
    async def test_get_air_quality_default_vars(self, air_quality_service, mock_air_quality_response):
        """Test getting air quality with default variables."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_air_quality_response

            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.get = AsyncMock(return_value=mock_response)

            # Call without specifying variables (should use defaults)
            result = await air_quality_service.get_air_quality(35.6762, 139.6503)

            assert "hourly" in result

    @pytest.mark.asyncio
    async def test_get_air_quality_error_handling(self, air_quality_service):
        """Test error handling in air quality service."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500

            mock_instance = mock_client.return_value.__aenter__.return_value
            mock_instance.get = AsyncMock(return_value=mock_response)

            with pytest.raises(ValueError, match="Air Quality API returned status 500"):
                await air_quality_service.get_air_quality(35.6762, 139.6503)

    def test_get_current_air_quality_index(self, air_quality_service, mock_air_quality_response):
        """Test extracting current air quality index."""
        current_aq = air_quality_service.get_current_air_quality_index(mock_air_quality_response)

        assert "time" in current_aq
        assert "pm10" in current_aq
        assert "pm2_5" in current_aq
        assert "ozone" in current_aq
        assert isinstance(current_aq["pm10"], (int, float))

    def test_get_pm25_level(self, air_quality_service):
        """Test PM2.5 level classification."""
        assert air_quality_service._get_pm25_level(10) == "Good"
        assert air_quality_service._get_pm25_level(25) == "Moderate"
        assert air_quality_service._get_pm25_level(45) == "Unhealthy for Sensitive Groups"
        assert air_quality_service._get_pm25_level(100) == "Unhealthy"
        assert air_quality_service._get_pm25_level(200) == "Very Unhealthy"
        assert air_quality_service._get_pm25_level(300) == "Hazardous"

    def test_get_pm10_level(self, air_quality_service):
        """Test PM10 level classification."""
        assert air_quality_service._get_pm10_level(50) == "Good"
        assert air_quality_service._get_pm10_level(100) == "Moderate"
        assert air_quality_service._get_pm10_level(200) == "Unhealthy for Sensitive Groups"
        assert air_quality_service._get_pm10_level(300) == "Unhealthy"
        assert air_quality_service._get_pm10_level(400) == "Very Unhealthy"
        assert air_quality_service._get_pm10_level(500) == "Hazardous"

    def test_get_health_advice(self, air_quality_service):
        """Test health advice generation."""
        advice_good = air_quality_service._get_health_advice(10)
        assert "good" in advice_good.lower()
        assert "safe" in advice_good.lower()

        advice_moderate = air_quality_service._get_health_advice(25)
        assert "acceptable" in advice_moderate.lower()

        advice_unhealthy = air_quality_service._get_health_advice(100)
        assert "reduce" in advice_unhealthy.lower() or "avoid" in advice_unhealthy.lower()

        advice_hazardous = air_quality_service._get_health_advice(300)
        assert "avoid" in advice_hazardous.lower()
        assert "indoors" in advice_hazardous.lower()

    def test_format_air_quality_response(self, air_quality_service):
        """Test formatting air quality response."""
        aq_data = {
            "time": "2024-10-21T12:00",
            "pm2_5": 12.3,
            "pm10": 25.5,
            "ozone": 45.2,
            "nitrogen_dioxide": 18.5,
            "carbon_monoxide": 250.0
        }

        result = air_quality_service.format_air_quality_response(
            "Tokyo", 35.6762, 139.6503, aq_data
        )

        assert "Tokyo" in result
        assert "PM2.5" in result
        assert "12.3" in result
        assert "PM10" in result
        assert "25.5" in result
        assert "Good" in result  # PM2.5 12.3 is Good
        assert "Health Advice" in result

    def test_format_air_quality_response_all_pollutants(self, air_quality_service):
        """Test formatting with all pollutants."""
        aq_data = {
            "time": "2024-10-21T12:00",
            "pm2_5": 12.3,
            "pm10": 25.5,
            "ozone": 45.2,
            "nitrogen_dioxide": 18.5,
            "carbon_monoxide": 250.0,
            "sulphur_dioxide": 2.5,
            "ammonia": 1.2,
            "dust": 8.5,
            "aerosol_optical_depth": 0.15
        }

        result = air_quality_service.format_air_quality_response(
            "Beijing", 39.9042, 116.4074, aq_data
        )

        assert "Beijing" in result
        assert "PM2.5" in result
        assert "PM10" in result
        assert "Ozone" in result
        assert "Nitrogen Dioxide" in result
        assert "Carbon Monoxide" in result
        assert "Sulfur Dioxide" in result
        assert "Ammonia" in result
        assert "Dust" in result
        assert "Aerosol Optical Depth" in result

    def test_format_air_quality_unhealthy(self, air_quality_service):
        """Test formatting with unhealthy air quality."""
        aq_data = {
            "time": "2024-10-21T12:00",
            "pm2_5": 100.0,  # Unhealthy
            "pm10": 200.0
        }

        result = air_quality_service.format_air_quality_response(
            "Delhi", 28.6139, 77.2090, aq_data
        )

        assert "Delhi" in result
        assert "Unhealthy" in result
        assert "reduce" in result.lower() or "avoid" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
