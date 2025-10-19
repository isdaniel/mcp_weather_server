"""
This server implements a modular, extensible design pattern similar to mcp-gsuite,
making it easy to add new weather-related tools and functionality.
Supports both stdio and SSE MCP server modes.
"""
import argparse
import asyncio
import contextlib
import logging
import sys
import traceback
from collections.abc import AsyncIterator, Sequence
from typing import Any, Dict, Optional

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.routing import Mount, Route
import uvicorn

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
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
            Route("/sse", endpoint=handle_mcp),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    return app


def create_streamable_http_app(mcp_server: Server, *, debug: bool = False, stateless: bool = False) -> Starlette:
    """
    Create a Starlette application with StreamableHTTPSessionManager.
    Implements the new MCP Streamable HTTP protocol with a single /mcp endpoint.

    Args:
        mcp_server: The MCP server instance
        debug: Whether to enable debug mode
        stateless: If True, creates a fresh transport for each request with no session tracking

    Returns:
        Tuple of (Starlette application instance, StreamableHTTPSessionManager instance)
    """

    # Create the session manager
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        event_store=None,  # No event store for now (no resumability)
        json_response=False,
        stateless=stateless,
    )

    async def handle_streamable_http(scope, receive, send) -> None:
        """Handle Streamable HTTP requests to the /mcp endpoint"""
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Context manager for session manager lifecycle."""
        async with session_manager.run():
            logger.info("Streamable HTTP session manager started!")
            try:
                yield
            finally:
                logger.info("Streamable HTTP session manager shutting down...")

    # Create Starlette app with a single endpoint, We mount the handler as an ASGI app, not as a route endpoint
    starlette_app = Starlette(
        debug=debug,
        routes=[
            Mount("/mcp", app=handle_streamable_http),
        ],
        lifespan=lifespan,
    )

    # Add CORS middleware
    starlette_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id", "mcp-protocol-version"],
        max_age=86400,
    )

    return starlette_app


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
    Supports stdio, SSE, and streamable-http modes based on command line arguments.
    For Smithery deployments, reads PORT from environment variable.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MCP Weather Server - supports stdio, SSE, and streamable-http modes')
    parser.add_argument('--mode', choices=['stdio', 'sse', 'streamable-http'], default='stdio',
                        help='Server mode: stdio (default), sse, or streamable-http')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (HTTP modes only, default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=None,
                        help='Port to listen on (HTTP modes only, default: from PORT env var or 8080)')
    parser.add_argument('--stateless', action='store_true',
                        help='Run in stateless mode (streamable-http only, creates fresh transport per request)')
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
        await run_server(args.mode, args.host, port, args.debug, args.stateless)

    except Exception as e:
        logger.exception(f"Failed to start server: {str(e)}")
        raise


async def run_server(mode: str, host: str = "0.0.0.0", port: int = 8080, debug: bool = False, stateless: bool = False):
    """
    Unified server runner that supports stdio, SSE, and streamable-http modes.

    Args:
        mode: Server mode ("stdio", "sse", or "streamable-http")
        host: Host to bind to (HTTP modes only)
        port: Port to listen on (HTTP modes only)
        debug: Whether to enable debug mode
        stateless: Whether to use stateless mode (streamable-http only)
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

    elif mode == "streamable-http":

        mode_desc = "stateless" if stateless else "stateful"
        logger.info(f"Starting Streamable HTTP server ({mode_desc}) on {host}:{port}...")
        logger.info(f"Endpoint: http://{host}:{port}/mcp")


        starlette_app = create_streamable_http_app(app, debug=debug, stateless=stateless)

        # Configure uvicorn
        config = uvicorn.Config(
            app=starlette_app,
            host=host,
            port=port,
            log_level="debug" if debug else "info"
        )

        # Run the server (session manager lifecycle is handled by lifespan)
        server = uvicorn.Server(config)
        await server.serve()

    else:
        raise ValueError(f"Unknown mode: {mode}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
