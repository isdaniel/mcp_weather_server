"""
Unit tests for WeatherService class.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch
from src.mcp_weather_server.tools.weather_service import WeatherService


class TestWeatherService:
    """Test cases for WeatherService class."""

    @pytest.fixture
    def weather_service(self):
        """Create a WeatherService instance for testing."""
        return WeatherService()

    @pytest.mark.asyncio
    async def test_get_coordinates_success(
        self,
        weather_service,
        mock_successful_geo_client,
        mock_geo_response
    ):
        """Test successful coordinate retrieval."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_successful_geo_client

            lat, lon = await weather_service.get_coordinates("New York")

            assert lat == 40.7128
            assert lon == -74.0060
            mock_successful_geo_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_coordinates_api_error(
        self,
        weather_service,
        mock_failed_client
    ):
        """Test coordinate retrieval with API error."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_failed_client

            with pytest.raises(ValueError, match="Geocoding API returned status 500"):
                await weather_service.get_coordinates("Invalid City")

    @pytest.mark.asyncio
    async def test_get_coordinates_no_results(
        self,
        weather_service,
        mock_empty_geo_response
    ):
        """Test coordinate retrieval with no results."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_empty_geo_response
        mock_client.get.return_value = mock_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ValueError, match="No coordinates found for city: Unknown City"):
                await weather_service.get_coordinates("Unknown City")

    @pytest.mark.asyncio
    async def test_get_coordinates_network_error(
        self,
        weather_service,
        mock_network_error_client
    ):
        """Test coordinate retrieval with network error."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_network_error_client

            with pytest.raises(ValueError, match="Network error while fetching coordinates"):
                await weather_service.get_coordinates("Test City")

    @pytest.mark.asyncio
    async def test_get_current_weather_success(
        self,
        weather_service,
        mock_geo_response,
        mock_weather_response
    ):
        """Test successful current weather retrieval."""
        # Mock the coordinates call
        with patch.object(weather_service, 'get_coordinates', return_value=(40.7128, -74.0060)):
            # Mock the weather API call
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_weather_response
            mock_client.get.return_value = mock_response

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # Mock the utility function to return a predictable index
                with patch('src.mcp_weather_server.utils.get_closest_utc_index', return_value=1):
                    result = await weather_service.get_current_weather("New York")

                    assert result["city"] == "New York"
                    assert result["latitude"] == 40.7128
                    assert result["longitude"] == -74.0060
                    assert result["temperature_c"] == 21.0
                    assert result["relative_humidity_percent"] == 66
                    assert result["dew_point_c"] == 14.0
                    assert result["weather_code"] == 1
                    assert "Mainly clear" in result["weather_description"]

    @pytest.mark.asyncio
    async def test_get_current_weather_api_error(self, weather_service):
        """Test current weather retrieval with API error."""
        with patch.object(weather_service, 'get_coordinates', return_value=(40.7128, -74.0060)):
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 500
            mock_client.get.return_value = mock_response

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with pytest.raises(ValueError, match="Weather API returned status 500"):
                    await weather_service.get_current_weather("New York")

    @pytest.mark.asyncio
    async def test_get_weather_by_date_range_success(
        self,
        weather_service,
        mock_weather_range_response
    ):
        """Test successful weather range retrieval."""
        with patch.object(weather_service, 'get_coordinates', return_value=(40.7128, -74.0060)):
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_weather_range_response
            mock_client.get.return_value = mock_response

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_client

                result = await weather_service.get_weather_by_date_range(
                    "New York", "2024-01-01", "2024-01-02"
                )

                assert result["city"] == "New York"
                assert result["start_date"] == "2024-01-01"
                assert result["end_date"] == "2024-01-02"
                assert len(result["weather_data"]) == 4
                assert result["weather_data"][0]["temperature_c"] == 20.0
                assert result["weather_data"][1]["weather_description"] == "Mainly clear"

    @pytest.mark.asyncio
    async def test_get_weather_by_date_range_invalid_response(self, weather_service):
        """Test weather range retrieval with invalid response."""
        with patch.object(weather_service, 'get_coordinates', return_value=(40.7128, -74.0060)):
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"invalid": "response"}
            mock_client.get.return_value = mock_response

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with pytest.raises(ValueError, match="Invalid response format from weather API"):
                    await weather_service.get_weather_by_date_range(
                        "New York", "2024-01-01", "2024-01-02"
                    )

    def test_format_current_weather_response(
        self,
        weather_service,
        sample_current_weather_data
    ):
        """Test formatting of current weather response."""
        result = weather_service.format_current_weather_response(sample_current_weather_data)

        expected = (
            "The weather in New York is Mainly clear with a temperature of 25.0°C, "
            "relative humidity at 70%, and dew point at 16.0°C."
        )
        assert result == expected

    def test_format_weather_range_response(
        self,
        weather_service,
        sample_weather_range_data
    ):
        """Test formatting of weather range response."""
        with patch('src.mcp_weather_server.utils.format_get_weather_bytime') as mock_format:
            mock_format.return_value = "formatted response"

            result = weather_service.format_weather_range_response(sample_weather_range_data)

            assert result == "formatted response"
            mock_format.assert_called_once_with(sample_weather_range_data)

    @pytest.mark.asyncio
    async def test_get_coordinates_malformed_response(self, weather_service):
        """Test coordinate retrieval with malformed JSON response."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"invalid": "data"}]}
        mock_client.get.return_value = mock_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ValueError, match="Invalid response format from geocoding API"):
                await weather_service.get_coordinates("Test City")

    @pytest.mark.asyncio
    async def test_get_current_weather_network_error(self, weather_service):
        """Test current weather retrieval with network error."""
        with patch.object(weather_service, 'get_coordinates', return_value=(40.7128, -74.0060)):
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Network error")

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with pytest.raises(ValueError, match="Network error while fetching weather"):
                    await weather_service.get_current_weather("New York")

    @pytest.mark.asyncio
    async def test_get_weather_by_date_range_network_error(self, weather_service):
        """Test weather range retrieval with network error."""
        with patch.object(weather_service, 'get_coordinates', return_value=(40.7128, -74.0060)):
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Network error")

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with pytest.raises(ValueError, match="Network error while fetching weather"):
                    await weather_service.get_weather_by_date_range(
                        "New York", "2024-01-01", "2024-01-02"
                    )
