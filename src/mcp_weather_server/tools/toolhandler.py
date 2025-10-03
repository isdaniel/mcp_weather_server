"""
Base ToolHandler class for extensible MCP tool management.
This follows the architecture pattern from mcp-gsuite for easy extension.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)


class ToolHandler(ABC):
    """
    Abstract base class for all MCP tool handlers.
    
    This provides a consistent interface for tool registration,
    description, and execution across the MCP weather server.
    """
    
    def __init__(self, tool_name: str):
        """
        Initialize a tool handler with a unique name.
        
        Args:
            tool_name: Unique identifier for this tool
        """
        self.name = tool_name
    
    @abstractmethod
    def get_tool_description(self) -> Tool:
        """
        Return the MCP Tool description for this handler.
        
        This method must be implemented by each tool handler to define
        the tool's schema, parameters, and documentation.
        
        Returns:
            Tool: MCP Tool object with schema and metadata
        """
        raise NotImplementedError("Each tool handler must implement get_tool_description")
    
    @abstractmethod
    async def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute the tool with provided arguments.
        
        This method contains the actual logic for the tool's functionality.
        Note: This method should be async to support API calls.
        
        Args:
            args: Dictionary of arguments passed to the tool
            
        Returns:
            Sequence of MCP content objects (text, image, or embedded resources)
            
        Raises:
            RuntimeError: For missing required arguments or execution errors
        """
        raise NotImplementedError("Each tool handler must implement run_tool")
    
    def validate_required_args(self, args: dict, required_fields: list[str]) -> None:
        """
        Validate that all required arguments are present.
        
        Args:
            args: Dictionary of provided arguments
            required_fields: List of required field names
            
        Raises:
            RuntimeError: If any required field is missing
        """
        missing_fields = [field for field in required_fields if field not in args]
        if missing_fields:
            raise RuntimeError(f"Missing required arguments: {', '.join(missing_fields)}")
