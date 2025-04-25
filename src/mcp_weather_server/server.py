import httpx
import logging
from typing import Annotated, List
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from dateutil import parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-weather")

# Create an MCP server
mcp = FastMCP("Weather")

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

async def get_coordinates(client: httpx.AsyncClient, city: str) -> tuple[float, float]:
    """
    Fetch the latitude and longitude for a given city using the Open-Meteo Geocoding API.

    :param client: An instance of httpx.AsyncClient
    :param city: The name of the city to fetch coordinates for
    :return: A tuple (latitude, longitude)
    :raises ValueError: If the coordinates cannot be retrieved
    """
    geo_response = await client.get(
        f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
    )
    if geo_response.status_code != 200 or "results" not in geo_response.json():
        raise ValueError(f"Error: Could not retrieve coordinates for {city}.")

    geo_data = geo_response.json()["results"][0]
    return geo_data["latitude"], geo_data["longitude"]

def get_closest_utc_index(hourly_times: List[str]) -> int:
    """
    Returns the index of the datetime in `hourly_times` closest to the current UTC time
    or a provided datetime.

    :param hourly_times: List of ISO 8601 time strings (UTC)
    :return: Index of the closest datetime in the list
    """

    current_time = datetime.now(timezone.utc)
    logger.info(f"current UTC time: {current_time}")
    parsed_times = [
        parser.isoparse(t).replace(tzinfo=timezone.utc) if parser.isoparse(t).tzinfo is None
        else parser.isoparse(t).astimezone(timezone.utc)
        for t in hourly_times
    ]

    return min(range(len(parsed_times)), key=lambda i: abs(parsed_times[i] - current_time))

# Add a weather tool
@mcp.tool()
async def get_current_weather(city: Annotated[str ,Field(description="The name of the city to fetch weather information for, PLEASE NOTE English name only, if the parameter city isn't English please translate to English before invoking this function.")]) -> Annotated[str, Field(description="A string describing the current weather condition and temperature in the specified city, or an error message if the request fails.")]:

    """Get current weather information for a specified city.
    It extracts the current hour's temperature and weather code, maps
    the weather code to a human-readable description, and returns a formatted summary.
    """

    async with httpx.AsyncClient() as client:
        # Get coordinates using the Geocoding API
        try:
            try:
                latitude, longitude = await get_coordinates(client, city)
            except ValueError as e:
                return str(e)
            # Get weather data using the Forecast API
            url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,weather_code&timezone=GMT&forecast_days=1"
            logger.info(f"api: {url}")
            weather_response = await client.get(url)
            if weather_response.status_code != 200:
                return f"Error: Could not retrieve weather information for {city}."

            weather_data = weather_response.json()
            curIndex = get_closest_utc_index(weather_data["hourly"]["time"])
            temperature = weather_data["hourly"]["temperature_2m"][curIndex]
            weather_code = weather_data["hourly"]["weather_code"][curIndex]
            relative_humidity = weather_data["hourly"]["relative_humidity_2m"][curIndex]
            dew_point = weather_data["hourly"]["dew_point_2m"][curIndex]

            description = weather_descriptions.get(weather_code, "Unknown weather code")

            return f"The weather in {city} is {description} with a temperature of {temperature}°C, Relative humidity at 2 meters: {relative_humidity} %, Dew point temperature at 2 meters: {dew_point}"
        except Exception as e:
            logger.exception(f"API invoke error: {str(e)}")
            return f"API invoke error: {str(e)}"

@mcp.tool()
async def get_weather_byDateTimeRange(
    city: Annotated[str, Field(description="The name of the city to fetch weather information for, PLEASE NOTE English name only, if the parameter city isn't English please translate to English before invoking this function.")],
    start_date: Annotated[str, Field(description="Start date in format YYYY-MM-DD, please follow ISO 8601 format")],
    end_date: Annotated[str, Field(description="End date in format YYYY-MM-DD , please follow ISO 8601 format")]
) -> Annotated[str, Field(description="A summary of hourly weather data for the given city and date range.")]:
    """
    Get weather information for a specified city between start and end dates.
    """

    async with httpx.AsyncClient() as client:
        try:
            try:
                latitude, longitude = await get_coordinates(client, city)
            except ValueError as e:
                return str(e)

            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={latitude}&longitude={longitude}"
                f"&hourly=temperature_2m,relative_humidity_2m,dew_point_2m"
                f"&timezone=GMT&start_date={start_date}&end_date={end_date}"
            )
            logger.info(f"api: {url}")
            response = await client.get(url)

            if response.status_code != 200:
                return f"Error: Could not retrieve weather information for {city}."

            data = response.json()
            times = data["hourly"]["time"]
            temperatures = data["hourly"]["temperature_2m"]
            humidities = data["hourly"]["relative_humidity_2m"]
            dew_points = data["hourly"]["dew_point_2m"]

            summary_lines = [f"Hourly weather data for {city} from {start_date} to {end_date}:\n"]
            for time, temp, rh, dew in zip(times, temperatures, humidities, dew_points):
                summary_lines.append(f"{time} - Temp: {temp}°C, Humidity: {rh}%, Dew Point: {dew}°C")

            return "\n".join(summary_lines)

        except Exception as e:
            logger.exception(f"API invoke error: {str(e)}")
            return f"API invoke error: {str(e)}"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
