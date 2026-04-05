# MLH PE Hackathon: URL Shortener API

A resilient URL shortener service built for production.

**Tech Stack:**

![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white) ![Peewee ORM](https://img.shields.io/badge/Peewee_ORM-3776AB?style=for-the-badge&logo=python&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white) ![Valkey](https://img.shields.io/badge/Valkey-DC382D?style=for-the-badge&logo=redis&logoColor=white) ![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white) ![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white) ![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![uv](https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=uv&logoColor=white)

**CI Status:**

[![codecov](https://img.shields.io/codecov/c/gh/PipeLieDev/pe-hackathon?token=ZMCM5CV9CQ&style=for-the-badge&logo=codecov&logoColor=white&label=Coverage)](https://codecov.io/gh/PipeLieDev/pe-hackathon) [![Build and push Docker image](https://img.shields.io/github/actions/workflow/status/PipeLieDev/pe-hackathon/build.yml?branch=main&label=Build+%26+Push+Docker&style=for-the-badge&logo=docker&logoColor=white)](https://github.com/PipeLieDev/pe-hackathon/actions/workflows/build.yml) [![Run tests and collect coverage](https://img.shields.io/github/actions/workflow/status/PipeLieDev/pe-hackathon/ci.yml?branch=main&label=Tests+%26+Coverage&style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/PipeLieDev/pe-hackathon/actions/workflows/ci.yml)

## Index

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Load Testing](#load-testing)
- [Monitoring & Observability](#monitoring--observability)
- [Deployment](#deployment)
- [AI Usage](AI_USAGE.md)
- [Architecture](/docs/ARCHITECTURE.md)
- [License](#license)

## Prerequisites

### 1. uv

A fast Python package manager that handles Python versions, virtual environments, and dependencies automatically — no manual `python -m venv` needed.

**macOS / Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

> [!note]
> For other install methods, see the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/).

#### uv Cheatsheet

| Command | What it does |
|---|---|
| `uv sync` | Install all dependencies (creates `.venv` automatically) |
| `uv run <script>` | Run a script inside the project virtualenv |
| `uv add <package>` | Add a new dependency |
| `uv remove <package>` | Remove a dependency |

### 2. Docker & Docker Compose

Required for running infrastructure services (PostgreSQL, Valkey) and the full monitoring stack.

## Configuration

Copy `.env.example` to `.env` before running anything:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `DATABASE_HOST` | `localhost` | PostgreSQL host |
| `DATABASE_PORT` | `5432` | PostgreSQL port |
| `DATABASE_NAME` | `hackathon_db` | Database name |
| `DATABASE_USER` | `postgres` | Database user |
| `DATABASE_PASSWORD` | `postgres` | Database password |
| `REDIS_URL` | — | Valkey/Redis connection URL (optional) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Quick Start

### Option 1: Local Development

Runs only PostgreSQL + Valkey via Docker. You run the Flask app yourself with `uv`.

**1. Start dev dependencies**

```bash
docker compose -f compose.dev.yml up -d
```

**2. Install dependencies**

```bash
uv sync
```

**3. Configure environment**

```bash
cp .env.example .env
```

**4. Run the server**

```bash
uv run run.py
```

**5. Verify**

```bash
curl http://localhost:5000/health
# → {"status":"ok"}
```

**6. Stop when done**

```bash
docker compose -f compose.dev.yml down
```

### Option 2: Full Stack with Monitoring

Everything containerized: app, nginx, Prometheus, Grafana, Loki, and Alertmanager.

**1. Start all services**

```bash
docker compose up --build -d
```

**2. Verify**

```bash
curl http://localhost/health
# → {"status":"ok"}
```

**3. Stop when done**

```bash
docker compose down
```

> [!note]
> Access the app at `http://localhost` via nginx. Monitoring URLs are listed in the [Monitoring & Observability](#monitoring--observability) section.

## API Endpoints

Full interactive docs available at `/apidocs/` via Swagger UI.

| Endpoint | Method | Description |
|---|---|---|
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
│   │   ├── user.py
│   │   ├── url.py
│   │   └── event.py
│   └── routes/
│       ├── __init__.py      # register_routes()
│       ├── users.py
│       ├── urls.py
│       └── events.py
├── tests/                   # Unit & integration tests
├── monitoring/              # Prometheus, Grafana, Alertmanager configs
├── k8s/                     # Kubernetes manifests
├── compose.yml              # Full stack (app + monitoring)
├── compose.dev.yml          # Dev only (DB + Valkey)
├── locustfile.py            # Load testing
└── scripts/seed.py          # Seed data script
```

## Running Tests

Make sure dev dependencies are running before starting. If not, run `docker compose -f compose.dev.yml up -d` first.

**1. Create test database (first time only)**

```bash
docker exec pe-hackathon-db-1 psql -U postgres -c "CREATE DATABASE hackathon_test_db;"
```

**2. Run all tests**

```bash
uv run pytest
```

**3. Run with coverage (70% minimum required)**

```bash
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```

**4. Unit tests only (no DB needed)**

```bash
uv run pytest tests/unit
```

**5. Integration tests only**

```bash
uv run pytest tests/integration
```

**6. Run a specific test**

```bash
uv run pytest tests/integration/test_users.py::test_name -v
```

## Load Testing

```bash
uv run locust -f locustfile.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:5000
```

## Monitoring & Observability

Available when running the full stack via `docker compose up --build`.

| Service | URL | Notes |
|---|---|---|
| App | http://localhost | Via nginx load balancer |
| Prometheus | http://localhost:9090 | |
| Grafana | http://localhost:30030 | Default credentials: admin / admin |
| Alertmanager | http://localhost:9093 | |
| Loki | http://localhost:3100 | |

### Grafana Dashboards

Pre-configured dashboard includes: request rate by HTTP method, p99 latency, error rates, and application resource usage.

### Alert Rules

| Alert | Condition |
|---|---|
| `HighErrorRateCritical` | Error rate > 5% |
| `HighAppCPU` | CPU usage > 80% |
| `HighMemory` | Memory usage > 80% |
| `NoRequests` | No traffic for 5 minutes |

## Deployment

### Docker Compose (recommended for development)

```bash
# Start the full stack
docker compose up --build -d

# Stop the stack
docker compose down
```

**Rollback:** rebuild from the previous image.

```bash
docker compose stop
docker compose up -d --build
```

### Kubernetes (production)

See [docs/k8s-setup.md](docs/k8s-setup.md) for the full K3s cluster setup guide.

**Deploy**

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres-cluster.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml
```

**Deploy monitoring**

```bash
./scripts/deploy-monitoring.sh
```

**Check status**

```bash
kubectl get pods -n url-shortener
```

**Rollback**

```bash
kubectl rollout undo deployment/url-shortener -n url-shortener
kubectl rollout status deployment/url-shortener -n url-shortener
```

## License

MIT
