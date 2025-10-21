
from datetime import datetime, timezone
import json
from typing import List
from zoneinfo import ZoneInfo
from mcp.types import ErrorData
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
        error_data = ErrorData(code=-1, message=f"Invalid timezone: {str(e)}")
        raise McpError(error_data)

def format_get_weather_bytime(data_result) -> str:
    """
    Format weather data with comprehensive field descriptions for AI model comprehension.

    Args:
        data_result: Dictionary containing weather forecast data

    Returns:
        Formatted string with weather data and field explanations
    """
    return f"""
Please analyze the following JSON weather forecast information and generate a comprehensive report.

=== FIELD DESCRIPTIONS ===

TOP-LEVEL FIELDS:
- city: The name of the city for which weather data is provided
- latitude: Geographic latitude of the city location (decimal degrees)
- longitude: Geographic longitude of the city location (decimal degrees)
- start_date: The beginning date of the weather forecast period (format: YYYY-MM-DD)
- end_date: The ending date of the weather forecast period (format: YYYY-MM-DD)
- weather_data: Array of hourly weather observations, each containing the fields described below

WEATHER_DATA FIELDS (for each hour):

TIME & LOCATION:
- time: ISO 8601 timestamp of the observation (UTC timezone)

TEMPERATURE:
- temperature_c: Air temperature in degrees Celsius (°C) at 2 meters above ground
- apparent_temperature_c: "Feels like" temperature in °C, accounting for wind chill and humidity
- dew_point_c: Dew point temperature in °C (temperature at which air becomes saturated)

HUMIDITY & ATMOSPHERIC CONDITIONS:
- humidity_percent: Relative humidity as a percentage (0-100%)
- pressure_hpa: Atmospheric pressure at mean sea level in hectopascals (hPa)
- cloud_cover_percent: Cloud cover as a percentage of sky covered (0-100%)
- visibility_m: Horizontal visibility distance in meters

WIND CONDITIONS:
- wind_speed_kmh: Wind speed at 10 meters above ground in kilometers per hour (km/h)
- wind_direction_degrees: Wind direction in meteorological degrees (0-360°, where 0°/360° = North, 90° = East, 180° = South, 270° = West)
- wind_gusts_kmh: Maximum wind gust speed in km/h

PRECIPITATION:
- precipitation_mm: Total precipitation (rain + snow) in millimeters (mm)
- rain_mm: Liquid rainfall amount in millimeters (mm)
- snowfall_cm: Snowfall amount in centimeters (cm)
- precipitation_probability_percent: Probability of precipitation occurrence as percentage (0-100%)

WEATHER CLASSIFICATION:
- weather_code: Numerical WMO weather code (see code mappings below)
- weather_description: Human-readable description of weather conditions

SAFETY & COMFORT INDICES:
- uv_index: UV radiation index (0-11+, where 0-2=Low, 3-5=Moderate, 6-7=High, 8-10=Very High, 11+=Extreme)

=== WEATHER DATA ===
{json.dumps(data_result, indent=2)}

=== ANALYSIS INSTRUCTIONS ===
Based on the above weather data, please provide:
1. A summary of weather trends over the date range
2. Notable weather events or significant changes
3. Temperature patterns (highs, lows, average)
4. Precipitation analysis (total amounts, probability patterns)
5. Wind conditions assessment
6. Any weather warnings or recommendations based on the data
        """

def format_air_quality_data(data_result) -> str:
    """
    Format air quality data with comprehensive field descriptions for AI model comprehension.

    Args:
        data_result: Dictionary containing air quality data

    Returns:
        Formatted string with air quality data and field explanations
    """
    return f"""
Please analyze the following JSON air quality information and generate a comprehensive report.

=== FIELD DESCRIPTIONS ===

TOP-LEVEL FIELDS:
- city: The name of the city for which air quality data is provided
- latitude: Geographic latitude of the city location (decimal degrees)
- longitude: Geographic longitude of the city location (decimal degrees)
- current_air_quality: Current air quality measurements at the time of observation
- full_data: Complete hourly air quality data including historical readings

AIR QUALITY POLLUTANT FIELDS:

PARTICULATE MATTER (Primary Health Indicators):
- pm2_5: Fine particulate matter ≤2.5 micrometers in diameter (μg/m³)
  * Most dangerous to health as it can penetrate deep into lungs
  * WHO Guidelines: ≤12 μg/m³ (Good), 12-35 (Moderate), 35-55 (Unhealthy for Sensitive), 55-150 (Unhealthy), 150-250 (Very Unhealthy), >250 (Hazardous)
- pm10: Coarse particulate matter ≤10 micrometers in diameter (μg/m³)
  * Includes dust, pollen, and mold spores
  * Guidelines: ≤54 μg/m³ (Good), 54-154 (Moderate), 154-254 (Unhealthy for Sensitive), 254-354 (Unhealthy), 354-424 (Very Unhealthy), >424 (Hazardous)

GASEOUS POLLUTANTS:
- ozone: Ground-level ozone (O3) concentration in μg/m³
  * Formed by reactions between nitrogen oxides and volatile organic compounds in sunlight
  * Harmful to respiratory system, especially during hot weather
- nitrogen_dioxide: NO2 concentration in μg/m³
  * Major air pollutant from vehicle emissions and industrial processes
  * Can aggravate respiratory diseases
- carbon_monoxide: CO concentration in μg/m³
  * Colorless, odorless gas from incomplete combustion
  * Reduces oxygen delivery to organs and tissues
- sulphur_dioxide: SO2 concentration in μg/m³
  * Produced by burning fossil fuels and smelting mineral ores
  * Causes respiratory problems and acid rain
- ammonia: NH3 concentration in μg/m³
  * Primarily from agricultural activities and industrial processes
  * Irritant to respiratory system at high concentrations

ATMOSPHERIC PARTICLES:
- dust: Dust particle concentration in μg/m³
  * Includes soil dust, construction dust, and other airborne particles
- aerosol_optical_depth: Measure of light extinction by aerosols (dimensionless, 0-1+)
  * Indicates atmospheric turbidity and visibility reduction
  * Higher values mean more aerosols and reduced air quality

=== HEALTH IMPACT GUIDELINES ===

PM2.5 HEALTH ADVISORY LEVELS:
- 0-12 μg/m³: Good - Air quality is satisfactory, safe for outdoor activities
- 12-35 μg/m³: Moderate - Acceptable quality, sensitive individuals should consider reducing prolonged outdoor exertion
- 35-55 μg/m³: Unhealthy for Sensitive Groups - Children, elderly, and people with respiratory conditions should limit outdoor activities
- 55-150 μg/m³: Unhealthy - Everyone should reduce outdoor activities, sensitive groups avoid outdoor activities
- 150-250 μg/m³: Very Unhealthy - Everyone should avoid outdoor activities, sensitive groups remain indoors
- >250 μg/m³: Hazardous - Health alert, everyone should avoid all outdoor activities and remain indoors

SENSITIVE GROUPS:
- Children and elderly
- People with asthma or other respiratory conditions
- People with heart disease
- Pregnant women
- Individuals with compromised immune systems

=== AIR QUALITY DATA ===
{json.dumps(data_result, indent=2)}

=== ANALYSIS INSTRUCTIONS ===
Based on the above air quality data, please provide:
1. Overall air quality assessment (Good/Moderate/Unhealthy/Hazardous)
2. Primary pollutants of concern and their levels
3. Health recommendations for the general population
4. Specific warnings for sensitive groups
5. Comparison with WHO and EPA air quality standards
6. Suggestions for protective measures (masks, indoor air purifiers, limiting outdoor activities)
7. Temporal trends if hourly data is available
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
