# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MLH PE Hackathon project — a URL shortener API built with Flask, Peewee ORM, and PostgreSQL. The app supports users, shortened URLs, and analytics events.

## Commands

- **Install dependencies:** `uv sync`
- **Run dev server:** `uv run run.py` (serves on `http://localhost:5000`, debug mode)
- **Add a dependency:** `uv add <package>`
- **Health check:** `curl http://localhost:5000/health`

## Architecture

- **Entry point:** `run.py` → calls `create_app()` from `app/__init__.py`
- **App factory (`app/__init__.py`):** loads `.env`, initializes DB, imports models, registers routes, defines `/health` endpoint
- **Database (`app/database.py`):** uses Peewee `DatabaseProxy` pattern — `db` is the proxy, `BaseModel` is the base class for all models. DB connections open per-request via `before_request` and close via `teardown_appcontext`
- **Models (`app/models/`):** each model in its own file, imported in `app/models/__init__.py` so Peewee registers them
- **Routes (`app/routes/`):** Flask blueprints, registered in `app/routes/__init__.py` via `register_routes(app)`
- **Config:** environment variables from `.env` (see `.env.example`); DB defaults to `hackathon_db` on `localhost:5432` with `postgres/postgres`

## Seed Data

CSV files in `seeds/` (users, urls, events) provide test data. The API must support bulk CSV import via `POST /users/bulk` (multipart/form-data).

## API Endpoints (from goals/EndpointsSpec.md)

- `GET /health` — returns `{"status": "ok"}`
- **Users:** `POST /users/bulk`, `GET /users` (paginated), `GET /users/<id>`, `POST /users`, `PUT /users/<id>`
- **URLs:** `POST /urls`, `GET /urls` (filterable by `user_id`), `GET /urls/<id>`, `PUT /urls/<id>`
- **Events:** `GET /events`

## Key Conventions

- Python 3.13, managed by `uv` (not pip/venv)
- Use `model_to_dict` from `playhouse.shortcuts` for JSON serialization
- Wrap bulk inserts in `db.atomic()` with `chunked()` for batching
- Events store a JSON `details` field
- Tables must be created explicitly via `db.create_tables([Model])`
