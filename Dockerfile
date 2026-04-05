FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy source code
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["uv", "run", "gunicorn", "--preload", "-w", "2", "--threads", "4", "-k", "gthread", "-b", "0.0.0.0:5000", "run:app"]
