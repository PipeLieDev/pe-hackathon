def test_list_urls_empty(client):
    res = client.get("/urls")
    assert res.status_code == 200
    assert res.json == []


def test_list_urls(client, sample_url):
    res = client.get("/urls")
    assert res.status_code == 200
    assert len(res.json) == 1
    assert res.json[0]["short_code"] == "abc123"


def test_list_urls_filter_by_user(client, sample_url, sample_user):
    res = client.get(f"/urls?user_id={sample_user}")
    assert res.status_code == 200
    assert len(res.json) == 1

    res = client.get("/urls?user_id=9999")
    assert res.status_code == 200
    assert len(res.json) == 0


def test_list_urls_filter_by_is_active(client, sample_url):
    res = client.get("/urls?is_active=true")
    assert res.status_code == 200
    assert len(res.json) == 1

    res = client.get("/urls?is_active=false")
    assert res.status_code == 200
    assert len(res.json) == 0


def test_get_url(client, sample_url):
    res = client.get(f"/urls/{sample_url}")
    assert res.status_code == 200
    assert res.json["id"] == sample_url
    assert res.json["short_code"] == "abc123"
    assert res.json["original_url"] == "https://example.com"
    assert res.json["is_active"] is True


def test_get_url_not_found(client):
    res = client.get("/urls/9999")
    assert res.status_code == 404


def test_create_url(client, sample_user):
    res = client.post(
        "/urls",
        json={
            "user_id": sample_user,
            "original_url": "https://example.com/new",
            "title": "New URL",
        },
    )
    assert res.status_code == 201
    assert res.json["user_id"] == sample_user
    assert res.json["original_url"] == "https://example.com/new"
    assert res.json["title"] == "New URL"
    assert res.json["is_active"] is True
    assert len(res.json["short_code"]) == 6


def test_create_url_user_not_found(client):
    res = client.post(
        "/urls",
        json={
            "user_id": 9999,
            "original_url": "https://example.com",
            "title": "Test",
        },
    )
    assert res.status_code == 404


def test_update_url(client, sample_url):
    res = client.put(
        f"/urls/{sample_url}",
        json={"title": "Updated Title", "is_active": False},
    )
    assert res.status_code == 200
    assert res.json["title"] == "Updated Title"
    assert res.json["is_active"] is False


def test_update_url_not_found(client):
    res = client.put("/urls/9999", json={"title": "x"})
    assert res.status_code == 404


def test_delete_url(client, sample_url):
    res = client.delete(f"/urls/{sample_url}")
    assert res.status_code == 204

    res = client.get(f"/urls/{sample_url}")
    assert res.status_code == 404


def test_delete_url_not_found(client):
    res = client.delete("/urls/9999")
    assert res.status_code == 404


def test_redirect_url(client, sample_url):
    res = client.get("/urls/abc123/redirect")
    assert res.status_code == 302
    assert res.headers["Location"] == "https://example.com"


def test_redirect_url_not_found(client):
    res = client.get("/urls/nonexist/redirect")
    assert res.status_code == 404


def test_redirect_inactive_url(client, sample_url):
    """Inactive URLs should not redirect."""
    client.put(f"/urls/{sample_url}", json={"is_active": False})
    res = client.get("/urls/abc123/redirect")
    assert res.status_code == 404
