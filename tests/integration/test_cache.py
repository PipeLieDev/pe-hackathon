import pytest

import app.cache as cache_mod


@pytest.fixture
def redis_client():
    """Return the raw Redis client, skip if unavailable."""
    r = cache_mod._get_redis()
    if r is None:
        pytest.skip("Redis not available")
    return r


# ── Users caching ──


class TestUsersCaching:
    def test_get_user_miss_then_hit(self, client, sample_user, redis_client):
        res1 = client.get(f"/users/{sample_user}")
        assert res1.status_code == 200
        assert res1.headers["X-Cache"] == "MISS"

        res2 = client.get(f"/users/{sample_user}")
        assert res2.status_code == 200
        assert res2.headers["X-Cache"] == "HIT"
        assert res2.json == res1.json

    def test_list_users_miss_then_hit(self, client, sample_user, redis_client):
        res1 = client.get("/users?page=1&per_page=10")
        assert res1.status_code == 200
        assert res1.headers["X-Cache"] == "MISS"

        res2 = client.get("/users?page=1&per_page=10")
        assert res2.status_code == 200
        assert res2.headers["X-Cache"] == "HIT"

    def test_update_user_invalidates_cache(self, client, sample_user, redis_client):
        # Warm the cache
        client.get(f"/users/{sample_user}")
        res = client.get(f"/users/{sample_user}")
        assert res.headers["X-Cache"] == "HIT"

        # Update should invalidate
        client.put(f"/users/{sample_user}", json={"username": "changed"})

        res = client.get(f"/users/{sample_user}")
        assert res.headers["X-Cache"] == "MISS"
        assert res.json["username"] == "changed"

    def test_update_user_invalidates_list_cache(self, client, sample_user, redis_client):
        # Warm list cache
        client.get("/users?page=1&per_page=10")
        res = client.get("/users?page=1&per_page=10")
        assert res.headers["X-Cache"] == "HIT"

        # Update should clear list cache
        client.put(f"/users/{sample_user}", json={"username": "changed"})

        res = client.get("/users?page=1&per_page=10")
        assert res.headers["X-Cache"] == "MISS"


# ── URLs caching ──


class TestUrlsCaching:
    def test_get_url_miss_then_hit(self, client, sample_url, redis_client):
        res1 = client.get(f"/urls/{sample_url}")
        assert res1.status_code == 200
        assert res1.headers["X-Cache"] == "MISS"

        res2 = client.get(f"/urls/{sample_url}")
        assert res2.status_code == 200
        assert res2.headers["X-Cache"] == "HIT"
        assert res2.json == res1.json

    def test_list_urls_miss_then_hit(self, client, sample_url, redis_client):
        res1 = client.get("/urls?page=1&per_page=10")
        assert res1.status_code == 200
        assert res1.headers["X-Cache"] == "MISS"

        res2 = client.get("/urls?page=1&per_page=10")
        assert res2.status_code == 200
        assert res2.headers["X-Cache"] == "HIT"

    def test_update_url_invalidates_cache(self, client, sample_url, redis_client):
        # Warm the cache
        client.get(f"/urls/{sample_url}")
        res = client.get(f"/urls/{sample_url}")
        assert res.headers["X-Cache"] == "HIT"

        # Update should invalidate
        client.put(f"/urls/{sample_url}", json={"title": "Changed"})

        res = client.get(f"/urls/{sample_url}")
        assert res.headers["X-Cache"] == "MISS"
        assert res.json["title"] == "Changed"

    def test_update_url_invalidates_list_cache(self, client, sample_url, redis_client):
        # Warm list cache
        client.get("/urls?page=1&per_page=10")
        res = client.get("/urls?page=1&per_page=10")
        assert res.headers["X-Cache"] == "HIT"

        # Update should clear list cache
        client.put(f"/urls/{sample_url}", json={"title": "Changed"})

        res = client.get("/urls?page=1&per_page=10")
        assert res.headers["X-Cache"] == "MISS"


# ── Cache keys stored correctly ──


class TestCacheKeys:
    def test_user_detail_stored_in_redis(self, client, sample_user, redis_client):
        client.get(f"/users/{sample_user}")
        assert redis_client.get(f"users:{sample_user}") is not None

    def test_url_detail_stored_in_redis(self, client, sample_url, redis_client):
        client.get(f"/urls/{sample_url}")
        assert redis_client.get(f"urls:{sample_url}") is not None

    def test_different_query_params_different_keys(self, client, sample_user, redis_client):
        client.get("/users?page=1&per_page=5")
        client.get("/users?page=1&per_page=10")
        keys = redis_client.keys("users:list:*")
        assert len(keys) == 2
