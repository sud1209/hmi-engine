FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY README.md .
# We need the workspace root pyproject.toml as well if we use workspace mode
# But for a single service Dockerfile, we can just copy the specific package
COPY mcp-server/pyproject.toml mcp-server/

# Sync dependencies
RUN uv sync --no-dev --project mcp-server

# Copy source code
COPY mcp-server/src/ mcp-server/src/
COPY mcp-server/data/ mcp-server/data/

# Set working directory to the package root for execution
WORKDIR /app/mcp-server

# Expose the port
EXPOSE 8001

# Command to run the server
CMD ["uv", "run", "python", "-m", "mcp_server.main"]
