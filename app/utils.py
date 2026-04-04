import json
import random
import string
from datetime import datetime

from flask import jsonify
from playhouse.shortcuts import model_to_dict


def serialize_model(instance, **kwargs):
    """Convert a Peewee model instance to a JSON-safe dict."""
    data = model_to_dict(instance, recurse=False, backrefs=False, **kwargs)
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.strftime("%Y-%m-%dT%H:%M:%S")
    # Parse JSON text fields
    if "details" in data and isinstance(data["details"], str):
        try:
            data["details"] = json.loads(data["details"])
        except (json.JSONDecodeError, TypeError):
            pass
    return data


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))
