def register_routes(api):
    from app.routes.users import users_bp
    from app.routes.urls import urls_bp
    from app.routes.events import events_bp

    api.register_blueprint(users_bp)
    api.register_blueprint(urls_bp)
    api.register_blueprint(events_bp)
