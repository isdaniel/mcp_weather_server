"""
Weather service for handling all weather API interactions.
This separates the business logic from the tool handlers.
"""

import httpx
import logging
from typing import Dict, List, Tuple, Any
from datetime import datetime, timezone
from . import utils

logger = logging.getLogger("mcp-weather")


class WeatherService:
    """
    Service class for weather-related API interactions.

    This class encapsulates all weather API logic, making it reusable
    across different tool handlers and easier to test and maintain.
    """

    BASE_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
    BASE_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
        """Initialize the weather service."""
        pass

    async def get_coordinates(self, city: str) -> Tuple[float, float]:
        """
        Fetch the latitude and longitude for a given city using the Open-Meteo Geocoding API.

        Args:
            city: The name of the city to fetch coordinates for

        Returns:
            Tuple of (latitude, longitude)

        Raises:
            ValueError: If the coordinates cannot be retrieved
        """
        async with httpx.AsyncClient() as client:
            try:
                geo_response = await client.get(f"{self.BASE_GEO_URL}?name={city}")

                if geo_response.status_code != 200:
                    raise ValueError(f"Geocoding API returned status {geo_response.status_code}")

                geo_data = geo_response.json()
                if "results" not in geo_data or not geo_data["results"]:
                    raise ValueError(f"No coordinates found for city: {city}")

                result = geo_data["results"][0]
                return result["latitude"], result["longitude"]

            except httpx.RequestError as e:
                raise ValueError(f"Network error while fetching coordinates for {city}: {str(e)}")
            except (KeyError, IndexError) as e:
                raise ValueError(f"Invalid response format from geocoding API: {str(e)}")

    async def get_current_weather(self, city: str) -> Dict[str, Any]:
        """
        Get current weather information for a specified city.

        Args:
            city: The name of the city

        Returns:
            Dictionary containing current weather data

        Raises:
            ValueError: If weather data cannot be retrieved
        """
        try:
            latitude, longitude = await self.get_coordinates(city)

            # Build the weather API URL for current conditions with enhanced variables
            url = (
                f"{self.BASE_WEATHER_URL}"
                f"?latitude={latitude}&longitude={longitude}"
                f"&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,weather_code,"
                f"wind_speed_10m,wind_direction_10m,wind_gusts_10m,"
                f"precipitation,rain,snowfall,precipitation_probability,"
                f"pressure_msl,cloud_cover,uv_index,apparent_temperature,visibility"
                f"&timezone=GMT&forecast_days=1"
            )

            logger.info(f"Fetching current weather from: {url}")

            async with httpx.AsyncClient() as client:
                weather_response = await client.get(url)

                if weather_response.status_code != 200:
                    raise ValueError(f"Weather API returned status {weather_response.status_code}")

                weather_data = weather_response.json()

                # Find the current hour index
                current_index = utils.get_closest_utc_index(weather_data["hourly"]["time"])

                # Extract current weather data with all enhanced variables
                current_weather = {
                    "city": city,
                    "latitude": latitude,
                    "longitude": longitude,
                    "time": weather_data["hourly"]["time"][current_index],
                    "temperature_c": weather_data["hourly"]["temperature_2m"][current_index],
                    "relative_humidity_percent": weather_data["hourly"]["relative_humidity_2m"][current_index],
                    "dew_point_c": weather_data["hourly"]["dew_point_2m"][current_index],
                    "weather_code": weather_data["hourly"]["weather_code"][current_index],
                    "weather_description": utils.weather_descriptions.get(
                        weather_data["hourly"]["weather_code"][current_index],
                        "Unknown weather condition"
                    ),
                    # Wind data
                    "wind_speed_kmh": weather_data["hourly"]["wind_speed_10m"][current_index],
                    "wind_direction_degrees": weather_data["hourly"]["wind_direction_10m"][current_index],
                    "wind_gusts_kmh": weather_data["hourly"]["wind_gusts_10m"][current_index],
                    # Precipitation data
                    "precipitation_mm": weather_data["hourly"]["precipitation"][current_index],
                    "rain_mm": weather_data["hourly"]["rain"][current_index],
                    "snowfall_cm": weather_data["hourly"]["snowfall"][current_index],
                    "precipitation_probability_percent": weather_data["hourly"]["precipitation_probability"][current_index],
                    # Atmospheric data
                    "pressure_hpa": weather_data["hourly"]["pressure_msl"][current_index],
                    "cloud_cover_percent": weather_data["hourly"]["cloud_cover"][current_index],
                    # Comfort & safety
                    "uv_index": weather_data["hourly"]["uv_index"][current_index],
                    "apparent_temperature_c": weather_data["hourly"]["apparent_temperature"][current_index],
                    "visibility_m": weather_data["hourly"]["visibility"][current_index],
                }

                return current_weather

        except httpx.RequestError as e:
            raise ValueError(f"Network error while fetching weather for {city}: {str(e)}")
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid response format from weather API: {str(e)}")

    async def get_weather_by_date_range(
        self,
        city: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get weather information for a specified city between start and end dates.

        Args:
            city: The name of the city
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary containing weather data for the date range

        Raises:
            ValueError: If weather data cannot be retrieved
        """
        try:
            latitude, longitude = await self.get_coordinates(city)

            # Build the weather API URL for date range with enhanced variables
            url = (
                f"{self.BASE_WEATHER_URL}"
                f"?latitude={latitude}&longitude={longitude}"
                f"&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,weather_code,"
                f"wind_speed_10m,wind_direction_10m,wind_gusts_10m,"
                f"precipitation,rain,snowfall,precipitation_probability,"
                f"pressure_msl,cloud_cover,uv_index,apparent_temperature,visibility"
                f"&timezone=GMT&start_date={start_date}&end_date={end_date}"
            )

            logger.info(f"Fetching weather history from: {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(url)

                if response.status_code != 200:
                    raise ValueError(f"Weather API returned status {response.status_code}")

                data = response.json()

                # Process the hourly data with enhanced variables
                weather_data = []
                hourly = data["hourly"]
                data_length = len(hourly["time"])

                for i in range(data_length):
                    weather_data.append({
                        "time": hourly["time"][i],
                        "temperature_c": hourly["temperature_2m"][i],
                        "humidity_percent": hourly["relative_humidity_2m"][i],
                        "dew_point_c": hourly["dew_point_2m"][i],
                        "weather_code": hourly["weather_code"][i],
                        "weather_description": utils.weather_descriptions.get(
                            hourly["weather_code"][i], "Unknown weather condition"
                        ),
                        "wind_speed_kmh": hourly["wind_speed_10m"][i],
                        "wind_direction_degrees": hourly["wind_direction_10m"][i],
                        "wind_gusts_kmh": hourly["wind_gusts_10m"][i],
                        "precipitation_mm": hourly["precipitation"][i],
                        "rain_mm": hourly["rain"][i],
                        "snowfall_cm": hourly["snowfall"][i],
                        "precipitation_probability_percent": hourly["precipitation_probability"][i],
                        "pressure_hpa": hourly["pressure_msl"][i],
                        "cloud_cover_percent": hourly["cloud_cover"][i],
                        "uv_index": hourly["uv_index"][i],
                        "apparent_temperature_c": hourly["apparent_temperature"][i],
                        "visibility_m": hourly["visibility"][i],
                    })

                return {
                    "city": city,
                    "latitude": latitude,
                    "longitude": longitude,
                    "start_date": start_date,
                    "end_date": end_date,
                    "weather_data": weather_data
                }

        except httpx.RequestError as e:
            raise ValueError(f"Network error while fetching weather for {city}: {str(e)}")
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid response format from weather API: {str(e)}")

    def format_current_weather_response(self, weather_data: Dict[str, Any]) -> str:
        """
        Format current weather data into a human-readable string with enhanced variables.

        Args:
            weather_data: Weather data dictionary from get_current_weather

        Returns:
            Formatted weather description string
        """
        temp = weather_data['temperature_c']
        feels_like = weather_data.get('apparent_temperature_c', temp)

        # Temperature text with "feels like" if significantly different
        temp_text = f"temperature of {temp}°C"
        if abs(feels_like - temp) > 2:
            temp_text += f" (feels like {feels_like}°C)"

        # Get wind direction as compass direction
        wind_dir = self._degrees_to_compass(weather_data.get('wind_direction_degrees', 0))

        # Build the base weather description
        base_text = (
            f"The weather in {weather_data['city']} is {weather_data['weather_description']} "
            f"with a {temp_text}, "
            f"relative humidity at {weather_data['relative_humidity_percent']}%, "
            f"and dew point at {weather_data['dew_point_c']}°C. "
            f"Wind is blowing from the {wind_dir} at {weather_data['wind_speed_kmh']} km/h "
            f"with gusts up to {weather_data['wind_gusts_kmh']} km/h."
        )

        # Add precipitation info if present
        precip_mm = weather_data.get('precipitation_mm', 0)
        rain_mm = weather_data.get('rain_mm', 0)
        snow_cm = weather_data.get('snowfall_cm', 0)
        precip_prob = weather_data.get('precipitation_probability_percent', 0)

        if precip_mm > 0 or precip_prob > 20:
            if snow_cm > 0:
                base_text += f" Snowfall of {snow_cm} cm is occurring."
            elif rain_mm > 0:
                base_text += f" Rainfall of {rain_mm} mm is occurring."

            if precip_prob > 0:
                base_text += f" Precipitation probability is {precip_prob}%."

        # Add atmospheric data
        pressure = weather_data.get('pressure_hpa', 0)
        clouds = weather_data.get('cloud_cover_percent', 0)
        base_text += f" Atmospheric pressure is {pressure} hPa with {clouds}% cloud cover."

        # Add UV index warning if significant
        uv = weather_data.get('uv_index', 0)
        if uv > 3:
            uv_warning = self._get_uv_warning(uv)
            base_text += f" UV index is {uv:.1f} ({uv_warning})."

        # Add visibility
        visibility = weather_data.get('visibility_m', 0)
        if visibility > 0:
            visibility_km = visibility / 1000
            base_text += f" Visibility is {visibility_km:.1f} km."

        return base_text

    def format_weather_range_response(self, weather_data: Dict[str, Any]) -> str:
        """
        Format weather range data for analysis.

        Args:
            weather_data: Weather data dictionary from get_weather_by_date_range

        Returns:
            Formatted string ready for AI analysis
        """
        return utils.format_get_weather_bytime(weather_data)

    def _degrees_to_compass(self, degrees: float) -> str:
        """
        Convert wind direction in degrees to compass direction.

        Args:
            degrees: Wind direction in degrees (0-360)

        Returns:
            Compass direction string (N, NE, E, SE, S, SW, W, NW)
        """
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(degrees / 22.5) % 16
        return directions[index]

    def _get_uv_warning(self, uv_index: float) -> str:
        """
        Get UV index warning level.

        Args:
            uv_index: UV index value

        Returns:
            Warning level string
        """
        if uv_index < 3:
            return "Low"
        elif uv_index < 6:
            return "Moderate"
        elif uv_index < 8:
            return "High"
        elif uv_index < 11:
            return "Very High"
        else:
            return "Extreme"
