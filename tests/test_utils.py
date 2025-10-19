"""
Unit tests for utility functions.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, Mock
from zoneinfo import ZoneInfo
from mcp import McpError
from src.mcp_weather_server.utils import (
    TimeResult,
    get_zoneinfo,
    format_get_weather_bytime,
    get_closest_utc_index,
    weather_descriptions
)


class TestTimeResult:
    """Test cases for TimeResult model."""

    def test_time_result_creation(self):
        """Test TimeResult model creation."""
        time_result = TimeResult(
            timezone="America/New_York",
            datetime="2024-01-01T15:30:45"
        )

        assert time_result.timezone == "America/New_York"
        assert time_result.datetime == "2024-01-01T15:30:45"

    def test_time_result_dict(self):
        """Test TimeResult conversion to dictionary."""
        time_result = TimeResult(
            timezone="UTC",
            datetime="2024-01-01T12:00:00"
        )

        result_dict = time_result.model_dump()
        assert result_dict["timezone"] == "UTC"
        assert result_dict["datetime"] == "2024-01-01T12:00:00"


class TestGetZoneinfo:
    """Test cases for get_zoneinfo function."""

    def test_get_zoneinfo_valid_timezone(self):
        """Test get_zoneinfo with valid timezone."""
        tz = get_zoneinfo("America/New_York")
        assert isinstance(tz, ZoneInfo)
        assert str(tz) == "America/New_York"

    def test_get_zoneinfo_utc(self):
        """Test get_zoneinfo with UTC timezone."""
        tz = get_zoneinfo("UTC")
        assert isinstance(tz, ZoneInfo)
        assert str(tz) == "UTC"

    def test_get_zoneinfo_invalid_timezone(self):
        """Test get_zoneinfo with invalid timezone."""
        with pytest.raises(McpError, match="Invalid timezone"):
            get_zoneinfo("Invalid/Timezone")

    def test_get_zoneinfo_empty_string(self):
        """Test get_zoneinfo with empty string."""
        with pytest.raises(McpError, match="Invalid timezone"):
            get_zoneinfo("")

    def test_get_zoneinfo_none(self):
        """Test get_zoneinfo with None."""
        with pytest.raises(McpError, match="Invalid timezone"):
            get_zoneinfo(None)

    def test_get_zoneinfo_common_timezones_real(self):
        """Test get_zoneinfo with common timezones without mocks (integration test)."""
        # Test the exact timezones that were causing issues in Windows
        common_timezones = [
            "UTC",
            "America/New_York",  # The exact failing case from the original issue
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
        ]

        for timezone_name in common_timezones:
            tz = get_zoneinfo(timezone_name)
            assert isinstance(tz, ZoneInfo)
            assert str(tz) == timezone_name

            # Verify we can actually use the timezone
            current_time = datetime.now(tz)
            assert current_time.tzinfo is not None

            # Verify the timezone can be used for time calculations
            iso_string = current_time.isoformat()
            assert len(iso_string) > 0

    def test_get_zoneinfo_windows_problematic_cases(self):
        """Test cases that specifically failed on Windows without tzdata."""
        # These are the exact cases from the original error logs
        problematic_cases = [
            "America/New_York",  # Original failing case
            "UTC",               # Also failed in the logs
        ]

        for timezone_name in problematic_cases:
            # This should NOT raise ZoneInfoNotFoundError if tzdata is properly installed
            try:
                tz = get_zoneinfo(timezone_name)
                assert isinstance(tz, ZoneInfo)

                # Test that we can create datetime objects with this timezone
                test_time = datetime(2024, 10, 19, 12, 0, 0, tzinfo=tz)
                assert test_time.tzinfo == tz

            except Exception as e:
                pytest.fail(f"Failed to load timezone {timezone_name} - this suggests tzdata is not properly installed: {e}")

    def test_get_zoneinfo_dst_transitions(self):
        """Test timezone handling across DST transitions."""
        ny_tz = get_zoneinfo("America/New_York")

        # Test dates around DST transitions
        # Spring forward (March)
        spring_before_dst = datetime(2024, 3, 9, 12, 0, 0, tzinfo=ny_tz)
        spring_after_dst = datetime(2024, 3, 11, 12, 0, 0, tzinfo=ny_tz)

        # Fall back (November)
        fall_before_dst = datetime(2024, 11, 2, 12, 0, 0, tzinfo=ny_tz)
        fall_after_dst = datetime(2024, 11, 4, 12, 0, 0, tzinfo=ny_tz)

        # All should work without errors
        for dt in [spring_before_dst, spring_after_dst, fall_before_dst, fall_after_dst]:
            assert dt.tzinfo == ny_tz
            # Should be able to get UTC offset
            offset = dt.utcoffset()
            assert offset is not None


class TestFormatGetWeatherBytime:
    """Test cases for format_get_weather_bytime function."""

    def test_format_get_weather_bytime_basic(self):
        """Test basic formatting of weather data."""
        weather_data = {
            "city": "New York",
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "weather_data": [
                {
                    "time": "2024-01-01T12:00",
                    "temperature_c": 25.0,
                    "humidity_percent": 70,
                    "weather_description": "Clear sky"
                }
            ]
        }

        result = format_get_weather_bytime(weather_data)

        assert "analyze" in result.lower()
        assert "New York" in result
        assert "2024-01-01" in result
        assert "2024-01-02" in result
        assert "weather_data" in result

    def test_format_get_weather_bytime_empty_data(self):
        """Test formatting with empty weather data."""
        weather_data = {
            "city": "Test City",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01",
            "weather_data": []
        }

        result = format_get_weather_bytime(weather_data)

        assert "Test City" in result
        assert "weather_data" in result
        assert "[]" in result

    def test_format_get_weather_bytime_complex_data(self):
        """Test formatting with complex weather data."""
        weather_data = {
            "city": "London",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "start_date": "2024-01-01",
            "end_date": "2024-01-03",
            "weather_data": [
                {
                    "time": "2024-01-01T00:00",
                    "temperature_c": 15.0,
                    "humidity_percent": 80,
                    "dew_point_c": 11.5,
                    "weather_code": 61,
                    "weather_description": "Slight rain"
                },
                {
                    "time": "2024-01-01T12:00",
                    "temperature_c": 18.0,
                    "humidity_percent": 75,
                    "dew_point_c": 13.0,
                    "weather_code": 1,
                    "weather_description": "Mainly clear"
                }
            ]
        }

        result = format_get_weather_bytime(weather_data)

        assert "London" in result
        assert "51.5074" in result
        assert "-0.1278" in result
        assert "Slight rain" in result
        assert "Mainly clear" in result


class TestGetClosestUtcIndex:
    """Test cases for get_closest_utc_index function."""

    def test_get_closest_utc_index_exact_match(self):
        """Test finding index when current time matches exactly."""
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        hourly_times = [
            "2024-01-01T10:00:00Z",
            "2024-01-01T11:00:00Z",
            "2024-01-01T12:00:00Z",  # This should match
            "2024-01-01T13:00:00Z",
            "2024-01-01T14:00:00Z"
        ]

        with patch('src.mcp_weather_server.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            index = get_closest_utc_index(hourly_times)
            assert index == 2

    def test_get_closest_utc_index_closest_before(self):
        """Test finding closest index when current time is between hours."""
        current_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        hourly_times = [
            "2024-01-01T10:00:00Z",
            "2024-01-01T11:00:00Z",
            "2024-01-01T12:00:00Z",  # This should be closest (30 min away)
            "2024-01-01T13:00:00Z",  # This is also 30 min away, but 12:00 comes first
            "2024-01-01T14:00:00Z"
        ]

        with patch('src.mcp_weather_server.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            index = get_closest_utc_index(hourly_times)
            assert index == 2

    def test_get_closest_utc_index_closest_after(self):
        """Test finding closest index when current time is closer to next hour."""
        current_time = datetime(2024, 1, 1, 12, 35, 0, tzinfo=timezone.utc)
        hourly_times = [
            "2024-01-01T10:00:00Z",
            "2024-01-01T11:00:00Z",
            "2024-01-01T12:00:00Z",  # 35 min away
            "2024-01-01T13:00:00Z",  # 25 min away - closer
            "2024-01-01T14:00:00Z"
        ]

        with patch('src.mcp_weather_server.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            index = get_closest_utc_index(hourly_times)
            assert index == 3

    def test_get_closest_utc_index_single_time(self):
        """Test with single time entry."""
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        hourly_times = ["2024-01-01T15:00:00Z"]

        with patch('src.mcp_weather_server.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            index = get_closest_utc_index(hourly_times)
            assert index == 0

    def test_get_closest_utc_index_empty_list(self):
        """Test with empty time list."""
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        hourly_times = []

        with patch('src.mcp_weather_server.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            with pytest.raises(ValueError):
                get_closest_utc_index(hourly_times)

    def test_get_closest_utc_index_different_timezones(self):
        """Test with times in different timezone formats."""
        current_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        hourly_times = [
            "2024-01-01T10:00:00",     # No timezone, should be treated as UTC
            "2024-01-01T11:00:00Z",    # UTC
            "2024-01-01T12:00:00+00:00",  # UTC with offset
            "2024-01-01T08:00:00-04:00",  # EST (12:00 UTC)
            "2024-01-01T14:00:00Z"
        ]

        with patch('src.mcp_weather_server.utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Should find one of the 12:00 UTC equivalent times
            index = get_closest_utc_index(hourly_times)
            assert index in [2, 3]  # Either the +00:00 or -04:00 versions


class TestWeatherDescriptions:
    """Test cases for weather descriptions dictionary."""

    def test_weather_descriptions_coverage(self):
        """Test that weather_descriptions contains expected codes."""
        # Test some common weather codes
        assert weather_descriptions[0] == "Clear sky"
        assert weather_descriptions[1] == "Mainly clear"
        assert weather_descriptions[2] == "Partly cloudy"
        assert weather_descriptions[3] == "Overcast"

        # Test precipitation codes
        assert weather_descriptions[61] == "Slight rain"
        assert weather_descriptions[63] == "Moderate rain"
        assert weather_descriptions[65] == "Heavy rain"

        # Test snow codes
        assert weather_descriptions[71] == "Slight snow fall"
        assert weather_descriptions[73] == "Moderate snow fall"
        assert weather_descriptions[75] == "Heavy snow fall"

        # Test severe weather
        assert weather_descriptions[95] == "Thunderstorm"
        assert weather_descriptions[99] == "Thunderstorm with heavy hail"

    def test_weather_descriptions_unknown_code(self):
        """Test behavior with unknown weather codes."""
        # Unknown codes should not be in the dictionary
        assert 999 not in weather_descriptions
        assert -1 not in weather_descriptions

    def test_weather_descriptions_fog_codes(self):
        """Test fog-related weather codes."""
        assert weather_descriptions[45] == "Fog"
        assert weather_descriptions[48] == "Depositing rime fog"

    def test_weather_descriptions_drizzle_codes(self):
        """Test drizzle-related weather codes."""
        assert weather_descriptions[51] == "Light drizzle"
        assert weather_descriptions[53] == "Moderate drizzle"
        assert weather_descriptions[55] == "Dense drizzle"
        assert weather_descriptions[56] == "Light freezing drizzle"
        assert weather_descriptions[57] == "Dense freezing drizzle"

    def test_weather_descriptions_shower_codes(self):
        """Test shower-related weather codes."""
        assert weather_descriptions[80] == "Slight rain showers"
        assert weather_descriptions[81] == "Moderate rain showers"
        assert weather_descriptions[82] == "Violent rain showers"
        assert weather_descriptions[85] == "Slight snow showers"
        assert weather_descriptions[86] == "Heavy snow showers"

    def test_weather_descriptions_hail_codes(self):
        """Test hail-related weather codes."""
        assert weather_descriptions[96] == "Thunderstorm with slight hail"
        assert weather_descriptions[99] == "Thunderstorm with heavy hail"

    def test_weather_descriptions_completeness(self):
        """Test that all expected weather codes are present."""
        expected_codes = [
            0, 1, 2, 3, 45, 48,
            51, 53, 55, 56, 57,
            61, 63, 65, 66, 67,
            71, 73, 75, 77,
            80, 81, 82, 85, 86,
            95, 96, 99
        ]

        for code in expected_codes:
            assert code in weather_descriptions, f"Weather code {code} is missing"
            assert isinstance(weather_descriptions[code], str)
            assert len(weather_descriptions[code]) > 0
