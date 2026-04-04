from dotenv import load_dotenv
from flask import Flask, jsonify, render_template
from flask_smorest import Api
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge

from app.database import db, init_db
from app.logging import configure_logging
from app.routes import register_routes

# Global metrics
URL_CREATED = Counter('url_shortener_urls_created_total', 'Total URLs created')
USER_REGISTERED = Counter('url_shortener_users_registered_total', 'Total users registered')
EVENT_RECORDED = Counter('url_shortener_events_recorded_total', 'Total events recorded')
TOTAL_USERS = Gauge('url_shortener_total_users', 'Current total users')
TOTAL_URLS = Gauge('url_shortener_total_urls', 'Current total URLs')


def create_app():
    load_dotenv()

    app = Flask(__name__)

    # Configure structured logging
    configure_logging(app)

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
        db.create_tables([User, Url, Event])

    # Initialize Prometheus metrics BEFORE API registration
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    @app.route('/metrics')
    def metrics():
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
    
    metrics = PrometheusMetrics(app, path=None)  # Disable automatic route
    metrics.info('app_info', 'URL Shortener API', version='1.0.0')

    api = Api(app)
    register_routes(api)

    @app.route("/health")
    def health():
        from flask import request
        # Update gauges with current counts
        try:
            TOTAL_USERS.set(User.select().count())
            TOTAL_URLS.set(Url.select().count())
            app.logger.info("Health check requested", extra={"endpoint": "/health", "user_agent": request.headers.get('User-Agent', 'unknown')})
        except Exception as e:
            app.logger.error("Failed to update metrics: %s", str(e), extra={"error": str(e)})

        return jsonify(status="ok")

    @app.route("/")
    def index():
        return render_template("index.html")

    return app
