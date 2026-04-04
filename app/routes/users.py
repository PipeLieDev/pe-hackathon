import csv
import io
from datetime import datetime

from flask import jsonify, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from peewee import IntegrityError
from playhouse.shortcuts import chunked

from app.database import db
from app.models.user import User
from app.schemas import (
    ErrorSchema,
    UserBulkResponseSchema,
    UserSchema,
    UserUpdateSchema,
)
from app.utils import serialize_model

users_bp = Blueprint(
    "users", __name__, url_prefix="/users", description="User operations"
)


@users_bp.route("/bulk")
class UserBulk(MethodView):
    @users_bp.response(201, UserBulkResponseSchema)
    def post(self):
        """Bulk import users from CSV

        Upload a CSV file with columns: id, username, email, created_at
        """
        if "file" not in request.files:
            abort(400, message="No file provided")

        file = request.files["file"]
        stream = io.TextIOWrapper(file.stream, encoding="utf-8")
        reader = csv.DictReader(stream)

        rows = []
        for row in reader:
            rows.append(
                {
                    "id": int(row["id"]),
                    "username": row["username"],
                    "email": row["email"],
                    "created_at": row["created_at"],
                }
            )

        with db.atomic():
            for batch in chunked(rows, 100):
                User.insert_many(batch).execute()

        db.execute_sql(
            "SELECT setval(pg_get_serial_sequence(%s, 'id'), COALESCE(MAX(id), 1)) FROM users",
            ("users",),
        )

        return {"imported": len(rows)}


@users_bp.route("")
class UserList(MethodView):
    @users_bp.response(200, UserSchema(many=True))
    def get(self):
        """List all users

        Supports pagination via ?page=1&per_page=20
        """
        query = User.select().order_by(User.id)

        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)
        if page is not None and per_page is not None:
            query = query.paginate(page, per_page)

        return [serialize_model(u) for u in query]

    @users_bp.arguments(UserSchema)
    @users_bp.response(201, UserSchema)
    @users_bp.alt_response(422, schema=ErrorSchema)
    def post(self, user_data):
        """Create a new user"""
        username = user_data["username"]
        email = user_data["email"]

        try:
            user = User.create(
                username=username,
                email=email,
                created_at=datetime.now(),
            )
        except IntegrityError:
            abort(409, message="Email already exists")

        return serialize_model(user)


@users_bp.route("/<int:user_id>")
class UserDetail(MethodView):
    @users_bp.response(200, UserSchema)
    @users_bp.alt_response(404, schema=ErrorSchema)
    def get(self, user_id):
        """Get a user by ID"""
        user = User.get_or_none(User.id == user_id)
        if not user:
            abort(404, message="User not found")
        return serialize_model(user)

    @users_bp.arguments(UserUpdateSchema)
    @users_bp.response(200, UserSchema)
    @users_bp.alt_response(404, schema=ErrorSchema)
    def put(self, user_data, user_id):
        """Update a user"""
        user = User.get_or_none(User.id == user_id)
        if not user:
            abort(404, message="User not found")

        if "username" in user_data:
            user.username = user_data["username"]
        if "email" in user_data:
            user.email = user_data["email"]

        try:
            user.save()
        except IntegrityError:
            abort(409, message="Email already exists")

        return serialize_model(user)
