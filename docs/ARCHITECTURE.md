# Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Browser  │  │  curl    │  │  Postman │  │  Locust  │  │  Mobile  │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
└───────┼─────────────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │             │
        └─────────────┴─────────────┴─────────────┴─────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NGINX (Load Balancer)                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  upstream app_servers {                                            │    │
│  │      server app1:5000;                                             │    │
│  │      server app2:5000;                                             │    │
│  │  }                                                                 │    │
│  │                                                                      │    │
│  │  server {                                                          │    │
│  │      listen 80;                                                    │    │
│  │      location / { proxy_pass http://app_servers; }                │    │
│  │  }                                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│      APP INSTANCE 1       │   │      APP INSTANCE 2       │
│  ┌─────────────────────┐  │   │  ┌─────────────────────┐  │
│  │   Flask + Peewee    │  │   │  │   Flask + Peewee    │  │
│  │                     │  │   │  │                     │  │
│  │  Routes:            │  │   │  │  Routes:            │  │
│  │  - /health         │  │   │  │  - /health         │  │
│  │  - /metrics        │  │   │  │  - /metrics        │  │
│  │  - /users/*        │  │   │  │  - /users/*        │  │
│  │  - /urls/*         │  │   │  │  - /urls/*         │  │
│  │  - /events/*       │  │   │  │  - /events/*       │  │
│  └──────────┬──────────┘  │   │  └──────────┬──────────┘  │
│             │             │   │             │             │
│             └─────────────┼───┴─────────────┘             │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│    VALKEY (Redis)          │   │     POSTGRESQL            │
│  ┌─────────────────────┐  │   │  ┌─────────────────────┐  │
│  │   Caching Layer     │  │   │  │   Database          │  │
│  │                     │  │   │  │                     │  │
│  │  - User cache       │  │   │  │  Tables:            │  │
│  │  - URL cache        │  │   │  │  - users            │  │
│  │  - List cache       │  │   │  │  - urls             │  │
│  │                     │  │   │  │  - events           │  │
│  │  TTL: 30s           │  │   │  │                     │  │
│  └─────────────────────┘  │   │  └─────────────────────┘  │
└───────────────────────────┘   └───────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                          MONITORING STACK                                   │
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌─────────────────┐   │
│  │Prometheus│◄───│  Flask   │───►│ Alertmanager │───►│ Discord Webhook│   │
│  │ :9090    │    │ /metrics │    │   :9093      │    │                 │   │
│  └────┬─────┘    └──────────┘    └──────────────┘    └─────────────────┘   │
│       │                                                               │     │
│       │    ┌──────────┐    ┌──────────┐                              │     │
│       └───►│ Grafana  │◄───│   Loki   │                              │     │
│            │  :3000   │    │  :3100   │◄──── Promtail                │     │
│            └──────────┘    └──────────┘                              │     │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                      │
│                                                                              │
│  1. Client request → Nginx (port 80)                                       │
│  2. Nginx load balances to app1 or app2                                    │
│  3. App checks Valkey cache:                                                │
│     - HIT: Return cached response + X-Cache: HIT header                     │
│     - MISS: Query PostgreSQL, store in cache, return response               │
│  4. Write operations (POST/PUT/DELETE):                                     │
│     - Write to PostgreSQL                                                   │
│     - Invalidate related cache entries                                     │
│     - Create event log entry                                                │
│  5. Prometheus scrapes /metrics every 15s                                  │
│  6. Alertmanager triggers alerts if thresholds exceeded                    │
│  7. Logs sent to Loki via Promtail → viewable in Grafana                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                              TECHNOLOGIES                                   │
│                                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │   Flask      │ │   Peewee     │ │  PostgreSQL  │ │  Valkey (Redis)  │   │
│  │   3.1        │ │   4.0        │ │    18        │ │     8-alpine     │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘   │
│                                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │   Nginx      │ │ Prometheus   │ │   Grafana    │ │    GitHub CI     │   │
│  │   Alpine     │ │    29        │ │    11        │ │                  │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

| Component | Purpose | Port |
|-----------|---------|------|
| **Nginx** | Load balancer, routes traffic to app instances | 80 |
| **Flask App** | API server, handles HTTP requests | 5000 |
| **Valkey** | In-memory cache for faster reads | 6379 |
| **PostgreSQL** | Persistent data storage | 5432 |
| **Prometheus** | Metrics collection & alerting | 9090 |
| **Grafana** | Visualization & dashboards | 3000 |
| **Alertmanager** | Alert routing to Discord | 9093 |
| **Loki** | Log aggregation | 3100 |

## Scaling Strategy

- **Horizontal**: Add more Flask instances to `app_servers` upstream
- **Vertical**: Increase Gunicorn workers per instance
- **Caching**: Increase Valkey memory for higher cache hit rates
- **Database**: PostgreSQL read replicas for read-heavy workloads