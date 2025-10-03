"""
This server implements a modular, extensible design pattern similar to mcp-gsuite,
making it easy to add new weather-related tools and functionality.
"""

import logging
import sys
import traceback
from typing import Any, Dict
from collections.abc import Sequence
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Import tool handlers
from .tools.toolhandler import ToolHandler
from .tools.tools_weather import (
    GetCurrentWeatherToolHandler,
    GetWeatherByDateRangeToolHandler,
    GetWeatherDetailsToolHandler,
)
from .tools.tools_time import (
    GetCurrentDateTimeToolHandler,
    GetTimeZoneInfoToolHandler,
    ConvertTimeToolHandler,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-weather")

# Create the MCP server
app = Server("mcp-weather-server")

# Global tool handlers registry
tool_handlers: Dict[str, ToolHandler] = {}


def add_tool_handler(tool_handler: ToolHandler) -> None:
    """
    Register a tool handler with the server.
    
    Args:
        tool_handler: The tool handler instance to register
    """
    global tool_handlers
    tool_handlers[tool_handler.name] = tool_handler
    logger.info(f"Registered tool handler: {tool_handler.name}")


def get_tool_handler(name: str) -> ToolHandler | None:
    """
    Retrieve a tool handler by name.
    
    Args:
        name: The name of the tool handler
        
    Returns:
        The tool handler instance or None if not found
    """
    return tool_handlers.get(name)


def register_all_tools() -> None:
    """
    Register all available tool handlers.
    
    This function serves as the central registry for all tools.
    New tool handlers should be added here for automatic registration.
    """
    # Weather tools
    add_tool_handler(GetCurrentWeatherToolHandler())
    add_tool_handler(GetWeatherByDateRangeToolHandler())
    add_tool_handler(GetWeatherDetailsToolHandler())
    
    # Time tools
    add_tool_handler(GetCurrentDateTimeToolHandler())
    add_tool_handler(GetTimeZoneInfoToolHandler())
    add_tool_handler(ConvertTimeToolHandler())
    
    logger.info(f"Registered {len(tool_handlers)} tool handlers")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List all available tools.
    
    Returns:
        List of Tool objects describing all registered tools
    """
    try:
        tools = [handler.get_tool_description() for handler in tool_handlers.values()]
        logger.info(f"Listed {len(tools)} available tools")
        return tools
    except Exception as e:
        logger.exception(f"Error listing tools: {str(e)}")
        raise


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """
    Execute a tool with the provided arguments.
    
    Args:
        name: The name of the tool to execute
        arguments: The arguments to pass to the tool
        
    Returns:
        Sequence of MCP content objects
        
    Raises:
        RuntimeError: If the tool execution fails
    """
    try:
        # Validate arguments
        if not isinstance(arguments, dict):
            raise RuntimeError("Arguments must be a dictionary")
        
        # Get the tool handler
        tool_handler = get_tool_handler(name)
        if not tool_handler:
            raise ValueError(f"Unknown tool: {name}")
        
        logger.info(f"Executing tool: {name} with arguments: {list(arguments.keys())}")
        
        # Execute the tool
        result = await tool_handler.run_tool(arguments)
        
        logger.info(f"Tool {name} executed successfully")
        return result
        
    except Exception as e:
        logger.exception(f"Error executing tool {name}: {str(e)}")
        error_traceback = traceback.format_exc()
        logger.error(f"Full traceback: {error_traceback}")
        
        # Return error as text content
        return [
            TextContent(
                type="text",
                text=f"Error executing tool '{name}': {str(e)}"
            )
        ]


async def main():
    """
    Main entry point for the MCP weather server.
    """
    try:
        # Register all tools
        register_all_tools()
        
        logger.info("Starting MCP Weather Server...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Registered tools: {list(tool_handlers.keys())}")
        
        # Start the server
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
            
    except Exception as e:
        logger.exception(f"Failed to start server: {str(e)}")
        raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
