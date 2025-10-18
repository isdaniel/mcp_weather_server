"""
This server implements a modular, extensible design pattern similar to mcp-gsuite,
making it easy to add new weather-related tools and functionality.
Supports both stdio and SSE MCP server modes.
"""

import argparse
import asyncio
import logging
import sys
import traceback
from typing import Any, Dict, Optional
from collections.abc import Sequence
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# SSE-related imports (imported conditionally)
try:
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.routing import Mount, Route
    from starlette.middleware.cors import CORSMiddleware
    import uvicorn
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False

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

# Create the MCP server instance
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





def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """
    Create a Starlette application that can serve the provided mcp server with SSE.
    Implements the MCP Streamable HTTP protocol with /mcp endpoint and CORS support.

    Args:
        mcp_server: The MCP server instance
        debug: Whether to enable debug mode

    Returns:
        Starlette application instance
    """
    if not SSE_AVAILABLE:
        raise RuntimeError("SSE dependencies not available. Install with: pip install starlette uvicorn")

    sse = SseServerTransport("/messages/")

    async def handle_mcp(request: Request) -> None:
        """Handle requests to the /mcp endpoint"""
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    app = Starlette(
        debug=debug,
        routes=[
            Route("/mcp", endpoint=handle_mcp),
            Route("/sse", endpoint=handle_mcp),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    # Add CORS middleware for Smithery deployment
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for MCP clients
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id", "mcp-protocol-version"],
        max_age=86400,
    )

    return app


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
    Supports both stdio and SSE modes based on command line arguments.
    For Smithery deployments, reads PORT from environment variable.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MCP Weather Server - supports stdio and SSE modes')
    parser.add_argument('--mode', choices=['stdio', 'sse'], default='stdio',
                        help='Server mode: stdio (default) or sse')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (SSE mode only, default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=None,
                        help='Port to listen on (SSE mode only, default: from PORT env var or 8080)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')

    args = parser.parse_args()

    # Get port from environment variable (Smithery sets this to 8081)
    # or use command line argument, or default to 8080
    import os
    port = args.port if args.port is not None else int(os.environ.get("PORT", 8080))

    try:
        # Register all tools
        register_all_tools()

        logger.info(f"Starting MCP Weather Server in {args.mode} mode...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Registered tools: {list(tool_handlers.keys())}")

        # Run the server in the specified mode
        await run_server(args.mode, args.host, port, args.debug)

    except Exception as e:
        logger.exception(f"Failed to start server: {str(e)}")
        raise


async def run_server(mode: str, host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
    """
    Unified server runner that supports both stdio and SSE modes.

    Args:
        mode: Server mode ("stdio" or "sse")
        host: Host to bind to (SSE mode only)
        port: Port to listen on (SSE mode only)
        debug: Whether to enable debug mode
    """
    if mode == "stdio":
        logger.info("Starting stdio server...")

        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )

    elif mode == "sse":
        if not SSE_AVAILABLE:
            raise RuntimeError(
                "SSE mode requires additional dependencies. "
                "Install with: pip install starlette uvicorn"
            )

        logger.info(f"Starting SSE server on {host}:{port}...")

        # Create Starlette app with SSE transport
        starlette_app = create_starlette_app(app, debug=debug)

        # Configure uvicorn
        config = uvicorn.Config(
            app=starlette_app,
            host=host,
            port=port,
            log_level="debug" if debug else "info"
        )

        # Run the server
        server = uvicorn.Server(config)
        await server.serve()

    else:
        raise ValueError(f"Unknown mode: {mode}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
