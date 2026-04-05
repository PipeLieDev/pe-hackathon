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

## Why Nginx as Load Balancer?

**Decision:** Use Nginx in front of multiple Flask app instances.

**Alternatives Considered:**
- Docker Compose built-in (no)
- Flask with multiple workers (Gunicorn)
- Cloud provider LB (AWS ALB, etc.)
- HAProxy

**Reasons:**
1. **Horizontal Scaling**: Easy to add more app instances
2. **Health Checks**: Nginx can detect and skip dead containers
3. **Static Files**: Can serve them directly (future-proofing)
4. **SSL Termination**: Can handle HTTPS in one place
5. **Industry Standard**: Battle-tested, reliable
6. **Low Resource**: Minimal CPU/memory overhead

**Trade-offs:**
- Additional complexity (more services to run)
- Need to configure properly (upstream, health checks)
- Single point of failure (mitigated by running on multiple nodes in k8s)

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

## Why PostgreSQL over MySQL/MongoDB?

**Decision:** Use PostgreSQL for data storage.

**Alternatives Considered:**
- MySQL (simpler, less features)
- MongoDB (NoSQL, different query patterns)
- SQLite (not for production)
- CockroachDB (distributed, overkill)

**Reasons:**
1. **Relational Model**: URLs, Users, Events have clear relationships
2. **ACID**: Important for financial/transactional data integrity
3. **JSON Support**: Can store flexible `details` field in events table
4. **Mature**: Well-tested, great tooling
5. **Provided in Stack**: docker-compose includes postgres

**Trade-offs:**
- Schema changes require migrations
- Horizontal scaling harder than NoSQL
- Overkill for simple data (but fine for hackathon)

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