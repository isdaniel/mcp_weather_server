FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies and the package, then drop root privileges
RUN uv venv .venv && uv pip install -e . \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

# Run the server in stdio mode
CMD ["uv", "run", "python", "-m", "mcp_weather_server", "--mode", "stdio"]
