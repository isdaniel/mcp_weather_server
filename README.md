[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/isdaniel-mcp-weather-server-badge.png)](https://mseep.ai/app/isdaniel-mcp-weather-server)

[![smithery badge](https://smithery.ai/badge/@isdaniel/mcp_weather_server)](https://smithery.ai/server/@isdaniel/mcp_weather_server)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/mcp-weather-server)](https://pypi.org/project/mcp-weather-server/)
[![PyPI - Version](https://img.shields.io/pypi/v/mcp-weather-server)](https://pypi.org/project/mcp-weather-server/)

# Weather MCP Server

A Model Context Protocol (MCP) server that provides weather information using the Open-Meteo API.

## Features

* Get current weather information for a specified city.

## Installation

Pip Installation and Usage, This package can be installed using pip:

```bash
pip install mcp_weather_server
```

This server is designed to be installed manually by adding its configuration to the `cline_mcp_settings.json` file.

1.  Add the following entry to the `mcpServers` object in your `cline_mcp_settings.json` file:

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": [
        "-m",
        "mcp_weather_server"
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

This server provides several tools: `get_weather`, `get_weather_by_datetime_range`, and `get_current_datetime`.

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

### `get_weather_by_datetime_range`

Retrieves weather information for a specified city between start and end dates.

**Parameters:**

*   `city` (string, required): The name of the city.
*   `start_date` (string, required): Start date in format YYYY-MM-DD (ISO 8601).
*   `end_date` (string, required): End date in format YYYY-MM-DD (ISO 8601).

**Example:**

To get the weather in London between 2024-01-01 and 2024-01-07, you would use the tool like this:

```
<use_mcp_tool>
<server_name>weather</server_name>
<tool_name>get_weather_by_datetime_range</tool_name>
<arguments>
{
  "city": "London",
  "start_date": "2024-01-01",
  "end_date": "2024-01-07"
}
</arguments>
</use_mcp_tool>
```

### `get_current_datetime`

Retrieves the current time in a specified timezone.

**Parameters:**

*   `timezone_name` (string, required): IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use UTC timezone if no timezone provided by the user.

**Example:**

To get the current time in New York, you would use the tool like this:

```
<use_mcp_tool>
<server_name>weather</server_name>
<tool_name>get_current_datetime</tool_name>
<arguments>
{
  "timezone_name": "America/New_York"
}
</arguments>
</use_mcp_tool>
```

## For developers

Change Working Directory Before Running Python

```
python -m mcp_weather_server
```

Or if you want Python to find your package no matter where you run from, you can set PYTHONPATH:

```
set PYTHONPATH=C:\xxx\mcp_weather_server\src
python -m mcp_weather_server
```
