# Failure Mode Documentation

This document describes how the URL Shortener API behaves when things go wrong, what the user sees, and how the system recovers.

---

## 1. Invalid / Garbage Input

| Scenario | Endpoint(s) | Response | Details |
|---|---|---|---|
| Missing required fields | `POST /users`, `POST /urls` | `422 Unprocessable Entity` | JSON body with validation errors from marshmallow schemas |
| Invalid email format | `POST /users`, `PUT /users/:id` | `422 Unprocessable Entity` | Schema rejects non-email strings |
| Invalid URL format | `POST /urls`, `PUT /urls/:id` | `422 Unprocessable Entity` | `validate.URL()` rejects non-URL strings |
| Wrong data types (e.g. int for username) | `POST /users` | `422 Unprocessable Entity` | Schema type validation |
| Empty JSON body `{}` | `POST /users`, `POST /urls` | `422 Unprocessable Entity` | Required fields missing |
| Non-JSON content type | All POST/PUT endpoints | `400 Bad Request` | flask-smorest rejects non-JSON payloads |
| Nonexistent resource ID | `GET/PUT/DELETE /users/:id`, `/urls/:id` | `404 Not Found` | JSON `{"message": "... not found"}` |
| Duplicate email on user create | `POST /users` | `409 Conflict` | `{"message": "Email already exists"}` |
| Referencing nonexistent user in URL create | `POST /urls` | `404 Not Found` | Checks user existence before creating |
| Referencing nonexistent URL/user in event create | `POST /events` | `404 Not Found` | Validates foreign keys before insert |

**Key behavior:** All error responses are returned as JSON. The app never exposes Python stack traces to the client.

---

## 2. Database Failure (PostgreSQL Down)

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

## 3. Cache Failure (Valkey/Redis Down)

| Symptom | Behavior |
|---|---|
| `REDIS_URL` not set | Cache silently disabled; app works without caching |
| Valkey unreachable at startup | `_get_redis()` catches the exception, sets `_DISABLED = True`; cache becomes no-op |
| Valkey goes down mid-operation | Each `cache_get`/`cache_set`/`cache_delete` call is wrapped in `try/except`; failures are swallowed silently |

**User impact:** None. Responses are served directly from the database. The `X-Cache` header will show `MISS` on every request.

**Recovery:** Restart the app to re-enable caching (the `_DISABLED` flag is set once and not retried).

---

## 4. Application Crash / Pod Death (Kubernetes)

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

## 5. Infrastructure Failures (Kubernetes)

| Component | Failure Mode | Impact |
|---|---|---|
| **Traefik Ingress** (K3s built-in) | Ingress controller down | No external traffic reaches the app; internal cluster traffic via Service still works |
| **Traefik Ingress** | One app pod down | Readiness probe removes unhealthy pod from endpoints; Traefik routes to healthy pods |
| **PostgreSQL (CloudNativePG)** | Primary goes down | Depends on cluster configuration; app returns 500 on all DB-dependent requests until failover completes |
| **Valkey** | Valkey pod down | No impact on app functionality; caching silently disabled, all requests served from DB |
| **Prometheus/Grafana** | Monitoring stack down | No impact on app functionality; metrics/dashboards unavailable |
| **Loki/Promtail** | Log aggregation down | No impact on app; logs still written to stdout |

---

## 6. Data Integrity Failures

| Scenario | Behavior |
|---|---|
| Short code collision on URL create | Retry loop generates a new code (up to 10 attempts). Returns `500` only if all 10 fail. |
| Deleting a URL with events | Events are explicitly deleted first (`Event.delete().where(Event.url_id == url.id)`), then the URL is removed. No orphaned records. |
| Deleting a user with URLs | **Not handled.** Deleting a user who owns URLs will fail with a foreign key constraint error (500). URLs must be deleted first. |

---

## Summary

| Failure Type | User Sees | Auto-Recovery? |
|---|---|---|
| Bad input | Clean JSON error (400/404/409/422) | N/A |
| Database down | 500 Internal Server Error | No (manual intervention) |
| Cache down | Normal responses (cache bypassed) | No (pod restart needed to retry) |
| Single pod crash | Brief errors for in-flight requests; other pods serve traffic | Yes (Kubernetes restarts pod) |
| All pods crash | Connection refused / 503 | Yes (Kubernetes restarts all pods, but brief downtime) |
| Short code collision | Transparent (retried internally) | Yes |
