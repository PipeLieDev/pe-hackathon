from peewee import AutoField, CharField, DateTimeField, ForeignKeyField, TextField

from app.database import BaseModel
from app.models.url import Url
from app.models.user import User


class Event(BaseModel):
    id = AutoField()
    url_id = ForeignKeyField(Url, column_name="url_id", backref="events")
    user_id = ForeignKeyField(User, column_name="user_id", backref="events")
    event_type = CharField()
    timestamp = DateTimeField()
    details = TextField()

    class Meta:
        table_name = "events"
