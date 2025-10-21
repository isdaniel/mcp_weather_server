"""
Air Quality tool handlers for the MCP weather server.
This module contains air quality-specific tool implementations.
"""

import json
import logging
from collections.abc import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from .toolhandler import ToolHandler
from .air_quality_service import AirQualityService
from .weather_service import WeatherService

logger = logging.getLogger("mcp-weather")


class GetAirQualityToolHandler(ToolHandler):
    """
    Tool handler for getting air quality information for a city.
    Provides PM2.5, PM10, ozone, and other pollutant data.
    """

    def __init__(self):
        super().__init__("get_air_quality")
        self.air_quality_service = AirQualityService()
        self.weather_service = WeatherService()  # For geocoding

    def get_tool_description(self) -> Tool:
        """
        Return the tool description for air quality lookup.
        """
        return Tool(
            name=self.name,
            description="""Get air quality information for a specified city including PM2.5, PM10,
            ozone, nitrogen dioxide, carbon monoxide, and other pollutants. Provides health
            advisories based on current air quality levels.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city to fetch air quality information for, PLEASE NOTE English name only, if the parameter city isn't English please translate to English before invoking this function."
                    },
                    "variables": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "pm10",
                                "pm2_5",
                                "carbon_monoxide",
                                "nitrogen_dioxide",
                                "ozone",
                                "sulphur_dioxide",
                                "ammonia",
                                "dust",
                                "aerosol_optical_depth"
                            ]
                        },
                        "description": "Air quality variables to retrieve. If not specified, defaults to pm10, pm2_5, ozone, nitrogen_dioxide, and carbon_monoxide."
                    }
                },
                "required": ["city"]
            }
        )

    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the air quality tool.
        """
        try:
            self.validate_required_args(args, ["city"])

            city = args["city"]
            variables = args.get("variables", [
                "pm10", "pm2_5", "ozone", "nitrogen_dioxide", "carbon_monoxide"
            ])

            logger.info(f"Getting air quality for: {city} with variables: {variables}")

            # Get coordinates for the city
            latitude, longitude = await self.weather_service.get_coordinates(city)

            # Get air quality data
            aq_data = await self.air_quality_service.get_air_quality(
                latitude, longitude, variables
            )

            # Get current air quality values
            current_aq = self.air_quality_service.get_current_air_quality_index(aq_data)

            # Build comprehensive response data for AI comprehension
            response_data = {
                "city": city,
                "latitude": latitude,
                "longitude": longitude,
                "current_air_quality": current_aq,
                "full_data": aq_data
            }

            # Format the response with comprehensive field descriptions
            formatted_response = self.air_quality_service.format_air_quality_comprehensive(
                response_data
            )

            return [
                TextContent(
                    type="text",
                    text=formatted_response
                )
            ]

        except ValueError as e:
            logger.error(f"Air quality service error: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ]
        except Exception as e:
            logger.exception(f"Unexpected error in get_air_quality: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Unexpected error occurred: {str(e)}"
                )
            ]


class GetAirQualityDetailsToolHandler(ToolHandler):
    """
    Tool handler for getting detailed air quality information with raw data.
    This tool provides structured JSON output for programmatic use.
    """

    def __init__(self):
        super().__init__("get_air_quality_details")
        self.air_quality_service = AirQualityService()
        self.weather_service = WeatherService()  # For geocoding

    def get_tool_description(self) -> Tool:
        """
        Return the tool description for detailed air quality lookup.
        """
        return Tool(
            name=self.name,
            description="""Get detailed air quality information for a specified city as structured JSON data.
            This tool provides raw air quality data for programmatic analysis and processing.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city to fetch air quality information for, PLEASE NOTE English name only, if the parameter city isn't English please translate to English before invoking this function."
                    },
                    "variables": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "pm10",
                                "pm2_5",
                                "carbon_monoxide",
                                "nitrogen_dioxide",
                                "ozone",
                                "sulphur_dioxide",
                                "ammonia",
                                "dust",
                                "aerosol_optical_depth"
                            ]
                        },
                        "description": "Air quality variables to retrieve"
                    }
                },
                "required": ["city"]
            }
        )

    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the detailed air quality tool.
        """
        try:
            self.validate_required_args(args, ["city"])

            city = args["city"]
            variables = args.get("variables", [
                "pm10", "pm2_5", "ozone", "nitrogen_dioxide", "carbon_monoxide",
                "sulphur_dioxide", "ammonia", "dust", "aerosol_optical_depth"
            ])

            logger.info(f"Getting detailed air quality for: {city}")

            # Get coordinates for the city
            latitude, longitude = await self.weather_service.get_coordinates(city)

            # Get air quality data
            aq_data = await self.air_quality_service.get_air_quality(
                latitude, longitude, variables
            )

            # Get current air quality values
            current_aq = self.air_quality_service.get_current_air_quality_index(aq_data)

            # Build response with metadata
            response_data = {
                "city": city,
                "latitude": latitude,
                "longitude": longitude,
                "current_air_quality": current_aq,
                "full_data": aq_data
            }

            return [
                TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2)
                )
            ]

        except ValueError as e:
            logger.error(f"Air quality service error: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )
            ]
        except Exception as e:
            logger.exception(f"Unexpected error in get_air_quality_details: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unexpected error occurred: {str(e)}"}, indent=2)
                )
            ]
