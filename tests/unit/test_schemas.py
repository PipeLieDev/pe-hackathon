from app.schemas import UserSchema, UserUpdateSchema


def test_user_schema_valid():
    schema = UserSchema()
    result = schema.load({"username": "testuser", "email": "test@example.com"})
    assert result["username"] == "testuser"
    assert result["email"] == "test@example.com"


def test_user_schema_missing_username():
    schema = UserSchema()
    errors = schema.validate({"email": "test@example.com"})
    assert "username" in errors


def test_user_schema_missing_email():
    schema = UserSchema()
    errors = schema.validate({"username": "testuser"})
    assert "email" in errors


def test_user_schema_invalid_email():
    schema = UserSchema()
    errors = schema.validate({"username": "testuser", "email": "not-an-email"})
    assert "email" in errors


def test_user_update_schema_partial():
    schema = UserUpdateSchema()
    result = schema.load({"username": "updated"})
    assert result == {"username": "updated"}


def test_user_update_schema_empty():
    schema = UserUpdateSchema()
    result = schema.load({})
    assert result == {}
