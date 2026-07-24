"""
Security-focused tests for input validation and query parameter handling.

Covers the fix for query parameter injection: user-controlled values must be
passed to httpx as `params` (so they get URL-encoded) and validated before use.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.mcp_weather_server.tools.weather_service import (
    WeatherService,
    validate_city,
    validate_date,
    MAX_CITY_LENGTH,
)
from src.mcp_weather_server.tools.air_quality_service import AirQualityService


class TestValidateCity:
    """Tests for the city name validator."""

    def test_valid_city(self):
        assert validate_city("Montreal") == "Montreal"

    def test_strips_whitespace(self):
        assert validate_city("  Paris  ") == "Paris"

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_city("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_city("   ")

    def test_non_string_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_city(12345)

    def test_none_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_city(None)

    def test_overly_long_city_rejected(self):
        with pytest.raises(ValueError, match="too long"):
            validate_city("A" * (MAX_CITY_LENGTH + 1))

    def test_max_length_city_accepted(self):
        assert validate_city("A" * MAX_CITY_LENGTH) == "A" * MAX_CITY_LENGTH


class TestValidateDate:
    """Tests for the date validator."""

    def test_valid_date(self):
        assert validate_date("2024-01-15", "start_date") == "2024-01-15"

    def test_bad_format_rejected(self):
        with pytest.raises(ValueError, match="start_date"):
            validate_date("15/01/2024", "start_date")

    def test_injection_attempt_rejected(self):
        with pytest.raises(ValueError, match="end_date"):
            validate_date("2024-01-15&forecast_days=16", "end_date")

    def test_non_string_rejected(self):
        with pytest.raises(ValueError, match="start_date"):
            validate_date(20240115, "start_date")

    def test_impossible_date_rejected(self):
        with pytest.raises(ValueError, match="start_date"):
            validate_date("2024-02-31", "start_date")


class TestQueryParameterInjection:
    """User input must reach httpx via `params`, never interpolated into the URL."""

    @pytest.mark.asyncio
    async def test_geocoding_uses_params_kwarg(self):
        service = WeatherService()
        mock_client = AsyncMock()
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"results": [{"latitude": 45.5, "longitude": -73.6}]}
        mock_client.get.return_value = response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client
            await service.get_coordinates("Montreal & Laval")

        args, kwargs = mock_client.get.call_args
        # URL is the bare endpoint, city goes through params for proper encoding
        assert args[0] == WeatherService.BASE_GEO_URL
        assert "?" not in args[0]
        assert kwargs["params"]["name"] == "Montreal & Laval"

    @pytest.mark.asyncio
    async def test_date_range_injection_rejected(self):
        service = WeatherService()
        with pytest.raises(ValueError, match="start_date"):
            await service.get_weather_by_date_range(
                "Paris", "2024-01-01&past_days=92", "2024-01-02"
            )

    @pytest.mark.asyncio
    async def test_start_after_end_rejected(self):
        service = WeatherService()
        with pytest.raises(ValueError, match="on or before"):
            await service.get_weather_by_date_range("Paris", "2024-02-01", "2024-01-01")

    @pytest.mark.asyncio
    async def test_empty_city_rejected_before_network_call(self):
        service = WeatherService()
        with patch("httpx.AsyncClient") as mock_client_class:
            with pytest.raises(ValueError, match="non-empty"):
                await service.get_coordinates("")
            mock_client_class.return_value.__aenter__.assert_not_called()


class TestAirQualityVariableAllowlist:
    """Air quality hourly variables must match the server-side allowlist."""

    @pytest.mark.asyncio
    async def test_invalid_variable_rejected(self):
        service = AirQualityService()
        with pytest.raises(ValueError, match="Invalid air quality variables"):
            await service.get_air_quality(45.5, -73.6, ["pm2_5", "evil&param=1"])

    @pytest.mark.asyncio
    async def test_valid_variables_use_params_kwarg(self):
        service = AirQualityService()
        mock_client = AsyncMock()
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"hourly": {"time": [], "pm2_5": []}}
        mock_client.get.return_value = response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client
            await service.get_air_quality(45.5, -73.6, ["pm2_5", "pm10"])

        args, kwargs = mock_client.get.call_args
        assert args[0] == AirQualityService.BASE_AIR_QUALITY_URL
        assert kwargs["params"]["hourly"] == "pm2_5,pm10"
