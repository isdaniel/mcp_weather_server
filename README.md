[![smithery badge](https://smithery.ai/badge/@isdaniel/mcp_weather_server)](https://smithery.ai/server/@isdaniel/mcp_weather_server)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/mcp-weather-server)](https://pypi.org/project/mcp-weather-server/)
[![PyPI - Version](https://img.shields.io/pypi/v/mcp-weather-server)](https://pypi.org/project/mcp-weather-server/)

# Weather MCP Server

A Model Context Protocol (MCP) server that provides weather information using the Open-Meteo API.

## Features

* Get current weather information for a specified city.

## Installation

This server is designed to be installed manually by adding its configuration to the `cline_mcp_settings.json` file.

1.  Add the following entry to the `mcpServers` object in your `cline_mcp_settings.json` file:

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": [
        "mcp_weather_server/server.py"
      ],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

2. Save the `cline_mcp_settings.json` file.

## Configuration

This server does not require an API key. It uses the Open-Meteo API, which is free and open-source.

## Usage

This server provides a single tool: `get_weather`.

### `get_weather`

Retrieves the current weather information for a given city.

**Parameters:**

*   `city` (string, required): The name of the city.

**Example:**

To get the weather in Taipei, you would use the tool like this:

```
<use_mcp_tool>
<server_name>weather</server_name>
<tool_name>get_weather</tool_name>
<arguments>
{
  "city": "Taipei"
}
</arguments>
</use_mcp_tool>
```

## Pip Installation and Usage

This package can be installed using pip:

```bash
pip install mcp_weather_server
```

After installation, you can use the `mcp_weather_server` command-line tool:

```bash
mcp_weather_server --city "Your City"
```

Replace `"Your City"` with the city you want to get weather information for.
