# app.py
import os
import uuid
import logging
import datetime
from flask import Flask, render_template, request, jsonify
from flask import redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# 文件上传配置
UPLOAD_FOLDER = 'static/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
VIDEO_UPLOAD_FOLDER = 'static/videos'
VIDEO_ALLOWED_EXTENSIONS = {'mp4', 'webm', 'mkv', 'avi', 'mov', 'flv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 * 1024  # 20GB

# 数据库配置（使用 SQLite，文件名为 users.db）
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT 配置
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'change-me-to-a-strong-secret')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)

logging.basicConfig(level=logging.INFO)

db = SQLAlchemy(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins='*')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in VIDEO_ALLOWED_EXTENSIONS


# ========== 数据库模型 ==========
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='default-avatar.GIF')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    filename = db.Column(db.String(300), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref='videos', lazy=True)

    @property
    def src(self):
        return f'videos/{self.filename}'

    @property
    def mime_type(self):
        ext = self.filename.rsplit('.', 1)[-1].lower() if '.' in self.filename else 'mp4'
        return {
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'mkv': 'video/x-matroska',
            'mov': 'video/quicktime',
            'avi': 'video/x-msvideo',
            'flv': 'video/x-flv',
        }.get(ext, 'video/mp4')


class Danmaku(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(200), nullable=False)
    play_time = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(7), default='#FFFFFF')
    mode = db.Column(db.String(10), default='scroll')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref='danmakus', lazy=True)
    video = db.relationship('Video', backref='danmakus', lazy=True)


# ========== 创建数据库表 ==========
with app.app_context():
    db.create_all()


# ========== 上下文处理器 ==========
@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return dict(current_user=user, now=datetime.datetime.now())
    return dict(current_user=None, now=datetime.datetime.now())


# ========== 页面路由 ==========
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Video.query.order_by(Video.created_at.desc())\
        .paginate(page=page, per_page=12, error_out=False)
    return render_template('index.html',
        videos=pagination.items, pagination=pagination)


@app.route('/login-page')
def login_page():
    return render_template('login.html')


@app.route('/register-page')
def register_page():
    return render_template('register.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        if not name or not email or not message:
            flash('请填写所有必填字段', 'error')
            return render_template('contact.html')
        logging.info("Contact form: %s - %s: %s", name, email, message)
        flash('留言提交成功，感谢你的反馈！', 'success')
        return render_template('contact.html', success=True)
    return render_template('contact.html')


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        next_url = request.path
        return redirect(url_for('login_page', next=next_url))
    user = User.query.get(session['user_id'])
    user_videos = Video.query.filter_by(user_id=user.id)\
        .order_by(Video.created_at.desc()).all()
    total_views = sum(v.views for v in user_videos)
    return render_template('profile.html',
        user=user, user_videos=user_videos, total_views=total_views)


@app.route('/logout')
def logout():
    session.clear()
    flash('已成功退出登录', 'info')
    return redirect(url_for('login_page'))


@app.route('/video/<int:video_id>')
def video_page(video_id):
    video = Video.query.get_or_404(video_id)
    video.views += 1
    db.session.commit()
    return render_template('video.html', video=video)


@app.route('/upload-video', methods=['GET', 'POST'])
def upload_video():
    if 'user_id' not in session:
        next_url = request.path
        return redirect(url_for('login_page', next=next_url))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()

        if not title:
            flash('请输入视频标题', 'error')
            return redirect(request.url)

        if 'video_file' not in request.files:
            flash('请选择视频文件', 'error')
            return redirect(request.url)

        file = request.files['video_file']
        if file.filename == '':
            flash('请选择视频文件', 'error')
            return redirect(request.url)

        if file and allowed_video_file(file.filename):
            os.makedirs(VIDEO_UPLOAD_FOLDER, exist_ok=True)
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(VIDEO_UPLOAD_FOLDER, filename))

            video = Video(
                title=title,
                description=description,
                filename=filename,
                user_id=session['user_id']
            )
            db.session.add(video)
            db.session.commit()
            flash('视频上传成功！', 'success')
            return redirect(url_for('video_page', video_id=video.id))
        else:
            flash('不支持的视频格式（支持 mp4, webm, mkv, avi, mov, flv）', 'error')
            return redirect(request.url)

    return render_template('upload_video.html')


# ========== 认证 API ==========
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password:
        return jsonify({'error': '缺少必要字段：username, email, password'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '邮箱已被注册'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    session['username'] = user.username
    access_token = create_access_token(identity=str(user.id))
    return jsonify({'message': '注册成功', 'access_token': access_token}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '缺少用户名或密码'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': '用户名或密码错误'}), 401

    session['user_id'] = user.id
    session['username'] = user.username

    access_token = create_access_token(identity=str(user.id))
    return jsonify({'access_token': access_token}), 200


# ========== 头像相关 ==========
@app.route('/choose-avatar')
def choose_avatar():
    if 'user_id' not in session:
        next_url = request.path
        return redirect(url_for('login_page', next=next_url))

    images_dir = os.path.join(app.static_folder, 'images')
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    images = []
    try:
        for filename in os.listdir(images_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in allowed_extensions:
                images.append(filename)
    except FileNotFoundError:
        flash('图片目录不存在', 'error')
        return redirect(url_for('profile'))

    return render_template('choose_avatar.html', images=images)


@app.route('/upload-avatar', methods=['GET', 'POST'])
def upload_avatar():
    if 'user_id' not in session:
        next_url = request.path
        return redirect(url_for('login_page', next=next_url))

    user = User.query.get(session['user_id'])

    images_dir = os.path.join(app.static_folder, 'images')
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    images = []
    try:
        for filename in os.listdir(images_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in allowed_extensions:
                images.append(filename)
    except FileNotFoundError:
        flash('图片目录不存在，请联系管理员', 'error')

    if request.method == 'POST':
        if 'avatar' not in request.files:
            flash('没有选择文件', 'error')
            return redirect(request.url)
        file = request.files['avatar']
        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"user_{user.id}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.avatar = filename
            db.session.commit()
            flash('头像上传成功', 'success')
            return redirect(url_for('profile'))
        else:
            flash('不支持的文件类型', 'error')
            return redirect(request.url)

    return render_template('upload_avatar.html', images=images)


@app.route('/set-avatar', methods=['POST'])
def set_avatar():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401

    data = request.get_json()
    avatar_path = data.get('avatar')
    if not avatar_path:
        return jsonify({'success': False, 'error': '未指定图片'}), 400

    if not avatar_path.startswith('images/'):
        return jsonify({'success': False, 'error': '无效的图片路径'}), 400

    filename = avatar_path.replace('images/', '')
    safe_filename = secure_filename(filename)
    if safe_filename != filename:
        return jsonify({'success': False, 'error': '非法的文件名'}), 400

    full_path = os.path.join(app.static_folder, avatar_path)
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'error': '图片文件不存在'}), 404

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    user.avatar = avatar_path
    db.session.commit()
    return jsonify({'success': True})


# ========== API 路由 ==========
@app.route('/api/profile', methods=['GET'])
@jwt_required()
def api_profile():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'avatar': user.avatar
    })


@app.route('/routes')
def list_routes():
    import urllib.parse
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {rule.rule} [{methods}]")
        output.append(line)
    return '<br>'.join(output)


# ========== 弹幕 SocketIO 事件 ==========
@socketio.on('join')
def handle_join(data):
    video_id = data.get('video_id')
    if video_id:
        join_room(f'video_{video_id}')


@socketio.on('send_danmaku')
def handle_send_danmaku(data):
    # 从 HTTP 请求头获取 JWT token 并手动解码鉴权
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return
    token = auth_header.split(' ', 1)[1]
    try:
        decoded = decode_token(token)
        user_id = int(decoded['sub'])
    except Exception:
        return

    content = (data.get('content') or '').strip()[:200]
    play_time = data.get('play_time')
    video_id = data.get('video_id')

    if not content or play_time is None or video_id is None:
        return

    danmaku = Danmaku(
        video_id=video_id,
        user_id=user_id,
        content=content,
        play_time=play_time,
        color=data.get('color', '#FFFFFF'),
        mode=data.get('mode', 'scroll')
    )
    db.session.add(danmaku)
    db.session.commit()

    user = User.query.get(user_id)

    danmaku_data = {
        'id': danmaku.id,
        'video_id': danmaku.video_id,
        'user_id': user_id,
        'username': user.username,
        'avatar': user.avatar,
        'content': danmaku.content,
        'play_time': danmaku.play_time,
        'color': danmaku.color,
        'mode': danmaku.mode,
        'created_at': danmaku.created_at.isoformat()
    }

    emit('new_danmaku', danmaku_data, room=f'video_{video_id}')


# ========== 弹幕 REST API ==========
@app.route('/api/videos/<int:video_id>/danmakus')
def get_danmakus(video_id):
    danmakus = (Danmaku.query
                .filter_by(video_id=video_id)
                .order_by(Danmaku.play_time.asc())
                .all())
    return jsonify({
        'danmakus': [{
            'id': d.id,
            'video_id': d.video_id,
            'user_id': d.user_id,
            'username': d.user.username,
            'avatar': d.user.avatar,
            'content': d.content,
            'play_time': d.play_time,
            'color': d.color,
            'mode': d.mode,
            'created_at': d.created_at.isoformat()
        } for d in danmakus]
    })


# ========== 视频管理 API ==========
@app.route('/video/<int:video_id>/delete', methods=['POST'])
def delete_video(video_id):
    if 'user_id' not in session:
        next_url = request.path
        return redirect(url_for('login_page', next=next_url))
    video = Video.query.get_or_404(video_id)
    if video.user_id != session['user_id']:
        flash('无权删除此视频', 'error')
        return redirect(url_for('video_page', video_id=video_id))
    Danmaku.query.filter_by(video_id=video_id).delete()
    filepath = os.path.join(VIDEO_UPLOAD_FOLDER, video.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(video)
    db.session.commit()
    flash('视频已删除', 'info')
    return redirect(url_for('index'))


@app.route('/api/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    data = request.get_json()
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    if not old_pw or not new_pw:
        return jsonify({'error': '请填写原密码和新密码'}), 400
    if len(new_pw) < 6:
        return jsonify({'error': '新密码至少6位'}), 400
    user = User.query.get(session['user_id'])
    if not user.check_password(old_pw):
        return jsonify({'error': '原密码错误'}), 403
    user.set_password(new_pw)
    db.session.commit()
    return jsonify({'message': '密码修改成功'})


# ========== 错误处理 ==========
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


if __name__ == '__main__':
    socketio.run(app, debug=True)
