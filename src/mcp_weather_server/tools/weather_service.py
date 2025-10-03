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
            
            # Build the weather API URL for current conditions
            url = (
                f"{self.BASE_WEATHER_URL}"
                f"?latitude={latitude}&longitude={longitude}"
                f"&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,weather_code"
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
                
                # Extract current weather data
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
                    )
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
            
            # Build the weather API URL for date range
            url = (
                f"{self.BASE_WEATHER_URL}"
                f"?latitude={latitude}&longitude={longitude}"
                f"&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,weather_code"
                f"&timezone=GMT&start_date={start_date}&end_date={end_date}"
            )
            
            logger.info(f"Fetching weather history from: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    raise ValueError(f"Weather API returned status {response.status_code}")
                
                data = response.json()
                
                # Process the hourly data
                times = data["hourly"]["time"]
                temperatures = data["hourly"]["temperature_2m"]
                humidities = data["hourly"]["relative_humidity_2m"]
                dew_points = data["hourly"]["dew_point_2m"]
                weather_codes = data["hourly"]["weather_code"]
                
                weather_data = []
                for time, temp, humidity, dew_point, weather_code in zip(
                    times, temperatures, humidities, dew_points, weather_codes
                ):
                    weather_data.append({
                        "time": time,
                        "temperature_c": temp,
                        "humidity_percent": humidity,
                        "dew_point_c": dew_point,
                        "weather_code": weather_code,
                        "weather_description": utils.weather_descriptions.get(
                            weather_code, "Unknown weather condition"
                        )
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
        Format current weather data into a human-readable string.
        
        Args:
            weather_data: Weather data dictionary from get_current_weather
            
        Returns:
            Formatted weather description string
        """
        return (
            f"The weather in {weather_data['city']} is {weather_data['weather_description']} "
            f"with a temperature of {weather_data['temperature_c']}°C, "
            f"relative humidity at {weather_data['relative_humidity_percent']}%, "
            f"and dew point at {weather_data['dew_point_c']}°C."
        )
    
    def format_weather_range_response(self, weather_data: Dict[str, Any]) -> str:
        """
        Format weather range data for analysis.
        
        Args:
            weather_data: Weather data dictionary from get_weather_by_date_range
            
        Returns:
            Formatted string ready for AI analysis
        """
        return utils.format_get_weather_bytime(weather_data)
