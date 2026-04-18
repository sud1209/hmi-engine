FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY agents/pyproject.toml agents/

# Sync dependencies
RUN uv sync --no-dev --project agents

# Install Playwright browsers
RUN uv run --project agents playwright install chromium

# Copy source code
COPY agents/src/ agents/src/

# Set working directory to the package root for execution
WORKDIR /app/agents

# Expose the port
EXPOSE 8000

# Command to run the agent runner
CMD ["uv", "run", "python", "-m", "agents.main"]
