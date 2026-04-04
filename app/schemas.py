from marshmallow import Schema, fields


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    email = fields.Str(required=True)
    created_at = fields.Str(dump_only=True)


class UserUpdateSchema(Schema):
    username = fields.Str()
    email = fields.Str()


class UserBulkResponseSchema(Schema):
    imported = fields.Int()


class UrlSchema(Schema):
    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    short_code = fields.Str(dump_only=True)
    original_url = fields.Str(required=True)
    title = fields.Str(load_default="")
    is_active = fields.Bool(dump_only=True)
    created_at = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)


class UrlUpdateSchema(Schema):
    title = fields.Str()
    is_active = fields.Bool()
    original_url = fields.Str()


class EventDetailSchema(Schema):
    short_code = fields.Str()
    original_url = fields.Str()
    reason = fields.Str()


class EventSchema(Schema):
    id = fields.Int(dump_only=True)
    url_id = fields.Int()
    user_id = fields.Int()
    event_type = fields.Str()
    timestamp = fields.Str()
    details = fields.Dict()


class HealthSchema(Schema):
    status = fields.Str()


class ErrorSchema(Schema):
    error = fields.Str()
