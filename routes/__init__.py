from routes.auth import auth_bp
from routes.main import main_bp
from routes.video import video_bp
from routes.social import social_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(social_bp)
