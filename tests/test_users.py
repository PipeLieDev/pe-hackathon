import io


def test_list_users_empty(client):
    res = client.get("/users")
    assert res.status_code == 200
    assert res.json == []


def test_list_users(client, sample_user):
    res = client.get("/users")
    assert res.status_code == 200
    assert len(res.json) == 1
    assert res.json[0]["username"] == "testuser"


def test_list_users_pagination(client, sample_user):
    res = client.get("/users?page=1&per_page=1")
    assert res.status_code == 200
    assert len(res.json) == 1

    res = client.get("/users?page=2&per_page=1")
    assert res.status_code == 200
    assert len(res.json) == 0


def test_get_user(client, sample_user):
    res = client.get(f"/users/{sample_user}")
    assert res.status_code == 200
    assert res.json["id"] == sample_user
    assert res.json["username"] == "testuser"
    assert res.json["email"] == "test@example.com"


def test_get_user_not_found(client):
    res = client.get("/users/9999")
    assert res.status_code == 404


def test_create_user(client):
    res = client.post(
        "/users",
        json={"username": "newuser", "email": "new@example.com"},
    )
    assert res.status_code == 201
    assert res.json["username"] == "newuser"
    assert res.json["email"] == "new@example.com"
    assert "id" in res.json
    assert "created_at" in res.json


def test_create_user_invalid_data(client):
    res = client.post("/users", json={"username": 123, "email": "a@b.com"})
    assert res.status_code == 422


def test_create_user_missing_fields(client):
    res = client.post("/users", json={"username": "nomail"})
    assert res.status_code == 422


def test_create_user_duplicate(client, sample_user):
    res = client.post(
        "/users",
        json={"username": "testuser", "email": "other@example.com"},
    )
    assert res.status_code == 409


def test_update_user(client, sample_user):
    res = client.put(
        f"/users/{sample_user}",
        json={"username": "updated_username"},
    )
    assert res.status_code == 200
    assert res.json["username"] == "updated_username"
    assert res.json["email"] == "test@example.com"


def test_update_user_not_found(client):
    res = client.put("/users/9999", json={"username": "x"})
    assert res.status_code == 404


def test_bulk_import(client):
    csv_data = "id,username,email,created_at\n10,bulkuser1,bulk1@test.com,2025-01-01 00:00:00\n11,bulkuser2,bulk2@test.com,2025-01-01 00:00:00\n"
    data = {"file": (io.BytesIO(csv_data.encode()), "users.csv")}
    res = client.post(
        "/users/bulk",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 201
    assert res.json["imported"] == 2
