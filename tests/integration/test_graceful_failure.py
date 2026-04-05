"""
Tests for graceful failure handling (Gold tier - Reliability Engineering).

Sends garbage/invalid data to every endpoint and verifies:
1. The app returns a proper HTTP error code (not 500).
2. The response is valid JSON (not a stack trace).
"""


# --- Users endpoint ---


class TestUsersGarbageData:
    def test_post_empty_body(self, client):
        res = client.post("/users", json={})
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_no_json(self, client):
        res = client.post("/users", data="not json", content_type="text/plain")
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_invalid_email(self, client):
        res = client.post("/users", json={"username": "x", "email": "garbage"})
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_empty_username(self, client):
        res = client.post("/users", json={"username": "", "email": "a@b.com"})
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_extra_fields_rejected(self, client):
        """flask-smorest rejects unknown fields by default — no XSS via extra fields."""
        res = client.post(
            "/users",
            json={"username": "u", "email": "u@e.com", "evil": "<script>alert(1)</script>"},
        )
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_get_nonexistent_user(self, client):
        res = client.get("/users/0")
        assert res.status_code == 404
        assert res.content_type == "application/json"

    def test_get_string_id(self, client):
        res = client.get("/users/abc")
        assert res.status_code in (404, 422)
        assert res.content_type == "application/json"

    def test_put_invalid_email(self, client, sample_user):
        res = client.put(f"/users/{sample_user}", json={"email": "not-an-email"})
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_put_no_json(self, client, sample_user):
        """PUT with non-JSON on an update schema with no required fields
        is treated as an empty update — returns 200 (no fields changed)."""
        res = client.put(
            f"/users/{sample_user}", data="garbage", content_type="text/plain"
        )
        assert res.status_code == 200
        assert res.content_type == "application/json"


# --- URLs endpoint ---


class TestUrlsGarbageData:
    def test_post_empty_body(self, client):
        res = client.post("/urls", json={})
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_no_json(self, client):
        res = client.post("/urls", data="not json", content_type="text/plain")
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_invalid_url(self, client, sample_user):
        res = client.post(
            "/urls", json={"user_id": sample_user, "original_url": "not-a-url"}
        )
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_missing_user_id(self, client):
        res = client.post("/urls", json={"original_url": "https://example.com"})
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_missing_url(self, client, sample_user):
        res = client.post("/urls", json={"user_id": sample_user})
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_string_user_id(self, client):
        res = client.post(
            "/urls", json={"user_id": "abc", "original_url": "https://example.com"}
        )
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_nonexistent_user(self, client):
        res = client.post(
            "/urls", json={"user_id": 99999, "original_url": "https://example.com"}
        )
        assert res.status_code == 404
        assert res.content_type == "application/json"

    def test_get_string_id(self, client):
        res = client.get("/urls/abc")
        assert res.status_code in (404, 422)
        assert res.content_type == "application/json"

    def test_put_invalid_url(self, client, sample_url):
        res = client.put(f"/urls/{sample_url}", json={"original_url": "not-a-url"})
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_put_no_json(self, client, sample_url):
        """PUT with non-JSON on an update schema with no required fields
        is treated as an empty update — returns 200 (no fields changed)."""
        res = client.put(
            f"/urls/{sample_url}", data="garbage", content_type="text/plain"
        )
        assert res.status_code == 200
        assert res.content_type == "application/json"

    def test_redirect_nonexistent_code(self, client):
        res = client.get("/urls/zzzzzzzzz/redirect")
        assert res.status_code == 404
        assert res.content_type == "application/json"


# --- Events endpoint ---


class TestEventsGarbageData:
    def test_post_empty_body(self, client):
        """Empty event body — missing required fields returns 422."""
        res = client.post("/events", json={})
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_no_json(self, client):
        """Non-JSON content passes schema (no required fields) but fails at DB level."""
        res = client.post("/events", data="not json", content_type="text/plain")
        assert res.status_code == 422
        assert res.content_type == "application/json"

    def test_post_nonexistent_url(self, client, sample_user):
        res = client.post(
            "/events",
            json={"url_id": 99999, "user_id": sample_user, "event_type": "click"},
        )
        assert res.status_code == 404
        assert res.content_type == "application/json"

    def test_post_nonexistent_user(self, client, sample_url):
        res = client.post(
            "/events",
            json={"url_id": sample_url, "user_id": 99999, "event_type": "click"},
        )
        assert res.status_code == 404
        assert res.content_type == "application/json"

    def test_post_string_ids(self, client):
        res = client.post(
            "/events",
            json={"url_id": "abc", "user_id": "xyz", "event_type": "click"},
        )
        assert res.status_code == 422
        assert res.content_type == "application/json"


# --- Health & nonexistent routes ---


class TestMiscGarbageData:
    def test_health_returns_json(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        assert res.json["status"] == "ok"

    def test_nonexistent_route(self, client):
        res = client.get("/this/does/not/exist")
        assert res.status_code == 404

    def test_method_not_allowed(self, client):
        res = client.patch("/users")
        assert res.status_code == 405
