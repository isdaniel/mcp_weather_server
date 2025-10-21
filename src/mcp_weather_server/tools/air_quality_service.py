"""
Air Quality service for handling air quality API interactions.
This service provides access to air quality data including PM2.5, PM10, ozone, and other pollutants.
"""

import httpx
import logging
from typing import Dict, List, Any
from . import utils

logger = logging.getLogger("mcp-weather")


class AirQualityService:
    """
    Service class for air quality API interactions.

    This class encapsulates all air quality API logic, making it reusable
    across different tool handlers and easier to test and maintain.
    """

    BASE_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def __init__(self):
        """Initialize the air quality service."""
        pass

    async def get_air_quality(
        self,
        latitude: float,
        longitude: float,
        hourly_vars: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get air quality data for given coordinates.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            hourly_vars: List of hourly variables to retrieve

        Returns:
            Air quality data dictionary

        Raises:
            ValueError: If air quality data cannot be retrieved
        """
        if hourly_vars is None:
            hourly_vars = ["pm10", "pm2_5", "ozone", "nitrogen_dioxide", "carbon_monoxide"]

        hourly_str = ",".join(hourly_vars)

        url = (
            f"{self.BASE_AIR_QUALITY_URL}"
            f"?latitude={latitude}&longitude={longitude}"
            f"&hourly={hourly_str}"
            f"&timezone=GMT"
        )

        logger.info(f"Fetching air quality data from: {url}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)

                if response.status_code != 200:
                    raise ValueError(f"Air Quality API returned status {response.status_code}")

                return response.json()

        except httpx.RequestError as e:
            raise ValueError(f"Network error while fetching air quality data: {str(e)}")
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid response format from air quality API: {str(e)}")

    def get_current_air_quality_index(self, aq_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract current air quality data from the hourly data.

        Args:
            aq_data: Air quality data from get_air_quality

        Returns:
            Dictionary with current air quality values
        """
        # Find the current hour index
        current_index = utils.get_closest_utc_index(aq_data["hourly"]["time"])

        current_aq = {
            "time": aq_data["hourly"]["time"][current_index],
        }

        # Extract all available pollutant values
        hourly = aq_data["hourly"]
        for key, values in hourly.items():
            if key != "time" and isinstance(values, list) and len(values) > current_index:
                current_aq[key] = values[current_index]

        return current_aq

    def format_air_quality_response(
        self,
        city: str,
        latitude: float,
        longitude: float,
        aq_data: Dict[str, Any]
    ) -> str:
        """
        Format air quality data into a human-readable string.

        Args:
            city: City name
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            aq_data: Current air quality data

        Returns:
            Formatted air quality description string
        """
        response_parts = [f"Air quality in {city} (lat: {latitude:.2f}, lon: {longitude:.2f}):"]

        # PM2.5 (most important for health)
        if "pm2_5" in aq_data:
            pm25 = aq_data["pm2_5"]
            pm25_level = self._get_pm25_level(pm25)
            response_parts.append(f"PM2.5: {pm25:.1f} μg/m³ ({pm25_level})")

        # PM10
        if "pm10" in aq_data:
            pm10 = aq_data["pm10"]
            pm10_level = self._get_pm10_level(pm10)
            response_parts.append(f"PM10: {pm10:.1f} μg/m³ ({pm10_level})")

        # Ozone
        if "ozone" in aq_data:
            ozone = aq_data["ozone"]
            response_parts.append(f"Ozone (O3): {ozone:.1f} μg/m³")

        # Nitrogen Dioxide
        if "nitrogen_dioxide" in aq_data:
            no2 = aq_data["nitrogen_dioxide"]
            response_parts.append(f"Nitrogen Dioxide (NO2): {no2:.1f} μg/m³")

        # Carbon Monoxide
        if "carbon_monoxide" in aq_data:
            co = aq_data["carbon_monoxide"]
            response_parts.append(f"Carbon Monoxide (CO): {co:.1f} μg/m³")

        # Sulfur Dioxide
        if "sulphur_dioxide" in aq_data:
            so2 = aq_data["sulphur_dioxide"]
            response_parts.append(f"Sulfur Dioxide (SO2): {so2:.1f} μg/m³")

        # Ammonia
        if "ammonia" in aq_data:
            nh3 = aq_data["ammonia"]
            response_parts.append(f"Ammonia (NH3): {nh3:.1f} μg/m³")

        # Dust
        if "dust" in aq_data:
            dust = aq_data["dust"]
            response_parts.append(f"Dust: {dust:.1f} μg/m³")

        # Aerosol Optical Depth
        if "aerosol_optical_depth" in aq_data:
            aod = aq_data["aerosol_optical_depth"]
            response_parts.append(f"Aerosol Optical Depth: {aod:.3f}")

        # Overall health recommendation
        if "pm2_5" in aq_data:
            health_advice = self._get_health_advice(aq_data["pm2_5"])
            response_parts.append(f"\nHealth Advice: {health_advice}")

        return "\n".join(response_parts)

    def format_air_quality_comprehensive(
        self,
        response_data: Dict[str, Any]
    ) -> str:
        """
        Format air quality data with comprehensive field descriptions for AI analysis.

        Args:
            response_data: Dictionary containing city, coordinates, and air quality data

        Returns:
            Formatted string with comprehensive descriptions for AI comprehension
        """

        return utils.format_air_quality_data(response_data)

    def _get_pm25_level(self, pm25: float) -> str:
        """
        Get PM2.5 air quality level based on WHO guidelines.

        Args:
            pm25: PM2.5 concentration in μg/m³

        Returns:
            Air quality level string
        """
        if pm25 <= 12:
            return "Good"
        elif pm25 <= 35:
            return "Moderate"
        elif pm25 <= 55:
            return "Unhealthy for Sensitive Groups"
        elif pm25 <= 150:
            return "Unhealthy"
        elif pm25 <= 250:
            return "Very Unhealthy"
        else:
            return "Hazardous"

    def _get_pm10_level(self, pm10: float) -> str:
        """
        Get PM10 air quality level.

        Args:
            pm10: PM10 concentration in μg/m³

        Returns:
            Air quality level string
        """
        if pm10 <= 54:
            return "Good"
        elif pm10 <= 154:
            return "Moderate"
        elif pm10 <= 254:
            return "Unhealthy for Sensitive Groups"
        elif pm10 <= 354:
            return "Unhealthy"
        elif pm10 <= 424:
            return "Very Unhealthy"
        else:
            return "Hazardous"

    def _get_health_advice(self, pm25: float) -> str:
        """
        Get health advice based on PM2.5 levels.

        Args:
            pm25: PM2.5 concentration in μg/m³

        Returns:
            Health advice string
        """
        if pm25 <= 12:
            return "Air quality is good. Safe for outdoor activities."
        elif pm25 <= 35:
            return "Air quality is acceptable. Sensitive individuals should consider reducing prolonged outdoor exertion."
        elif pm25 <= 55:
            return "Sensitive groups (children, elderly, people with respiratory conditions) should limit outdoor activities."
        elif pm25 <= 150:
            return "Everyone should reduce outdoor activities. Sensitive groups should avoid outdoor activities."
        elif pm25 <= 250:
            return "Everyone should avoid outdoor activities. Sensitive groups should remain indoors."
        else:
            return "Health alert: Everyone should avoid all outdoor activities and remain indoors."
