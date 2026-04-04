from peewee import (
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    TextField,
)

from app.database import BaseModel
from app.models.user import User


class Url(BaseModel):
    id = AutoField()
    user_id = ForeignKeyField(User, column_name="user_id", backref="urls")
    short_code = CharField(max_length=10, unique=True, index=True)
    original_url = TextField()
    title = CharField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        table_name = "urls"
