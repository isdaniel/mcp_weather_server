"""
Weather-related tool handlers for the MCP weather server.
This module contains all weather-specific tool implementations.
"""

import json
import logging
from collections.abc import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from .toolhandler import ToolHandler
from .weather_service import WeatherService

logger = logging.getLogger("mcp-weather")


class GetCurrentWeatherToolHandler(ToolHandler):
    """
    Tool handler for getting current weather information for a city.
    """
    
    def __init__(self):
        super().__init__("get_current_weather")
        self.weather_service = WeatherService()
    
    def get_tool_description(self) -> Tool:
        """
        Return the tool description for current weather lookup.
        """
        return Tool(
            name=self.name,
            description="""Get current weather information for a specified city.
            It extracts the current hour's temperature and weather code, maps
            the weather code to a human-readable description, and returns a formatted summary.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city to fetch weather information for, PLEASE NOTE English name only, if the parameter city isn't English please translate to English before invoking this function."
                    }
                },
                "required": ["city"]
            }
        )
    
    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the current weather tool.
        """
        try:
            self.validate_required_args(args, ["city"])
            
            city = args["city"]
            logger.info(f"Getting current weather for: {city}")
            
            # Get weather data from service
            weather_data = await self.weather_service.get_current_weather(city)
            
            # Format the response
            formatted_response = self.weather_service.format_current_weather_response(weather_data)
            
            return [
                TextContent(
                    type="text",
                    text=formatted_response
                )
            ]
            
        except ValueError as e:
            logger.error(f"Weather service error: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ]
        except Exception as e:
            logger.exception(f"Unexpected error in get_current_weather: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Unexpected error occurred: {str(e)}"
                )
            ]


class GetWeatherByDateRangeToolHandler(ToolHandler):
    """
    Tool handler for getting weather information for a date range.
    """
    
    def __init__(self):
        super().__init__("get_weather_byDateTimeRange")
        self.weather_service = WeatherService()
    
    def get_tool_description(self) -> Tool:
        """
        Return the tool description for weather date range lookup.
        """
        return Tool(
            name=self.name,
            description="""Get weather information for a specified city between start and end dates.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city to fetch weather information for, PLEASE NOTE English name only, if the parameter city isn't English please translate to English before invoking this function."
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in format YYYY-MM-DD, please follow ISO 8601 format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in format YYYY-MM-DD , please follow ISO 8601 format"
                    }
                },
                "required": ["city", "start_date", "end_date"]
            }
        )
    
    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the weather date range tool.
        """
        try:
            self.validate_required_args(args, ["city", "start_date", "end_date"])
            
            city = args["city"]
            start_date = args["start_date"]
            end_date = args["end_date"]
            
            logger.info(f"Getting weather for {city} from {start_date} to {end_date}")
            
            # Get weather data from service
            weather_data = await self.weather_service.get_weather_by_date_range(
                city, start_date, end_date
            )
            
            # Format the response for analysis
            formatted_response = self.weather_service.format_weather_range_response(weather_data)
            
            return [
                TextContent(
                    type="text",
                    text=formatted_response
                )
            ]
            
        except ValueError as e:
            logger.error(f"Weather service error: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ]
        except Exception as e:
            logger.exception(f"Unexpected error in get_weather_by_date_range: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Unexpected error occurred: {str(e)}"
                )
            ]


class GetWeatherDetailsToolHandler(ToolHandler):
    """
    Tool handler for getting detailed weather information with raw data.
    This tool provides structured JSON output for programmatic use.
    """
    
    def __init__(self):
        super().__init__("get_weather_details")
        self.weather_service = WeatherService()
    
    def get_tool_description(self) -> Tool:
        """
        Return the tool description for detailed weather lookup.
        """
        return Tool(
            name=self.name,
            description="""Get detailed weather information for a specified city as structured JSON data.
            This tool provides raw weather data for programmatic analysis and processing.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city to fetch weather information for, PLEASE NOTE English name only, if the parameter city isn't English please translate to English before invoking this function."
                    },
                    "include_forecast": {
                        "type": "boolean",
                        "description": "Whether to include forecast data (next 24 hours)",
                        "default": False
                    }
                },
                "required": ["city"]
            }
        )
    
    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the detailed weather tool.
        """
        try:
            self.validate_required_args(args, ["city"])
            
            city = args["city"]
            include_forecast = args.get("include_forecast", False)
            
            logger.info(f"Getting detailed weather for: {city} (forecast: {include_forecast})")
            
            # Get current weather data
            weather_data = await self.weather_service.get_current_weather(city)
            
            # If forecast is requested, get the next 24 hours
            if include_forecast:
                from datetime import datetime, timedelta
                
                today = datetime.now().strftime("%Y-%m-%d")
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                
                forecast_data = await self.weather_service.get_weather_by_date_range(
                    city, today, tomorrow
                )
                weather_data["forecast"] = forecast_data["weather_data"]
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps(weather_data, indent=2)
                )
            ]
            
        except ValueError as e:
            logger.error(f"Weather service error: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )
            ]
        except Exception as e:
            logger.exception(f"Unexpected error in get_weather_details: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unexpected error occurred: {str(e)}"}, indent=2)
                )
            ]
