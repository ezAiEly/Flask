import os
import logging
import datetime
from flask import Flask, render_template, session
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from config import config_map
from models import db, User, scan_videos
from routes import register_blueprints
from events import register_events

logging.basicConfig(level=logging.INFO)

jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins='*')


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)

    register_blueprints(app)
    register_events(socketio)

    # ── 上下文处理器 ──────────────────────────────────
    @app.context_processor
    def inject_user():
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            return dict(current_user=user, now=datetime.datetime.now())
        return dict(current_user=None, now=datetime.datetime.now())

    # ── 错误处理 ──────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('error.html', code=400,
            title='请求无效',
            message='请求包含无效参数，请检查后重试。'), 400

    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', code=404,
            title='页面未找到',
            message='你访问的页面不存在或已被移除。'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', code=500,
            title='服务器错误',
            message='服务器遇到了意外错误，请稍后重试。'), 500

    # ── 数据库初始化 ──────────────────────────────────
    with app.app_context():
        db.create_all()
        scan_videos()

    return app


if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True)
