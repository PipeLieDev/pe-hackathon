import heapq
import os
import time

from peewee import DatabaseProxy, Model
from playhouse.pool import PooledPostgresqlDatabase

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    database = PooledPostgresqlDatabase(
        os.environ.get("DATABASE_NAME", "hackathon_db"),
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        user=os.environ.get("DATABASE_USER", "postgres"),
        password=os.environ.get("DATABASE_PASSWORD", "postgres"),
        max_connections=int(os.environ.get("DATABASE_MAX_CONNECTIONS", 20)),
        stale_timeout=300,
        timeout=10,
    )
    db.initialize(database)

    # Pre-fill the connection pool so startup traffic doesn't thundering-herd PostgreSQL
    min_connections = int(os.environ.get("DATABASE_MIN_CONNECTIONS", 10))
    warm_conns = []
    for _ in range(min_connections):
        try:
            conn = super(PooledPostgresqlDatabase, database)._connect()
            ts = time.time()
            database._heap_counter += 1
            heapq.heappush(database._connections, (ts, database._heap_counter, conn))
            warm_conns.append(conn)
        except Exception:
            break

    pid = os.getpid()
    app.logger.info(
        "Connection pool pre-filled: %d/%d connections ready (worker pid=%d, max=%d)",
        len(warm_conns), min_connections, pid,
        int(os.environ.get("DATABASE_MAX_CONNECTIONS", 20)),
    )

    @app.before_request
    def _db_connect():
        from flask import request
        # Skip DB connection for endpoints that don't need it
        if request.path in ("/health", "/metrics"):
            return
        db.connect(reuse_if_open=True)

    @app.teardown_request
    def _db_close(exc):
        if not db.is_closed():
            db.close()
