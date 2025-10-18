FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies and the package
RUN (uv venv .venv) && (. .venv/bin/activate) && (uv pip install -e .)

# Expose port (Smithery sets PORT env var to 8081)
EXPOSE 8081

# Run the server in SSE mode, reading port from PORT environment variable
CMD ["uv", "run", "python", "-m", "mcp_weather_server", "--mode", "sse", "--host", "0.0.0.0"]
