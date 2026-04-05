# MLH PE Hackathon: URL Shortener API

A URL shortener API built with Flask, Peewee ORM, and PostgreSQL. Supports user management, shortened URLs, and analytics events.

**Stack:**

- Flask
- Peewee ORM
- PostgreSQL
- Valkey
- Prometheus
- Grafana
- nginx

## Prerequisites

- **uv** — a fast Python package manager that handles Python versions, virtual environments, and dependencies automatically.
  Install it with:

  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  For other methods see the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/).
- Docker & Docker Compose

## uv Basics

`uv` manages your Python version, virtual environment, and dependencies automatically. Without manual `python -m venv` needed.

| Command | What it does |
|---------|--------------|
| `uv sync` | Install all dependencies (creates `.venv` automatically) |
| `uv run <script>` | Run a script using the project's virtual environment |
| `uv add <package>` | Add a new dependency |
| `uv remove <package>` | Remove a dependency |

## Quick Start

### Option 1: Local Development

Uses `compose.dev.yml` which runs only the infrastructure services (PostgreSQL, Valkey). Run the app yourself with `uv`.

```bash
# 1. Start dev dependencies (DB + Valkey)
docker compose -f compose.dev.yml up -d

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env

# 4. Run the server
uv run run.py

# 5. Verify
curl http://localhost:5000/health
# → {"status":"ok"}

# Stop dev dependencies when done
docker compose -f compose.dev.yml down
```

### Option 2: Full Stack with Monitoring

```bash
# Start all services including monitoring
docker compose up --build

# The app will be available at http://localhost (via nginx)
# Monitoring stack:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
# - Alertmanager: http://localhost:9093
# - Loki (logs): http://localhost:3100
```

## API Endpoints

The API is documented via Swagger UI at `/apidocs/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/users` | POST | Register a user |
| `/users` | GET | List users |
| `/urls` | POST | Create a shortened URL |
| `/urls` | GET | List URLs |
| `/urls/<short_code>` | GET | Redirect to original URL |
| `/urls/<short_code>/stats` | GET | Get URL statistics |
| `/events` | GET | List analytics events |

## Project Structure

```
mlh-pe-hackathon/
├── app/
│   ├── __init__.py          # App factory, Prometheus metrics
│   ├── database.py          # DatabaseProxy, BaseModel, connection hooks
│   ├── cache.py             # Valkey/Redis caching layer
│   ├── logging.py           # Structured JSON logging
│   ├── models/
│   │   ├── user.py          # User model
│   │   ├── url.py           # URL model
│   │   └── event.py         # Analytics event model
│   └── routes/
│       ├── __init__.py      # register_routes()
│       ├── users.py         # User endpoints
│       ├── urls.py          # URL endpoints
│       └── events.py        # Event endpoints
├── tests/                   # Unit & integration tests
├── monitoring/              # Prometheus, Grafana, Alertmanager configs
├── k8s/                     # Kubernetes manifests
├── compose.yml              # Full stack (app + monitoring)
├── compose.dev.yml          # Dev only (DB + Valkey)
├── locustfile.py            # Load testing
└── scripts/seed.py          # Seed data script
```

## Running Tests

```bash
# Start dev dependencies
docker compose -f compose.dev.yml up -d

# Create test database (first time only)
docker exec pe-hackathon-db-1 psql -U postgres -c "CREATE DATABASE hackathon_test_db;"

# Run all tests
uv run pytest

# Run with coverage (requires 70% minimum)
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=70

# Run only unit tests (no DB needed)
uv run pytest tests/unit

# Run only integration tests
uv run pytest tests/integration

# Run a specific test
uv run pytest tests/integration/test_users.py::test_name -v
```

## Load Testing

```bash
uv run locust -f locustfile.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:5000
```

## Monitoring & Observability

### Accessing Services (Full Stack)

- **App**: http://localhost (via nginx load balancer)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Alertmanager**: http://localhost:9093
- **Loki**: http://localhost:3100

### Grafana Dashboards

The project includes a pre-configured Grafana dashboard showing:
- Request rate by HTTP method
- p99 latency
- Error rates
- Application resource usage

### Alert Rules

Pre-configured alerts:
- HighErrorRateCritical (>5% errors)
- HighAppCPU (>80% CPU)
- HighMemory (>80% memory)
- NoRequests (no traffic for 5 minutes)

## Caching

The app uses Valkey (Redis-compatible) for caching:
- URL lookups are cached
- Cache hit/miss is indicated via `X-Cache` header
- Graceful fallback if Valkey is unavailable

## Kubernetes Deployment

The `k8s/` directory contains manifests for deploying to Kubernetes. See `k8s/README.md` for details.

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_HOST` | localhost | PostgreSQL host |
| `DATABASE_PORT` | 5432 | PostgreSQL port |
| `DATABASE_NAME` | hackathon_db | Database name |
| `DATABASE_USER` | postgres | Database user |
| `DATABASE_PASSWORD` | postgres | Database password |
| `REDIS_URL` | - | Valkey/Redis URL (optional) |
| `LOG_LEVEL` | INFO | Logging level |
