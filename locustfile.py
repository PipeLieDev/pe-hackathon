"""
Load test for MLH PE Hackathon URL Shortener API.

Usage:
  # Install locust first:
  pip install locust

  # Run headless (50 users, 10 spawn rate, 60s duration):
  locust -f locustfile.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:5000

  # Run with web UI (open http://localhost:8089):
  locust -f locustfile.py --host http://localhost:5000

  # Silver tier (200 users):
  locust -f locustfile.py --headless -u 200 -r 20 --run-time 60s --host http://localhost:5000

  # Gold tier (500 users):
  locust -f locustfile.py --headless -u 500 -r 50 --run-time 60s --host http://localhost:5000
"""

import random
import string

from locust import HttpUser, between, task


def random_username():
    return "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def random_email(username):
    domains = ["hackstack.io", "opswise.net", "example.com", "test.dev"]
    return f"{username}@{random.choice(domains)}"


def random_url():
    paths = ["dashboard", "profile", "settings", "home", "about", "docs", "api/v1/data"]
    return f"https://example.com/{random.choice(paths)}/{random.randint(1, 9999)}"


class URLShortenerUser(HttpUser):
    """
    Simulates a typical user of the URL shortener API.
    Weighted tasks reflect realistic usage patterns:
    - Health checks are frequent (monitoring)
    - Read operations (GET) are more common than writes
    - Create/Update are less frequent
    """

    wait_time = between(0.5, 2)  # Realistic think time between requests

    def on_start(self):
        """Create a user and a URL at the start of each simulated session."""
        self.user_id = None
        self.url_id = None
        self.short_code = None
        self._create_user()
        if self.user_id:
            self._create_url()

    # ── Setup helpers (not @task — called from on_start) ──────────────────────

    def _create_user(self):
        username = random_username()
        resp = self.client.post(
            "/users",
            json={"username": username, "email": random_email(username)},
            name="/users [POST setup]",
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            self.user_id = data.get("id")

    def _create_url(self):
        resp = self.client.post(
            "/urls",
            json={
                "user_id": self.user_id,
                "original_url": random_url(),
                "title": "Load Test URL",
            },
            name="/urls [POST setup]",
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            self.url_id = data.get("id")
            self.short_code = data.get("short_code")

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @task(10)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(8)
    def list_users(self):
        self.client.get("/users", name="/users")

    @task(6)
    def list_urls(self):
        self.client.get("/urls", name="/urls")

    @task(5)
    def list_events(self):
        self.client.get("/events", name="/events")

    @task(4)
    def get_user_by_id(self):
        if self.user_id:
            self.client.get(f"/users/{self.user_id}", name="/users/<id>")

    @task(4)
    def get_url_by_id(self):
        if self.url_id:
            self.client.get(f"/urls/{self.url_id}", name="/urls/<id>")

    @task(3)
    def list_urls_by_user(self):
        if self.user_id:
            self.client.get(f"/urls?user_id={self.user_id}", name="/urls?user_id=")

    @task(2)
    def create_user(self):
        username = random_username()
        self.client.post(
            "/users",
            json={"username": username, "email": random_email(username)},
            name="/users [POST]",
        )

    @task(2)
    def create_url(self):
        if self.user_id:
            self.client.post(
                "/urls",
                json={
                    "user_id": self.user_id,
                    "original_url": random_url(),
                    "title": "Perf Test",
                },
                name="/urls [POST]",
            )

    @task(1)
    def update_user(self):
        if self.user_id:
            self.client.put(
                f"/users/{self.user_id}",
                json={"username": random_username()},
                name="/users/<id> [PUT]",
            )

    @task(1)
    def update_url(self):
        if self.url_id:
            self.client.put(
                f"/urls/{self.url_id}",
                json={"title": "Updated by load test", "is_active": True},
                name="/urls/<id> [PUT]",
            )

    @task(1)
    def invalid_user_request(self):
        """Tests graceful error handling — expects 4xx, not a crash."""
        with self.client.post(
            "/users",
            json={"username": 12345, "email": "not-an-email"},
            name="/users [POST invalid]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (400, 422):
                resp.success()
            elif resp.status_code >= 500:
                resp.failure(f"Server crashed on invalid input: {resp.status_code}")
