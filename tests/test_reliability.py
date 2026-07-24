"""
Reliability tests: HTTP timeouts, connect retries, malformed JSON handling,
and guards against empty upstream data.
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch

import httpx

from src.mcp_weather_server import utils
from src.mcp_weather_server.tools.weather_service import (
    WeatherService,
    make_http_client,
    parse_json_response,
    REQUEST_TIMEOUT,
    TRANSPORT_RETRIES,
)
from src.mcp_weather_server.tools.air_quality_service import AirQualityService


class TestHttpClientConfiguration:
    def test_timeout_is_configured(self):
        client = make_http_client()
        assert client.timeout == REQUEST_TIMEOUT
        assert REQUEST_TIMEOUT.read == 10.0
        assert REQUEST_TIMEOUT.connect == 5.0

    def test_transport_retries_configured(self):
        assert TRANSPORT_RETRIES > 0
        transport = httpx.AsyncHTTPTransport(retries=TRANSPORT_RETRIES)
        assert transport._pool._retries == TRANSPORT_RETRIES


class TestParseJsonResponse:
    def test_valid_json(self):
        response = Mock()
        response.json.return_value = {"ok": True}
        assert parse_json_response(response, "test API") == {"ok": True}

    def test_malformed_json_raises_clear_error(self):
        response = Mock()
        response.json.side_effect = json.JSONDecodeError("Expecting value", "<html>", 0)
        with pytest.raises(ValueError, match="Invalid JSON response from test API"):
            parse_json_response(response, "test API")


class TestMalformedUpstreamResponses:
    @pytest.mark.asyncio
    async def test_geocoding_malformed_json(self):
        service = WeatherService()
        mock_client = AsyncMock()
        response = Mock()
        response.status_code = 200
        response.json.side_effect = json.JSONDecodeError("Expecting value", "<html>", 0)
        mock_client.get.return_value = response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client
            with pytest.raises(ValueError, match="Invalid JSON response from geocoding API"):
                await service.get_coordinates("Paris")

    @pytest.mark.asyncio
    async def test_air_quality_malformed_json(self):
        service = AirQualityService()
        mock_client = AsyncMock()
        response = Mock()
        response.status_code = 200
        response.json.side_effect = json.JSONDecodeError("Expecting value", "<html>", 0)
        mock_client.get.return_value = response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client
            with pytest.raises(ValueError, match="Invalid JSON response from air quality API"):
                await service.get_air_quality(45.5, -73.6)


class TestGetClosestUtcIndexGuards:
    def test_empty_list_raises_value_error(self):
        with pytest.raises(ValueError, match="No hourly time data"):
            utils.get_closest_utc_index([])

    def test_unparseable_time_raises_value_error(self):
        with pytest.raises(ValueError):
            utils.get_closest_utc_index(["not-a-date"])

    def test_normal_case_still_works(self):
        assert utils.get_closest_utc_index(["2024-01-01T00:00"]) == 0

    def test_empty_hourly_data_propagates_from_air_quality(self):
        service = AirQualityService()
        with pytest.raises(ValueError, match="No hourly time data"):
            service.get_current_air_quality_index({"hourly": {"time": []}})
