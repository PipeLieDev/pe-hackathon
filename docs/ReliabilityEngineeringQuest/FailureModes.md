# Failure Mode Documentation

This document describes how the URL Shortener API behaves when infrastructure components fail, what the user sees, and how the system recovers.

---

## 1. Database Failure (PostgreSQL Down)

| Symptom | Behavior |
|---|---|
| DB unreachable at startup | App fails to start; tables cannot be created in `create_app()` |
| DB goes down mid-request | Peewee raises `OperationalError`; Flask returns `500 Internal Server Error` |
| Connection pool exhausted | Requests block or timeout; returns 500 |

**Mitigation:**
- Peewee opens a connection per request (`before_request`) and closes it on teardown (`teardown_appcontext`), preventing connection leaks.
- The `/health` endpoint catches DB errors when updating metrics gauges and logs the error, but still returns `200 OK` (health check does not fail on metric update failure).

**Recovery:** Restart the app once PostgreSQL is available. Connections are re-established per-request.

---

## 2. Cache Failure (Valkey/Redis Down)

| Symptom | Behavior |
|---|---|
| `REDIS_URL` not set | Cache silently disabled; app works without caching |
| Valkey unreachable at startup | `_get_redis()` catches the exception, sets `_DISABLED = True`; cache becomes no-op |
| Valkey goes down mid-operation | Each `cache_get`/`cache_set`/`cache_delete` call is wrapped in `try/except`; failures are swallowed silently |

**User impact:** None. Responses are served directly from the database. The `X-Cache` header will show `MISS` on every request.

**Recovery:** Restart the app to re-enable caching (the `_DISABLED` flag is set once and not retried).

---

## 3. Application Crash / Pod Death (Kubernetes)

The app is deployed on Kubernetes with 3 replicas, rolling updates, and health probes.

| Scenario | Behavior |
|---|---|
| Unhandled exception in a request | Flask catches it and returns `500 Internal Server Error` as JSON (via flask-smorest error handling). Other requests are unaffected. |
| Pod killed (SIGKILL, OOM) | Kubernetes Deployment controller automatically restarts the pod. During restart, the remaining 2 replicas continue serving traffic. |
| Pod fails liveness probe (`/health`) | Kubelet restarts the container after 5 consecutive failures (checked every 10s, initial delay 30s). |
| Pod fails readiness probe (`/health`) | Pod is removed from the Service endpoint list — no traffic is routed to it until it passes again (checked every 5s, initial delay 15s). |
| Rolling update failure | `maxUnavailable: 1` ensures at least 2 of 3 replicas remain available during deploys. If new pods fail readiness, the rollout stalls without taking down healthy pods. |
| All 3 pods crash simultaneously | Service is fully down. Kubernetes will restart all pods, but there will be downtime until at least one becomes ready. |

**Pod anti-affinity** is configured (`topologyKey: kubernetes.io/hostname`), so replicas are spread across different nodes — a single node failure won't take down all instances.

**Resource limits:** Each pod requests 100m CPU / 256Mi memory with limits of 500m CPU / 512Mi. Exceeding memory limit triggers OOM kill and automatic restart.

---

## 4. Infrastructure Failures (Kubernetes)

| Component | Failure Mode | Impact |
|---|---|---|
| **Traefik Ingress** (K3s built-in) | Ingress controller down | No external traffic reaches the app; internal cluster traffic via Service still works |
| **Traefik Ingress** | One app pod down | Readiness probe removes unhealthy pod from endpoints; Traefik routes to healthy pods |
| **PostgreSQL (CloudNativePG)** | Primary goes down | Depends on cluster configuration; app returns 500 on all DB-dependent requests until failover completes |
| **Valkey** | Valkey pod down | No impact on app functionality; caching silently disabled, all requests served from DB |
| **Prometheus/Grafana** | Monitoring stack down | No impact on app functionality; metrics/dashboards unavailable |
| **Loki/Promtail** | Log aggregation down | No impact on app; logs still written to stdout |

---

## Summary

| Failure Type | User Sees | Auto-Recovery? |
|---|---|---|
| Database down | 500 Internal Server Error | No (manual intervention) |
| Cache down | Normal responses (cache bypassed) | No (pod restart needed to retry) |
| Single pod crash | Brief errors for in-flight requests; other pods serve traffic | Yes (Kubernetes restarts pod) |
| All pods crash | Connection refused / 503 | Yes (Kubernetes restarts all pods, but brief downtime) |
