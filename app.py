import os
import logging
import datetime
from flask import Flask, render_template, session, request, jsonify, redirect, url_for
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import config_map
from models import db, User, scan_videos
from routes import register_blueprints
from events import register_events

logging.basicConfig(level=logging.INFO)

jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins='*', async_mode='threading')
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # ── JSON 请求豁免 CSRF（必须在 csrf.init_app 之前注册） ─
    @app.before_request
    def _csrf_exempt_json():
        if request.is_json:
            view = app.view_functions.get(request.endpoint)
            if view:
                csrf.exempt(view)

    csrf.init_app(app)
    socketio.init_app(app)

    register_blueprints(app)
    register_events(socketio)

    # ── CSRF 豁免 API 路由 ─────────────────────────────
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/api/'):
            view = app.view_functions.get(rule.endpoint)
            if view:
                csrf.exempt(view)

    # ── 上下文处理器 ──────────────────────────────────
    @app.context_processor
    def inject_user():
        user_id = session.get('user_id')
        if user_id:
            user = db.session.get(User, user_id)
            return dict(current_user=user, now=datetime.datetime.now())
        return dict(current_user=None, now=datetime.datetime.now())

    # ── JWT 过期处理（返回 JSON，前端拦截 401） ──────────
    @jwt.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_payload):
        return jsonify({'error': '登录已过期，请重新登录', 'code': 'token_expired'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(_reason):
        return jsonify({'error': '无效的登录凭证', 'code': 'token_invalid'}), 401

    @jwt.unauthorized_loader
    def unauthorized_callback(_reason):
        return jsonify({'error': '请先登录', 'code': 'unauthorized'}), 401

    # ── 错误处理 ──────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        if request.is_json:
            return jsonify({'error': '请求无效'}), 400
        return render_template('error.html', code=400,
            title='请求无效',
            message='请求包含无效参数，请检查后重试。'), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': '请先登录', 'code': 'unauthorized'}), 401
        return redirect(url_for('auth.login_page', next=request.path))

    @app.errorhandler(404)
    def not_found(e):
        if request.is_json:
            return jsonify({'error': '页面未找到'}), 404
        return render_template('error.html', code=404,
            title='页面未找到',
            message='你访问的页面不存在或已被移除。'), 404

    @app.errorhandler(500)
    def server_error(e):
        if request.is_json:
            return jsonify({'error': '服务器错误'}), 500
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
