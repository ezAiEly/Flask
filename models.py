import os
import logging
import datetime
import subprocess
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ── helpers ──────────────────────────────────────────────

def allowed_file(filename):
    from config import Config
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def allowed_video_file(filename):
    from config import Config
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.VIDEO_ALLOWED_EXTENSIONS


def get_video_duration(filepath):
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries',
            'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
            filepath
        ], capture_output=True, text=True, timeout=15)
        return float(result.stdout.strip()) if result.stdout.strip() else None
    except Exception:
        return None


def scan_videos():
    from config import Config
    folder = Config.VIDEO_UPLOAD_FOLDER
    if not os.path.exists(folder):
        return
    default_user = User.query.first()
    if not default_user:
        logging.info('scan_videos: 数据库中没有用户，跳过扫描')
        return
    registered = {v.filename for v in Video.query.all()}
    count = 0
    for fname in os.listdir(folder):
        if not allowed_video_file(fname):
            continue
        if fname in registered:
            continue
        filepath = os.path.join(folder, fname)
        duration = get_video_duration(filepath)
        title = os.path.splitext(fname)[0]
        video = Video(title=title, filename=fname, duration=duration, user_id=default_user.id)
        db.session.add(video)
        count += 1
        logging.info(f'scan_videos: 注册视频 {fname} (duration={duration})')
    if count:
        db.session.commit()
        logging.info(f'scan_videos: 成功注册 {count} 个新视频')


# ── 关注关系表 ───────────────────────────────────────────

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


# ── 模型 ─────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), default='default-avatar.GIF')
    bio = db.Column(db.String(200), default='')

    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers_ref', lazy='dynamic'), lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    filename = db.Column(db.String(300), nullable=False)
    duration = db.Column(db.Float, nullable=True)
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
            'mp4': 'video/mp4', 'webm': 'video/webm', 'mkv': 'video/x-matroska',
            'mov': 'video/quicktime', 'avi': 'video/x-msvideo', 'flv': 'video/x-flv',
        }.get(ext, 'video/mp4')

    @property
    def duration_hms(self):
        if not self.duration:
            return None
        m, s = divmod(int(self.duration), 60)
        h, m = divmod(m, 60)
        return f'{h}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'

    @property
    def file_size_mb(self):
        from config import Config
        path = os.path.join(Config.VIDEO_UPLOAD_FOLDER, self.filename)
        if os.path.exists(path):
            return round(os.path.getsize(path) / (1024 * 1024), 1)
        return None


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


class VideoLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='uq_video_like'),)


class VideoCoin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    count = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='uq_video_coin'),)


class VideoFavorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='uq_video_fav'),)


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    actor = db.relationship('User', foreign_keys=[actor_id])
    video = db.relationship('Video')


# ── Feed 推送 ────────────────────────────────────────────

def push_feed(actor_id, action, video_id):
    actor = User.query.get(actor_id)
    if not actor:
        return
    for follower in actor.followers_ref:
        db.session.add(Feed(
            user_id=follower.id, actor_id=actor_id,
            action=action, video_id=video_id))
