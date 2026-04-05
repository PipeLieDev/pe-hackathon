# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MLH PE Hackathon project — a URL shortener API built with Flask, Peewee ORM, and PostgreSQL. The app supports users, shortened URLs, and analytics events. Uses Valkey (Redis-compatible) for caching, Prometheus + Grafana for monitoring, and nginx for load balancing.

## Commands

- **Install dependencies:** `uv sync` (use `uv sync --dev` to include test/dev deps)
- **Run dev server:** `uv run run.py` (serves on `http://localhost:5000`, debug mode)
- **Add a dependency:** `uv add <package>`
- **Run all tests:** `uv run pytest`
- **Run tests with coverage:** `uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=70`
- **Run a single test file:** `uv run pytest tests/integration/test_users.py`
- **Run a single test:** `uv run pytest tests/integration/test_users.py::test_name -v`
- **Run only unit tests:** `uv run pytest tests/unit/`
- **Run only integration tests:** `uv run pytest tests/integration/`
- **Load testing:** `uv run locust -f locustfile.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:5000`
- **Docker full stack:** `docker compose up --build` (app on port 80 via nginx, Grafana on 3000, Prometheus on 9090)
- **Seed data:** `uv run python scripts/seed.py`

## Architecture

- **Entry point:** `run.py` → calls `create_app()` from `app/__init__.py`
- **App factory (`app/__init__.py`):** loads `.env`, configures structured logging, sets up flask-smorest (OpenAPI/Swagger UI at `/apidocs/`), initializes DB, registers routes, defines `/health` and `/metrics` endpoints. Exports Prometheus counters/gauges used by route handlers.
- **Database (`app/database.py`):** uses Peewee `DatabaseProxy` pattern — `db` is the proxy, `BaseModel` is the base class for all models. DB connections open per-request via `before_request` and close via `teardown_appcontext`.
- **Models (`app/models/`):** each model in its own file (User, Url, Event), imported in `app/models/__init__.py` so Peewee registers them
- **Routes (`app/routes/`):** flask-smorest `Blueprint` classes registered via `register_routes(api)` in `app/routes/__init__.py`. Routes use marshmallow schemas from `app/schemas.py` for request validation and response serialization.
- **Caching (`app/cache.py`):** Valkey/Redis cache with graceful fallback — if `REDIS_URL` is unset or Valkey is down, caching silently becomes a no-op. Provides `cache_get`, `cache_set`, `cache_delete`, `cache_delete_pattern`. Responses include `X-Cache: HIT/MISS` header.
- **Logging (`app/logging.py`):** structlog + python-json-logger for structured JSON logging
- **Config:** environment variables from `.env` (see `.env.example`); DB defaults to `hackathon_db` on `localhost:5432` with `postgres/postgres`. `REDIS_URL` optional (e.g., `redis://localhost:6379/0`).

## Testing

- Tests require a running PostgreSQL instance with a `hackathon_test_db` database and a Valkey/Redis instance
- **Session-scoped** app fixture creates the test database tables once; **autouse** `clean_tables` fixture truncates all tables between integration tests
- Tests use Redis DB index 1 (`redis://localhost:6379/1`) to avoid colliding with dev data
- CI enforces **70% minimum code coverage** (`--cov-fail-under=70`)

## Infrastructure

- **Docker Compose (`compose.yml`):** runs 2 app instances behind nginx load balancer, plus PostgreSQL, Valkey, Prometheus, Alertmanager, Grafana, Loki, and Promtail
- **Kubernetes (`k8s/`):** deployment manifests for the full stack. `k8s/monitoring/` has workload YAMLs (Deployments, Services, RBAC) only — ConfigMaps are generated from `monitoring/` source files at deploy time.
- **Monitoring configs (`monitoring/`):** single source of truth for all monitoring configs. Base files (e.g., `prometheus.yml`) are used by Docker Compose; `*.k8s.yml` variants are used for k8s. Shared configs (`alertmanager.yml`, `alert_rules.yml`) have one file for both environments.
- **CI (`.github/workflows/ci.yml`):** runs tests with PostgreSQL + Valkey service containers on push to `main`/`dev/*` and PRs to `main`
- **Deploy (`.github/workflows/deploy.yml`):** deploys app to k3s on push to main (via build workflow) or manual dispatch
- **Deploy Monitoring (`.github/workflows/deploy-monitoring.yml`):** deploys monitoring stack to k3s. Auto-triggers after app deploy by default; comment out the `workflow_run` block to switch to manual-only

## Key Conventions

- Python 3.13, managed by `uv` (not pip/venv)
- Use `model_to_dict` from `playhouse.shortcuts` for JSON serialization
- Wrap bulk inserts in `db.atomic()` with `chunked()` for batching
- Events store a JSON `details` field
- Tables must be created explicitly via `db.create_tables([Model])`
- Prometheus metrics: import counters/gauges from `app/__init__.py` (e.g., `URL_CREATED`, `USER_REGISTERED`) and call `.inc()` in route handlers
