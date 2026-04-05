# Capacity Planning

## Current Deployment

| Component | Instances | CPU (req/limit) | Memory (req/limit) | Storage |
|---|---|---|---|---|
| Flask app pods | 3 replicas | 2 / 4 cores | 2Gi / 4Gi | — |
| PostgreSQL (CNPG) | 3 instances | 500m / 2 cores | 1Gi / 2Gi | 5Gi per instance |
| Valkey master | 1 | 250m / 500m | 256Mi / 512Mi | — (no persistence) |
| Valkey replicas | 3 | 250m / 500m | 256Mi / 512Mi | — |
| Valkey sentinels | 3 | 250m / 500m | 256Mi / 512Mi | — |

**Physical infrastructure:** 3x Dell Optiplex nodes running K3s.

## Capacity Assumptions

### Request Throughput

- Each Flask pod runs **2 Gunicorn workers** with **4 threads each** = 8 concurrent requests per pod.
- With 3 replicas: **24 concurrent requests** cluster-wide.
- Cache-hit responses (Valkey TTL: 30s) bypass the database entirely, so read-heavy workloads can sustain significantly higher throughput than write-heavy ones.

### Database Connections

| Parameter | Value |
|---|---|
| PostgreSQL `max_connections` | 200 |
| Pool `max_connections` per worker | 20 |
| Pool `min_connections` per worker | 10 (pre-filled on startup) |
| Stale timeout | 300s |
| **Total potential connections** | 3 pods x 2 workers x 20 = **120** |
| **Headroom** | 80 connections (for superuser, migrations, monitoring) |

### Cache Layer

- Valkey is used as a **volatile cache only** (no persistence, no durability guarantee).
- TTL is **30 seconds** for all cached entries.
- Cache misses fall through to PostgreSQL transparently.
- If Valkey is completely unavailable, the app degrades gracefully — all reads go directly to PostgreSQL.

### Storage

- PostgreSQL: **5Gi per instance** (15Gi total across the 3-instance CNPG cluster).
- Prometheus: **7-day retention** for time-series metrics.
- Loki: persistent volume for log storage (indexed by labels only, not full-text).

## Known Limits

### Hard Limits

| Limit | Value | What happens when exceeded |
|---|---|---|
| PostgreSQL max connections | 200 | New connections are refused; requests fail with connection errors |
| DB pool per worker | 20 | Requests queue for up to 10s (`timeout=10`), then fail |
| PostgreSQL storage | 5Gi per instance | Writes fail; CNPG may fence the cluster |
| Node count | 3 physical machines | No more pods can be scheduled if all nodes are at resource capacity |

### Scaling Ceilings

| Scenario | Replicas | Workers | Pool Max | Total DB Connections | Fits in 200? |
|---|---|---|---|---|---|
| Current | 3 | 2 | 20 | 120 | Yes (80 headroom) |
| 5 replicas | 5 | 2 | 20 | 200 | Barely (no headroom) |
| 6+ replicas | 6 | 2 | 20 | 240 | No |
| 4 workers/pod | 3 | 4 | 20 | 240 | No |

**The primary scaling bottleneck is PostgreSQL connection count.** Scaling beyond 5 replicas or increasing workers per pod requires either raising `max_connections` or introducing a connection pooler (PgBouncer).

### Monitoring Thresholds (Alerting)

These alerts fire before limits are hit:

| Alert | Threshold |
|---|---|
| HighCPUUsage | > 90% CPU utilization |
| HighAppCPU | Process CPU > 80% for 3m |
| HighMemory | Memory > 512MB |
| HighLatency | p95 response time > 2s |
| HighErrorRate | > 5% error rate over 5m |
| HighErrorRateCritical | > 25% 5xx error rate |

## Scaling Recommendations

### Short-term (within current hardware)

1. **Increase app replicas** up to 5 (max before DB connection exhaustion).
2. **Raise Valkey TTL** beyond 30s for read-heavy workloads to reduce PostgreSQL pressure.
3. **Add read replicas** via CNPG `-ro` service endpoint for SELECT queries.

### Medium-term (requires configuration changes)

1. **Introduce PgBouncer** in front of PostgreSQL to multiplex connections (enables 10+ app replicas without raising `max_connections`).
2. **Increase PostgreSQL `max_connections`** if PgBouncer is not yet viable (~5-10MB additional memory per 100 connections).
3. **Make `DATABASE_MAX_CONNECTIONS` explicit** in the Kubernetes ConfigMap instead of relying on the code default.

### Long-term (requires hardware changes)

1. **Add nodes** to the K3s cluster to schedule more pods.
2. **Increase PostgreSQL storage** beyond 5Gi as the URL and event tables grow.
3. **Dedicated database nodes** — move PostgreSQL to nodes with more memory/disk to avoid resource contention with app pods.
