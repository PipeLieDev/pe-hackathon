# System Architecture

## Overview

A horizontally scalable web service with two Flask application instances behind an Nginx load balancer, backed by a Valkey (Redis) caching layer and a PostgreSQL database. A full observability stack (Prometheus, Grafana, Loki, Alertmanager) handles metrics, logs, and alerts.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                 CLIENTS                                 │
│   ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐   │
│   │ Browser  │  │   curl   │  │ Postman │  │  Locust  │  │  Mobile  │   │
│   └──────────┘  └──────────┘  └─────────┘  └──────────┘  └──────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          NGINX (Load Balancer)                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  upstream app_servers {                                         │   │
│   │      server app1:5000;                                          │   │
│   │      server app2:5000;                                          │   │
│   │  }                                                              │   │
│   │                                                                 │   │
│   │  server {                                                       │   │
│   │      listen 80;                                                 │   │
│   │      location / { proxy_pass http://app_servers; }              │   │
│   │  }                                                              │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                      ┌──────────────┴────────────┐
                      │                           │
                      │                           │
                      ▼                           ▼
          ┌──────────────────────┐    ┌──────────────────────┐
          │    APP INSTANCE 1    │    │    APP INSTANCE 2    │
          │   Flask + Peewee     │    │   Flask + Peewee     │
          │       :5000          │    │       :5000          │
          │                      │    │                      │
          │  GET  /health        │    │  GET  /health        │
          │  GET  /metrics       │    │  GET  /metrics       │
          │  CRUD /users/*       │    │  CRUD /users/*       │
          │  CRUD /urls/*        │    │  CRUD /urls/*        │
          │  CRUD /events/*      │    │  CRUD /events/*      │
          └───────────┬──────────┘    └───────────┬──────────┘
                      │                           │
                      ├───────────────────────────┤
                      │                           │
                      │    ┌─────── cache ────────┤
                      │    │                      │
                      │    │    HIT ──────────────┤ ◄── X-Cache: HIT header
                      │    │                      │
                      │    │    MISS ───────────► │
                      ▼    ▼                      ▼
          ┌──────────────────────┐    ┌──────────────────────┐
          │  VALKEY  (Redis)     │    │      POSTGRESQL      │
          │      :6379           │    │         :5432        │
          │                      │    │                      │
          │ · user cache         │    │  tables:             │
          │ · url  cache         │    │    users             │
          │ · list cache         │    │    urls              │
          │ TTL: 30s             │    │    events            │
          └──────────────────────┘    └──────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│                          MONITORING STACK                                 │
│                                                                           │
│  ┌───────────┐      ┌──────────┐      ┌──────────────┐      ┌──────────┐  │
│  │ Prometheus│ ◄─── │  Flask   │ ───► │ Alertmanager │ ───► │ Discord  │  │
│  │ :9090     │      │ /metrics │      │   :9093      │      │ Webhook  │  │
│  └─────┬─────┘      └──────────┘      └──────────────┘      └──────────┘  │
│        │                                                                  │
│        │     ┌──────────┐      ┌──────────┐                               │
│        └───► │ Grafana  │ ◄─── │   Loki   │ ◄──── Promtail                │
│              │  :3000   │      │  :3100   │                               │
│              └──────────┘      └──────────┘                               │
└───────────────────────────────────────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────────┐
│                                                                           │
│  DATA FLOW                                                                │
│                                                                           │
│  1. client ──► Nginx :80                                                  │
│  2. Nginx ──► app1 or app2  (round-robin)                                 │
│  3. app checks Valkey                                                     │
│       HIT  → return cached response  +  X-Cache: HIT                      │
│       MISS → query PostgreSQL → cache result → return response            │
│  4. write ops (POST/PUT/DELETE)                                           │
│       → write PostgreSQL                                                  │
│       → invalidate cache                                                  │
│       → append event log                                                  │
│  5. Prometheus scrapes /metrics every 15 s                                │
│  6. Alertmanager → Discord if threshold exceeded                          │
│  7. Promtail ships logs → Loki → Grafana                                  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────────┐
│  COMPONENT REFERENCE                                                      │
├────────────────┬──────────────────────────────────────────┬───────────────┤
│  Component     │  Role                                    │  Port         │
├────────────────┼──────────────────────────────────────────┼───────────────┤
│  Nginx         │  Load balancer                           │  80           │
│  Flask app     │  API server                              │  5000         │
│  Valkey        │  In-memory cache                         │  6379         │
│  PostgreSQL    │  Persistent storage                      │  5432         │
│  Prometheus    │  Metrics collection                      │  9090         │
│  Grafana       │  Dashboards & visualisation              │  3000         │
│  Alertmanager  │  Alert routing                           │  9093         │
│  Loki          │  Log aggregation                         │  3100         │
└────────────────┴──────────────────────────────────────────┴───────────────┘
```

---

## Components

### Nginx — Load Balancer `:80`

Entry point for all traffic. Distributes incoming requests across app instances using round-robin. Adding more instances to the upstream block is the primary horizontal scaling lever.

**Why Nginx?** It is the de facto standard for lightweight reverse proxying and load balancing. It handles connection pooling, SSL termination, and upstream health checks with minimal memory overhead — no application-layer changes are needed to scale out.

### Flask + Peewee — App Instances `:5000`

Stateless API servers. Each instance exposes the same route surface:

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/metrics` | Prometheus scrape endpoint |
| `CRUD` | `/users/*` | User resource |
| `CRUD` | `/urls/*` | URL resource |
| `CRUD` | `/events/*` | Event log resource |

Because instances are stateless, Nginx can route any request to either one without session affinity.

**Why two instances?** Running at least two instances provides basic high availability (HA). If one instance crashes or is being redeployed, Nginx continues routing to the healthy one with zero downtime. It also doubles throughput capacity for concurrent requests.

### Valkey (Redis) — Cache Layer `:6379`

Sits in front of PostgreSQL to absorb read traffic. All cached entries expire after **30 seconds** (TTL). Responses served from cache include an `X-Cache: HIT` header. Write operations (POST / PUT / DELETE) invalidate the relevant cache keys immediately to prevent stale reads.

**Why Valkey instead of Redis?** In 2024, Redis changed its license from BSD to the Server Side Public License (SSPL), which is not OSI-approved and restricts usage in managed/cloud service offerings. Valkey is a community-maintained hard fork of Redis 7.2 (the last BSD-licensed version), governed by the Linux Foundation. It is API-compatible — no code changes are needed to switch — and remains fully open source. For this project it means no licensing cost, no vendor lock-in, and no risk of future license changes affecting deployment.

### PostgreSQL — Persistent Storage `:5432`

Source of truth. Three tables:

- **users** — account records
- **urls** — URL entries
- **events** — append-only event log written on every mutation

**Why PostgreSQL?** It is battle-tested, fully ACID-compliant, and open source under the PostgreSQL License (permissive, no SSPL-style concerns). For a service with relational data and an event log that requires strong consistency guarantees, PostgreSQL is the safe default.

---

## Monitoring Stack

### Prometheus `:9090`

Scrapes `/metrics` from both app instances every **15 seconds**. Stores time-series data and evaluates alerting rules.

**Why Prometheus?** It uses a pull model, which means the monitoring system controls the scrape schedule and can detect when a target goes silent — a dead app that stops responding is itself an alert condition. It is the standard in Kubernetes and Docker ecosystems, and the `/metrics` endpoint exposed by Flask integrates with it out of the box.

### Grafana `:3000`

Visualisation layer. Queries both Prometheus (metrics) and Loki (logs) so dashboards can correlate a spike in error rate with the exact log lines that caused it.

**Why Grafana?** It unifies metrics and logs in a single UI. The alternative — separate dashboards for metrics and logs — makes debugging slower because you have to context-switch between tools. Grafana's unified query layer eliminates that.

### Loki `:3100` + Promtail

Promtail runs as a log collector alongside the app containers, tailing stdout/stderr and shipping structured log lines to Loki. Loki indexes labels (not full text) for efficient querying.

**Why Loki over the ELK stack?** Loki deliberately does not full-text index log content. It only indexes metadata labels (e.g. `app=flask`, `level=error`), which makes storage dramatically cheaper and ingestion faster. For a project at this scale, Loki's resource footprint is a fraction of what Elasticsearch would require for equivalent log volume.

### Alertmanager `:9093`

Receives firing alerts from Prometheus, deduplicates and groups them, then routes notifications to a **Discord webhook**.

**Why Discord over email or PagerDuty?** For small teams, Discord is already where coordination happens. Routing alerts there means no additional tooling cost and no context switch to check a separate alert inbox. Alertmanager's grouping and inhibition rules prevent alert storms from flooding the channel during an incident.

---

## Data Flow
```
read path
  client → Nginx → app → Valkey HIT  → response (X-Cache: HIT)
                       → Valkey MISS → PostgreSQL → cache → response

write path
  client → Nginx → app → PostgreSQL (write)
                       → Valkey (invalidate affected keys)
                       → events table (append log entry)

observability path
  app stdout  → Promtail → Loki  → Grafana
  app /metrics← Prometheus scrape → Grafana
                                  → Alertmanager → Discord
```

---

## Design Decisions Summary

| Decision | Chosen | Rejected | Reason |
|----------|--------|----------|--------|
| Cache | Valkey | Redis | Redis relicensed to SSPL in 2024; Valkey is the OSS fork, API-compatible, no licensing cost |
| Load balancer | Nginx | HAProxy, Traefik | Minimal config overhead; widely understood; sufficient for this scale |
| App instances | 2× Flask | Single instance | Basic HA — one instance can be redeployed without downtime |
| Log storage | Loki | Elasticsearch | Label-only indexing keeps storage cost low; adequate for this log volume |
| Alerting target | Discord | PagerDuty, email | Zero cost; team is already on Discord; Alertmanager grouping prevents spam |
| Metrics | Prometheus | Datadog, New Relic | Self-hosted, no per-seat cost, pull model detects silent failures |

---

## Scaling Strategy

| Axis | Approach |
|------|----------|
| **Horizontal** | Add Flask instances to Nginx upstream; no config change needed in the app |
| **Vertical** | Increase Gunicorn worker count per instance for CPU-bound workloads |
| **Cache** | Increase Valkey memory allocation or raise TTL to reduce PostgreSQL load |
| **Database** | Add PostgreSQL read replicas; route `SELECT` queries to replicas via app config |
