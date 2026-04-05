"""
Health-check-only load test — isolates network/app overhead from DB/cache.

Usage:
  uv run locust -f locustfile_health.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:5000
"""

from locust import HttpUser, between, task


class HealthCheckUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def health(self):
        self.client.get("/health")
