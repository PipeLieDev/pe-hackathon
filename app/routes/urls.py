from datetime import datetime

from flask import redirect, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from peewee import IntegrityError

from app import URL_CREATED
from app.cache import cache_delete, cache_delete_pattern, cache_get, cache_set
from app.database import db
from app.models.url import Url
from app.models.user import User
from app.schemas import ErrorSchema, UrlSchema, UrlUpdateSchema
from app.utils import generate_short_code, serialize_model

urls_bp = Blueprint(
    "urls", __name__, url_prefix="/urls", description="URL operations"
)


@urls_bp.route("")
class UrlList(MethodView):
    @urls_bp.response(200, UrlSchema(many=True))
    def get(self):
        """List all URLs

        Supports filtering by ?user_id= and pagination via ?page=&per_page=
        """
        user_id = request.args.get("user_id", type=int)
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        cache_key = f"urls:list:{user_id}:{page}:{per_page}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        query = Url.select().order_by(Url.id)
        if user_id:
            query = query.where(Url.user_id == user_id)
        urls = query.paginate(page, per_page)

        result = [serialize_model(u) for u in urls]
        cache_set(cache_key, result, ttl=30)
        return result

    @urls_bp.arguments(UrlSchema)
    @urls_bp.response(201, UrlSchema)
    @urls_bp.alt_response(404, schema=ErrorSchema)
    def post(self, url_data):
        """Create a shortened URL"""
        user_id = url_data["user_id"]
        original_url = url_data["original_url"]
        title = url_data.get("title", "")

        user = User.get_or_none(User.id == user_id)
        if not user:
            abort(404, message="User not found")

        # Generate unique short code with retry using savepoints
        now = datetime.now()
        for _ in range(10):
            short_code = generate_short_code()
            try:
                with db.atomic():
                    url = Url.create(
                        user_id=user_id,
                        short_code=short_code,
                        original_url=original_url,
                        title=title,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                URL_CREATED.inc()  # Increment metric
                return serialize_model(url)
            except IntegrityError:
                continue

        abort(500, message="Failed to generate unique short code")


@urls_bp.route("/<int:url_id>")
class UrlDetail(MethodView):
    @urls_bp.response(200, UrlSchema)
    @urls_bp.alt_response(404, schema=ErrorSchema)
    def get(self, url_id):
        """Get a URL by ID"""
        cache_key = f"urls:{url_id}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        url = Url.get_or_none(Url.id == url_id)
        if not url:
            abort(404, message="URL not found")
        result = serialize_model(url)
        cache_set(cache_key, result, ttl=30)
        return result

    @urls_bp.arguments(UrlUpdateSchema)
    @urls_bp.response(200, UrlSchema)
    @urls_bp.alt_response(404, schema=ErrorSchema)
    def put(self, url_data, url_id):
        """Update a URL"""
        url = Url.get_or_none(Url.id == url_id)
        if not url:
            abort(404, message="URL not found")

        if "title" in url_data:
            url.title = url_data["title"]
        if "is_active" in url_data:
            url.is_active = url_data["is_active"]
        if "original_url" in url_data:
            url.original_url = url_data["original_url"]

        url.updated_at = datetime.now()
        url.save()

        cache_delete(f"urls:{url_id}")
        cache_delete_pattern("urls:list:*")
        return serialize_model(url)

    @urls_bp.response(204)
    @urls_bp.alt_response(404, schema=ErrorSchema)
    def delete(self, url_id):
        """Delete a URL"""
        url = Url.get_or_none(Url.id == url_id)
        if not url:
            abort(404, message="URL not found")

        url.delete_instance()
        cache_delete(f"urls:{url_id}")
        cache_delete_pattern("urls:list:*")
        return ""


@urls_bp.route("/<string:short_code>/redirect")
class UrlRedirect(MethodView):
    @urls_bp.alt_response(404, schema=ErrorSchema)
    def get(self, short_code):
        """Redirect to the original URL by short code"""
        url = Url.get_or_none(Url.short_code == short_code)
        if not url:
            abort(404, message="URL not found")
        if not url.is_active:
            abort(404, message="URL is not active")
        return redirect(url.original_url, code=302)
