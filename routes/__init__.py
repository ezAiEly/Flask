from routes.auth import auth_bp
from routes.main import main_bp
from routes.video import video_bp
from routes.social import social_bp
from routes.games import game_bp
from routes.notifications import notif_bp
from routes.playlists import playlist_bp
from routes.admin import admin_bp
from routes.third_party import third_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(notif_bp)
    app.register_blueprint(playlist_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(third_bp)
