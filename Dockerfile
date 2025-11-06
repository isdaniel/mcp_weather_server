FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies and the package
RUN (uv venv .venv) && (. .venv/bin/activate) && (uv pip install -e .)

# Run the server in SSE mode, reading port from PORT environment variable
CMD ["uv", "run", "python", "-m", "mcp_weather_server", "--mode", "stdio"]
