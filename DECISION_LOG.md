# Decision Log

## Why Redis/Valkey for Caching?

**Decision:** Use Valkey (Redis-compatible) for caching layer.

**Alternatives Considered:**
- No caching (query DB directly)
- Memcached
- PostgreSQL native caching (pg_caching)

**Reasons:**
1. **Performance**: In-memory caching is 10-100x faster than DB queries
2. **TTL Support**: Built-in expiration for cache invalidation
3. **Industry Standard**: Well-understood, well-documented patterns
4. **Already Available**: Included in docker-compose stack (valkey service)
5. **Graceful Fallback**: Cache module handles missing Redis (no errors, just slower)

**Trade-offs:**
- Additional infrastructure (need to maintain Redis)
- Cache invalidation complexity
- Memory usage

---

## Why Flask + Peewee instead of Django/FastAPI?

**Decision:** Use Flask with Peewee ORM.

**Alternatives Considered:**
- Django (full-featured, heavier)
- FastAPI + SQLAlchemy (async, newer)
- Express.js + TypeScript (different stack)
- Go/Gin (different stack)

**Reasons:**
1. **Hackathon Simplicity**: Less boilerplate, faster to get started
2. **Peewee**: Lightweight, Pythonic ORM - good fit for simple CRUD
3. **flask-smorest**: Built-in OpenAPI/Swagger docs (auto-generated API docs!)
4. **Familiarity**: Team already comfortable with Flask
5. **Small Scope**: URL shortener doesn't need Django's features

**Trade-offs:**
- Less built-in functionality (auth, admin, etc.)
- Peewee less feature-rich than SQLAlchemy/Django ORM
- No async (mitigated by caching layer)

---

docker compose cannot scale like k8s

---

## Why Valkey over Redis?

**Decision:** Use Valkey (Redis fork) instead of Redis.

**Alternatives Considered:**
- Redis (original)
- KeyDB (Redis fork with multi-threading)
- DragonflyDB (modern, higher performance)

**Reasons:**
1. **Open Source Governance**: Redis moved to RSPLv2 license (SSPL) in 2024 - Valkey is fully open source (BSD)
2. **Future-Proof**: Avoid potential vendor lock-in from Redis Ltd.
3. **API Compatibility**: 100% Redis-compatible - drop-in replacement
4. **Active Development**: Backed by cloud providers, Linux Foundation
5. **No Code Changes**: Existing Redis clients work without modification

**Trade-offs:**
- Smaller community than Redis (but growing)
- Fewer third-party integrations
- Newer project (less battle-tested)

---

## Why Kubernetes over Docker Compose?

**Decision:** Deploy to Kubernetes (k3s) instead of Docker Compose for production.

**Alternatives Considered:**
- Docker Compose (simpler)
- Nomad (simpler than k8s)
- AWS ECS/Fargate (managed)
- Terraform + cloud VMs (simpler)

**Reasons:**
1. **Scaling**: Horizontal pod autoscaling, load balancing built-in
2. **Self-Healing**: Automatic restarts, health checks, node management
3. **Industry Standard**: Most common orchestrator, widely understood
4. **Declarative**: Infrastructure as Code - GitOps friendly
5. **Namespace Isolation**: Better multi-environment separation (dev/staging/prod)
6. **Rolling Updates**: Zero-downtime deployments out of the box
7. **Ephemeral Storage**: Stateless app design - pods can be replaced freely

**Trade-offs:**
- Steeper learning curve
- More complex setup
- Higher resource overhead
- Requires cluster management (k3s light-weight but still extra work)

---

## Why Prometheus + Grafana for Monitoring?

**Decision:** Use Prometheus for metrics, Grafana for visualization.

**Alternatives Considered:**
- Datadog (proprietary, expensive)
- CloudWatch (AWS-only)
- ELK Stack (more for logs than metrics)
- Self-hosted alternatives (VictoriaMetrics, Thanos)

**Reasons:**
1. **Industry Standard**: Most common in SRE/DevOps
2. **Open Source**: Free, no vendor lock-in
3. **Integrations**: Lots of exporters (DB, Redis, nginx, etc.)
4. **Grafana**: Best-in-class visualization, works with many data sources
5. **Already Configured**: docker-compose includes these services

**Trade-offs:**
- Need to understand PromQL (learning curve)
- Storage can grow large (retention policies needed)
- Push vs Pull model (Prometheus = pull)

---

## Why GitHub Actions for CI?

**Decision:** Use GitHub Actions for continuous integration.

**Alternatives Considered:**
- Jenkins (self-hosted, more setup)
- CircleCI (free tier limited)
- GitLab CI (requires GitLab)
- Travis CI (not free for private repos)

**Reasons:**
1. **Already Using GitHub**: No separate account needed
2. **Generous Free Tier**: Unlimited minutes for public repos
3. **Easy Setup**: YAML-based, lots of templates
4. **Built-in**: Integrated with PRs, branches, secrets

**Trade-offs:**
- Limited to GitHub (lock-in)
- Can hit rate limits on heavy usage
- Some features only on paid plans
