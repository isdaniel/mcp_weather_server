"""
Integration tests for timezone dependency functionality.
These tests verify that tzdata is properly installed and working without mocks.
"""

import pytest
import platform
from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones
from src.mcp_weather_server.utils import get_zoneinfo


class TestTimezoneDependency:
    """Test cases for timezone dependency functionality."""

    def test_tzdata_is_available(self):
        """Test that tzdata module is available and working."""
        try:
            import tzdata
            assert tzdata is not None
        except ImportError:
            pytest.fail("tzdata module is not available - this is required for timezone support on Windows")

    def test_zoneinfo_has_timezones(self):
        """Test that zoneinfo has access to timezone data."""
        timezones = available_timezones()
        assert len(timezones) > 0, "No timezones available - tzdata may not be properly installed"

        # Check for some common timezones that should always be available
        required_timezones = {
            'UTC',
            'America/New_York',
            'Europe/London',
            'Asia/Tokyo',
            'Australia/Sydney'
        }

        missing_timezones = required_timezones - timezones
        assert not missing_timezones, f"Missing required timezones: {missing_timezones}"

    def test_america_new_york_timezone_works(self):
        """Test that America/New_York timezone specifically works (the failing case)."""
        try:
            tz = ZoneInfo("America/New_York")
            now = datetime.now(tz)
            assert now.tzinfo is not None
            assert str(now.tzinfo) == "America/New_York"
        except Exception as e:
            pytest.fail(f"America/New_York timezone failed to load: {e}")

    def test_utc_timezone_works(self):
        """Test that UTC timezone works (another commonly failing case)."""
        try:
            tz = ZoneInfo("UTC")
            now = datetime.now(tz)
            assert now.tzinfo is not None
            assert str(now.tzinfo) == "UTC"
        except Exception as e:
            pytest.fail(f"UTC timezone failed to load: {e}")

    def test_utils_get_zoneinfo_real_timezones(self):
        """Test utils.get_zoneinfo with real timezone data (no mocks)."""
        # Test common timezones that were causing issues
        test_timezones = [
            "UTC",
            "America/New_York",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Australia/Sydney"
        ]

        for timezone_name in test_timezones:
            try:
                tz = get_zoneinfo(timezone_name)
                assert isinstance(tz, ZoneInfo)
                assert str(tz) == timezone_name
            except Exception as e:
                pytest.fail(f"get_zoneinfo failed for {timezone_name}: {e}")

    def test_timezone_conversion_across_dst(self):
        """Test timezone conversion across daylight saving time boundaries."""
        try:
            # Test conversion during DST and non-DST periods
            summer_date = datetime(2024, 7, 15, 12, 0, 0)  # Summer (DST)
            winter_date = datetime(2024, 1, 15, 12, 0, 0)   # Winter (no DST)

            ny_tz = ZoneInfo("America/New_York")
            utc_tz = ZoneInfo("UTC")

            # Summer conversion
            summer_ny = summer_date.replace(tzinfo=ny_tz)
            summer_utc = summer_ny.astimezone(utc_tz)
            assert summer_utc.tzinfo == utc_tz

            # Winter conversion
            winter_ny = winter_date.replace(tzinfo=ny_tz)
            winter_utc = winter_ny.astimezone(utc_tz)
            assert winter_utc.tzinfo == utc_tz

            # The UTC offset should be different between summer and winter
            summer_offset = summer_ny.utcoffset().total_seconds()
            winter_offset = winter_ny.utcoffset().total_seconds()
            assert summer_offset != winter_offset, "DST offset difference not detected"

        except Exception as e:
            pytest.fail(f"DST timezone conversion failed: {e}")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific timezone test")
    def test_windows_timezone_support(self):
        """Test that timezone support works specifically on Windows."""
        # This test will only run on Windows where the original issue occurred
        try:
            # Test the exact case that was failing
            tz = ZoneInfo("America/New_York")
            current_time = datetime.now(tz)

            # Verify we can format it properly
            iso_time = current_time.isoformat()
            assert "America/New_York" in str(current_time.tzinfo) or "-" in iso_time or "+" in iso_time

        except Exception as e:
            pytest.fail(f"Windows timezone support failed: {e}")

    def test_timezone_data_completeness(self):
        """Test that we have a reasonable amount of timezone data."""
        timezones = available_timezones()

        # Should have at least 400 timezones (IANA database has ~600)
        assert len(timezones) >= 400, f"Too few timezones available: {len(timezones)}"

        # Check for major continents/regions
        continents = ['America', 'Europe', 'Asia', 'Africa', 'Australia', 'Pacific']
        for continent in continents:
            continent_zones = [tz for tz in timezones if tz.startswith(continent + '/')]
            assert len(continent_zones) > 0, f"No timezones found for {continent}"

    def test_timezone_edge_cases(self):
        """Test edge cases that might expose missing timezone data."""
        edge_case_timezones = [
            "UTC",
            "GMT",
            "US/Eastern",     # Legacy but should work
            "US/Pacific",     # Legacy but should work
            "Europe/Dublin",  # Has unique DST behavior
            "Antarctica/McMurdo",  # Unusual timezone
            "Pacific/Kiritimati",  # +14 UTC (ahead of date line)
            "Pacific/Honolulu",    # -10 UTC
        ]

        for timezone_name in edge_case_timezones:
            if timezone_name in available_timezones():
                try:
                    tz = get_zoneinfo(timezone_name)
                    current_time = datetime.now(tz)
                    assert current_time.tzinfo is not None
                except Exception as e:
                    pytest.fail(f"Edge case timezone {timezone_name} failed: {e}")

    def test_invalid_timezone_handling(self):
        """Test that invalid timezones are properly handled."""
        invalid_timezones = [
            "Invalid/Timezone",
            "NotReal/Place",
            "America/FakeCity",
            "",
            "UTC+5",  # This format is not supported by zoneinfo
        ]

        for invalid_tz in invalid_timezones:
            with pytest.raises(Exception):
                get_zoneinfo(invalid_tz)

    def test_timezone_abbreviations(self):
        """Test that timezone abbreviations work correctly."""
        test_cases = [
            ("America/New_York", ["EST", "EDT"]),  # Eastern Time
            ("America/Los_Angeles", ["PST", "PDT"]),  # Pacific Time
            ("Europe/London", ["GMT", "BST"]),  # British Time
            ("UTC", ["UTC"]),  # UTC should always be UTC
        ]

        for timezone_name, expected_abbrevs in test_cases:
            try:
                tz = ZoneInfo(timezone_name)

                # Test winter time (January)
                winter_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tz)
                winter_abbrev = winter_time.strftime("%Z")

                # Test summer time (July)
                summer_time = datetime(2024, 7, 15, 12, 0, 0, tzinfo=tz)
                summer_abbrev = summer_time.strftime("%Z")

                # At least one of the abbreviations should match expected
                all_abbrevs = {winter_abbrev, summer_abbrev}
                assert any(abbrev in expected_abbrevs for abbrev in all_abbrevs), \
                    f"No expected abbreviation found for {timezone_name}. Got: {all_abbrevs}, Expected: {expected_abbrevs}"

            except Exception as e:
                pytest.fail(f"Timezone abbreviation test failed for {timezone_name}: {e}")
