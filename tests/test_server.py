"""
Unit tests for server functionality.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from src.mcp_weather_server.server import (
    add_tool_handler,
    get_tool_handler,
    register_all_tools,
    list_tools,
    call_tool,
    tool_handlers
)
from src.mcp_weather_server.tools.toolhandler import ToolHandler
from mcp.types import Tool, TextContent


class MockToolHandler(ToolHandler):
    """Mock tool handler for testing."""

    def __init__(self, name="mock_tool"):
        super().__init__(name)
        self.get_tool_description_called = False
        self.run_tool_called = False
        self.run_tool_args = None

    def get_tool_description(self) -> Tool:
        self.get_tool_description_called = True
        return Tool(
            name=self.name,
            description="Mock tool for testing",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_param": {"type": "string"}
                },
                "required": ["test_param"]
            }
        )

    async def run_tool(self, args: dict):
        self.run_tool_called = True
        self.run_tool_args = args
        return [TextContent(type="text", text=f"Mock result for {args}")]


class TestServerFunctions:
    """Test cases for server functions."""

    def setup_method(self):
        """Clear tool handlers before each test."""
        global tool_handlers
        tool_handlers.clear()

    def test_add_tool_handler(self):
        """Test adding a tool handler."""
        handler = MockToolHandler("test_tool")
        add_tool_handler(handler)

        assert "test_tool" in tool_handlers
        assert tool_handlers["test_tool"] == handler

    def test_get_tool_handler_existing(self):
        """Test getting an existing tool handler."""
        handler = MockToolHandler("existing_tool")
        add_tool_handler(handler)

        retrieved = get_tool_handler("existing_tool")
        assert retrieved == handler

    def test_get_tool_handler_nonexistent(self):
        """Test getting a non-existent tool handler."""
        retrieved = get_tool_handler("nonexistent_tool")
        assert retrieved is None

    def test_register_all_tools(self):
        """Test registering all tools."""
        register_all_tools()

        # Check that expected tools are registered
        expected_tools = [
            "get_current_weather",
            "get_weather_byDateTimeRange",
            "get_weather_details",
            "get_current_datetime",
            "get_timezone_info",
            "convert_time"
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_handlers
            assert tool_handlers[tool_name] is not None

    @pytest.mark.asyncio
    async def test_list_tools_empty(self):
        """Test listing tools when no tools are registered."""
        result = await list_tools()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_tools_with_handlers(self):
        """Test listing tools with registered handlers."""
        handler1 = MockToolHandler("tool1")
        handler2 = MockToolHandler("tool2")
        add_tool_handler(handler1)
        add_tool_handler(handler2)

        result = await list_tools()

        assert len(result) == 2
        assert handler1.get_tool_description_called
        assert handler2.get_tool_description_called

        tool_names = [tool.name for tool in result]
        assert "tool1" in tool_names
        assert "tool2" in tool_names

    @pytest.mark.asyncio
    async def test_list_tools_exception_handling(self):
        """Test list_tools exception handling."""
        # Create a mock handler that raises an exception
        with patch.dict(tool_handlers, {"bad_tool": Mock()}):
            tool_handlers["bad_tool"].get_tool_description.side_effect = Exception("Test error")

            with pytest.raises(Exception):
                await list_tools()

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """Test successful tool execution."""
        handler = MockToolHandler("test_tool")
        add_tool_handler(handler)

        args = {"test_param": "test_value"}
        result = await call_tool("test_tool", args)

        assert handler.run_tool_called
        assert handler.run_tool_args == args
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "test_value" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_nonexistent(self):
        """Test calling a non-existent tool."""
        args = {"test_param": "test_value"}
        result = await call_tool("nonexistent_tool", args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error executing tool 'nonexistent_tool'" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_invalid_arguments(self):
        """Test calling a tool with invalid arguments."""
        handler = MockToolHandler("test_tool")
        add_tool_handler(handler)

        # Pass non-dict arguments
        result = await call_tool("test_tool", "invalid_args")

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error executing tool 'test_tool'" in result[0].text
        assert "Arguments must be a dictionary" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_handler_exception(self):
        """Test calling a tool when handler raises an exception."""
        handler = MockToolHandler("test_tool")
        handler.run_tool = AsyncMock(side_effect=Exception("Handler error"))
        add_tool_handler(handler)

        args = {"test_param": "test_value"}
        result = await call_tool("test_tool", args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error executing tool 'test_tool'" in result[0].text
        assert "Handler error" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_with_complex_args(self):
        """Test calling a tool with complex arguments."""
        handler = MockToolHandler("complex_tool")
        add_tool_handler(handler)

        complex_args = {
            "string_param": "test_string",
            "number_param": 42,
            "list_param": [1, 2, 3],
            "dict_param": {"nested": "value"}
        }

        result = await call_tool("complex_tool", complex_args)

        assert handler.run_tool_called
        assert handler.run_tool_args == complex_args
        assert len(result) == 1


class TestToolHandlerIntegration:
    """Integration tests for tool handler registration and execution."""

    def setup_method(self):
        """Clear tool handlers before each test."""
        global tool_handlers
        tool_handlers.clear()

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow from registration to execution."""
        # Register a tool
        handler = MockToolHandler("workflow_tool")
        add_tool_handler(handler)

        # List tools
        tools = await list_tools()
        assert len(tools) == 1
        assert tools[0].name == "workflow_tool"

        # Call the tool
        args = {"test_param": "workflow_test"}
        result = await call_tool("workflow_tool", args)

        assert len(result) == 1
        assert "workflow_test" in result[0].text

    @pytest.mark.asyncio
    async def test_multiple_tools_workflow(self):
        """Test workflow with multiple tools."""
        # Register multiple tools
        handler1 = MockToolHandler("tool_one")
        handler2 = MockToolHandler("tool_two")
        handler3 = MockToolHandler("tool_three")

        add_tool_handler(handler1)
        add_tool_handler(handler2)
        add_tool_handler(handler3)

        # List all tools
        tools = await list_tools()
        assert len(tools) == 3

        tool_names = [tool.name for tool in tools]
        assert "tool_one" in tool_names
        assert "tool_two" in tool_names
        assert "tool_three" in tool_names

        # Call each tool
        for tool_name in ["tool_one", "tool_two", "tool_three"]:
            args = {"test_param": f"test_{tool_name}"}
            result = await call_tool(tool_name, args)
            assert len(result) == 1
            assert f"test_{tool_name}" in result[0].text

    @pytest.mark.asyncio
    async def test_real_tool_registration(self):
        """Test registration of real tool handlers."""
        register_all_tools()

        # Verify specific tools are registered
        weather_tool = get_tool_handler("get_current_weather")
        assert weather_tool is not None

        time_tool = get_tool_handler("get_current_datetime")
        assert time_tool is not None

        # Test tool descriptions
        tools = await list_tools()
        assert len(tools) >= 6  # Should have at least 6 tools

        # Verify tool names
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "get_current_weather",
            "get_weather_byDateTimeRange",
            "get_weather_details",
            "get_current_datetime",
            "get_timezone_info",
            "convert_time"
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_handler_replacement(self):
        """Test replacing an existing tool handler."""
        # Add initial handler
        handler1 = MockToolHandler("replaceable_tool")
        add_tool_handler(handler1)

        # Verify it's registered
        assert get_tool_handler("replaceable_tool") == handler1

        # Replace with new handler
        handler2 = MockToolHandler("replaceable_tool")
        add_tool_handler(handler2)

        # Verify replacement
        assert get_tool_handler("replaceable_tool") == handler2
        assert get_tool_handler("replaceable_tool") != handler1

    def test_tool_handlers_persistence(self):
        """Test that tool handlers persist across multiple operations."""
        handler = MockToolHandler("persistent_tool")
        add_tool_handler(handler)

        # Perform multiple operations
        retrieved1 = get_tool_handler("persistent_tool")
        retrieved2 = get_tool_handler("persistent_tool")
        retrieved3 = get_tool_handler("persistent_tool")

        # All should return the same handler instance
        assert retrieved1 == handler
        assert retrieved2 == handler
        assert retrieved3 == handler
        assert retrieved1 == retrieved2 == retrieved3
