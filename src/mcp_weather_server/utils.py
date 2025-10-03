
from datetime import datetime, timezone
import json
from typing import List
from zoneinfo import ZoneInfo
from mcp import McpError
from pydantic import BaseModel
from dateutil import parser

class TimeResult(BaseModel):
    timezone: str
    datetime: str

def get_zoneinfo(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except Exception as e:
        raise McpError(f"Invalid timezone: {str(e)}")

def format_get_weather_bytime(data_result) -> str:
    return f"""
Please analyze the above JSON weather forecast information and generate a report for me. Please note that the content is provided
city: city name
start_date: search weather start time
end_date: search weather end time
weather_data: weather data.
{json.dumps(data_result)}
        """

def get_closest_utc_index(hourly_times: List[str]) -> int:
    """
    Returns the index of the datetime in `hourly_times` closest to the current UTC time
    or a provided datetime.

    :param hourly_times: List of ISO 8601 time strings (UTC)
    :return: Index of the closest datetime in the list
    """

    current_time = datetime.now(timezone.utc)
    parsed_times = [
        parser.isoparse(t).replace(tzinfo=timezone.utc) if parser.isoparse(t).tzinfo is None
        else parser.isoparse(t).astimezone(timezone.utc)
        for t in hourly_times
    ]

    return min(range(len(parsed_times)), key=lambda i: abs(parsed_times[i] - current_time))

# Weather code descriptions (from Open-Meteo documentation)
weather_descriptions = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}
