import json
from datetime import datetime

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app import EVENT_RECORDED
from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from app.schemas import ErrorSchema, EventSchema
from app.utils import serialize_model

events_bp = Blueprint(
    "events", __name__, url_prefix="/events", description="Event/analytics operations"
)


@events_bp.route("")
class EventList(MethodView):
    @events_bp.response(200, EventSchema(many=True))
    def get(self):
        """List all events

        Supports filtering by ?url_id=, ?user_id=, ?event_type=
        """
        query = Event.select().order_by(Event.id)

        url_id = request.args.get("url_id", type=int)
        if url_id:
            query = query.where(Event.url_id == url_id)

        user_id = request.args.get("user_id", type=int)
        if user_id:
            query = query.where(Event.user_id == user_id)

        event_type = request.args.get("event_type")
        if event_type:
            query = query.where(Event.event_type == event_type)

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        events = query.paginate(page, per_page)

        return [serialize_model(e) for e in events]

    @events_bp.arguments(EventSchema)
    @events_bp.response(201, EventSchema)
    @events_bp.alt_response(404, schema=ErrorSchema)
    def post(self, event_data):
        """Create a new event"""
        url_id = event_data.get("url_id")
        user_id = event_data.get("user_id")
        event_type = event_data.get("event_type")
        details = event_data.get("details", {})

        if url_id and not Url.get_or_none(Url.id == url_id):
            abort(404, message="URL not found")
        if user_id and not User.get_or_none(User.id == user_id):
            abort(404, message="User not found")

        event = Event.create(
            url_id=url_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime.now(),
            details=json.dumps(details),
        )
        EVENT_RECORDED.inc()
        return serialize_model(event)
