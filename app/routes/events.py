from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint

from app.models.event import Event
from app.schemas import EventSchema
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
