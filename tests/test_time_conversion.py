"""
Regression tests for convert_time timezone semantics.

A trailing 'Z' means UTC; previously such timestamps were incorrectly
stamped with from_timezone, shifting the converted result.
"""

import json
import pytest

from src.mcp_weather_server.tools.tools_time import (
    ConvertTimeToolHandler,
    GetTimeZoneInfoToolHandler,
)


@pytest.fixture
def convert_handler():
    return ConvertTimeToolHandler()


class TestConvertTimeZuluSuffix:
    @pytest.mark.asyncio
    async def test_z_suffix_is_treated_as_utc(self, convert_handler):
        result = await convert_handler.run_tool({
            "datetime_str": "2024-01-15T12:00:00Z",
            "from_timezone": "America/New_York",
            "to_timezone": "Europe/Paris",
        })

        payload = json.loads(result[0].text)
        # 12:00 UTC is 13:00 in Paris (UTC+1 in January), NOT 18:00
        # (which would mean the Z timestamp was wrongly read as New York time)
        assert payload["converted_datetime"] == "2024-01-15T13:00:00+01:00"
        assert payload["original_timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_naive_input_uses_from_timezone(self, convert_handler):
        result = await convert_handler.run_tool({
            "datetime_str": "2024-01-15T12:00:00",
            "from_timezone": "America/New_York",
            "to_timezone": "Europe/Paris",
        })

        payload = json.loads(result[0].text)
        # 12:00 in New York (UTC-5) is 18:00 in Paris (UTC+1)
        assert payload["converted_datetime"] == "2024-01-15T18:00:00+01:00"
        assert payload["original_timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_explicit_offset_is_preserved(self, convert_handler):
        result = await convert_handler.run_tool({
            "datetime_str": "2024-01-15T12:00:00+00:00",
            "from_timezone": "America/New_York",
            "to_timezone": "Europe/Paris",
        })

        payload = json.loads(result[0].text)
        # The +00:00 offset in the string wins over from_timezone
        assert payload["converted_datetime"] == "2024-01-15T13:00:00+01:00"

    @pytest.mark.asyncio
    async def test_dst_z_suffix(self, convert_handler):
        result = await convert_handler.run_tool({
            "datetime_str": "2024-07-15T12:00:00Z",
            "from_timezone": "America/New_York",
            "to_timezone": "Europe/Paris",
        })

        payload = json.loads(result[0].text)
        # In July, Paris is UTC+2
        assert payload["converted_datetime"] == "2024-07-15T14:00:00+02:00"


class TestGetTimezoneInfoUtcTime:
    @pytest.mark.asyncio
    async def test_utc_time_is_timezone_aware(self):
        handler = GetTimeZoneInfoToolHandler()
        result = await handler.run_tool({"timezone_name": "America/Montreal"})

        payload = json.loads(result[0].text)
        # datetime.now(timezone.utc) produces an aware ISO string with offset
        assert payload["current_utc_time"].endswith("+00:00")
        assert payload["timezone_name"] == "America/Montreal"
