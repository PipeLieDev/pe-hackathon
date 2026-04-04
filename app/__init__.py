from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template
from flask_smorest import Api

from app.database import db, init_db
from app.routes import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)

    # flask-smorest / OpenAPI config
    app.config["API_TITLE"] = "URL Shortener API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/apidocs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    init_db(app)

    from app.models import Event, Url, User

    with app.app_context():
        db.create_tables([User, Url, Event], safe=True)

    @app.after_request
    def add_cache_header(response):
        if hasattr(g, "x_cache"):
            response.headers["X-Cache"] = g.x_cache
        return response

    api = Api(app)
    register_routes(api)

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.route("/")
    def index():
        return render_template("index.html")

    return app
