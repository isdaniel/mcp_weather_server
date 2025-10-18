"""
Time-related tool handlers for the MCP weather server.
This module contains time and timezone-related tool implementations.
"""

import json
import logging
from collections.abc import Sequence
from datetime import datetime
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from .toolhandler import ToolHandler
from .. import utils

logger = logging.getLogger("mcp-weather")


class GetCurrentDateTimeToolHandler(ToolHandler):
    """
    Tool handler for getting current date and time in a specified timezone.
    """
    
    def __init__(self):
        super().__init__("get_current_datetime")
    
    def get_tool_description(self) -> Tool:
        """
        Return the tool description for current datetime lookup.
        """
        return Tool(
            name=self.name,
            description="""Get current time in specified timezone.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone_name": {
                        "type": "string",
                        "description": "IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use UTC timezone if no timezone provided by the user."
                    }
                },
                "required": ["timezone_name"]
            }
        )
    
    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the current datetime tool.
        """
        try:
            self.validate_required_args(args, ["timezone_name"])
            
            timezone_name = args["timezone_name"]
            logger.info(f"Getting current time for timezone: {timezone_name}")
            
            # Get timezone info
            timezone = utils.get_zoneinfo(timezone_name)
            current_time = datetime.now(timezone)
            
            # Create time result
            time_result = utils.TimeResult(
                timezone=timezone_name,
                datetime=current_time.isoformat(timespec="seconds"),
            )
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps(time_result.dict(), indent=2)
                )
            ]
            
        except Exception as e:
            logger.exception(f"Error in get_current_datetime: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Error getting current time: {str(e)}"
                )
            ]


class GetTimeZoneInfoToolHandler(ToolHandler):
    """
    Tool handler for getting information about timezones.
    """
    
    def __init__(self):
        super().__init__("get_timezone_info")
    
    def get_tool_description(self) -> Tool:
        """
        Return the tool description for timezone information lookup.
        """
        return Tool(
            name=self.name,
            description="""Get information about a specific timezone including current time and UTC offset.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone_name": {
                        "type": "string",
                        "description": "IANA timezone name (e.g., 'America/New_York', 'Europe/London')"
                    }
                },
                "required": ["timezone_name"]
            }
        )
    
    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the timezone info tool.
        """
        try:
            self.validate_required_args(args, ["timezone_name"])
            
            timezone_name = args["timezone_name"]
            logger.info(f"Getting timezone info for: {timezone_name}")
            
            # Get timezone info
            timezone = utils.get_zoneinfo(timezone_name)
            current_time = datetime.now(timezone)
            utc_time = datetime.utcnow()
            
            # Calculate UTC offset
            offset = current_time.utcoffset()
            offset_hours = offset.total_seconds() / 3600 if offset else 0
            
            timezone_info = {
                "timezone_name": timezone_name,
                "current_local_time": current_time.isoformat(timespec="seconds"),
                "current_utc_time": utc_time.isoformat(timespec="seconds"),
                "utc_offset_hours": offset_hours,
                "is_dst": current_time.dst() is not None and current_time.dst().total_seconds() > 0,
                "timezone_abbreviation": current_time.strftime("%Z"),
            }
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps(timezone_info, indent=2)
                )
            ]
            
        except Exception as e:
            logger.exception(f"Error in get_timezone_info: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Error getting timezone info: {str(e)}"
                )
            ]


class ConvertTimeToolHandler(ToolHandler):
    """
    Tool handler for converting time between different timezones.
    """
    
    def __init__(self):
        super().__init__("convert_time")
    
    def get_tool_description(self) -> Tool:
        """
        Return the tool description for time conversion.
        """
        return Tool(
            name=self.name,
            description="""Convert time from one timezone to another.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "datetime_str": {
                        "type": "string",
                        "description": "DateTime string in ISO format (e.g., '2024-01-15T14:30:00') or 'now' for current time"
                    },
                    "from_timezone": {
                        "type": "string",
                        "description": "Source timezone (IANA timezone name)"
                    },
                    "to_timezone": {
                        "type": "string",
                        "description": "Target timezone (IANA timezone name)"
                    }
                },
                "required": ["datetime_str", "from_timezone", "to_timezone"]
            }
        )
    
    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the time conversion tool.
        """
        try:
            self.validate_required_args(args, ["datetime_str", "from_timezone", "to_timezone"])
            
            datetime_str = args["datetime_str"]
            from_timezone_name = args["from_timezone"]
            to_timezone_name = args["to_timezone"]
            
            logger.info(f"Converting time '{datetime_str}' from {from_timezone_name} to {to_timezone_name}")
            
            # Get timezone objects
            from_timezone = utils.get_zoneinfo(from_timezone_name)
            to_timezone = utils.get_zoneinfo(to_timezone_name)
            
            # Parse the datetime
            if datetime_str.lower() == "now":
                source_time = datetime.now(from_timezone)
            else:
                # Parse the datetime string and localize it
                if datetime_str.endswith('Z'):
                    # UTC time
                    naive_time = datetime.fromisoformat(datetime_str[:-1])
                    source_time = naive_time.replace(tzinfo=from_timezone)
                else:
                    # Assume local time in from_timezone
                    naive_time = datetime.fromisoformat(datetime_str)
                    source_time = naive_time.replace(tzinfo=from_timezone)
            
            # Convert to target timezone
            target_time = source_time.astimezone(to_timezone)
            
            conversion_result = {
                "original_datetime": source_time.isoformat(timespec="seconds"),
                "original_timezone": from_timezone_name,
                "converted_datetime": target_time.isoformat(timespec="seconds"),
                "converted_timezone": to_timezone_name,
                "time_difference_hours": (target_time.utcoffset().total_seconds() - source_time.utcoffset().total_seconds()) / 3600
            }
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps(conversion_result, indent=2)
                )
            ]
            
        except Exception as e:
            logger.exception(f"Error in convert_time: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Error converting time: {str(e)}"
                )
            ]
