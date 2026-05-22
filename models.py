import os
import logging
import datetime
import subprocess
import secrets
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


def _get_or_create_system_user():
    sys_user = User.query.filter_by(is_system=True).first()
    if not sys_user:
        sys_user = User(
            username='system',
            email='system@localhost',
            is_system=True
        )
        sys_user.set_password(os.urandom(32).hex())
        db.session.add(sys_user)
        db.session.commit()
        logging.info('scan_videos: 已创建系统用户 (id=%d)', sys_user.id)
    return sys_user


def scan_videos():
    from config import Config
    folder = Config.VIDEO_UPLOAD_FOLDER
    if not os.path.exists(folder):
        return
    sys_user = _get_or_create_system_user()
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
        video = Video(title=title, filename=fname, duration=duration, user_id=sys_user.id)
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
    avatar = db.Column(db.String(200), default='images/default-avatar.GIF')
    bio = db.Column(db.String(200), default='')
    is_system = db.Column(db.Boolean, default=False)
    xp = db.Column(db.Integer, default=0)
    coins_balance = db.Column(db.Integer, default=0)
    preferences = db.Column(db.JSON, default=dict)
    mascot_image = db.Column(db.String(300), default='')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

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

    @property
    def level(self):
        xp = self.xp or 0
        if xp < 100: return 0
        if xp < 300: return 1
        if xp < 700: return 2
        if xp < 1500: return 3
        if xp < 3100: return 4
        if xp < 6300: return 5
        return 6

    @property
    def level_color(self):
        colors = {0: '#9499a0', 1: '#00a1d6', 2: '#52c41a', 3: '#f59e0b',
                  4: '#fa8c16', 5: '#f5222d', 6: '#722ed1'}
        return colors.get(self.level, '#9499a0')

    @property
    def xp_next(self):
        thresholds = {0: 100, 1: 300, 2: 700, 3: 1500, 4: 3100, 5: 6300, 6: 12700}
        return thresholds.get(self.level, 12700)

    @property
    def xp_progress(self):
        if self.level >= 6: return 100
        current = self.xp or 0
        prev = {1: 100, 2: 300, 3: 700, 4: 1500, 5: 3100, 6: 6300}.get(self.level, 0)
        needed = {0: 100, 1: 200, 2: 400, 3: 800, 4: 1600, 5: 3200, 6: 6400}.get(self.level, 100)
        return min(100, int((current - prev) / needed * 100))


# 标签关联表（定义在 Video 之前）
video_tags = db.Table('video_tags',
    db.Column('video_id', db.Integer, db.ForeignKey('video.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    filename = db.Column(db.String(300), nullable=False)
    duration = db.Column(db.Float, nullable=True)
    category = db.Column(db.String(20), default='', index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    views = db.Column(db.Integer, default=0)
    cover_image = db.Column(db.String(300), default='')
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    user = db.relationship('User', backref='videos', lazy=True)
    tags = db.relationship('Tag', secondary=video_tags, lazy='joined',
                           backref=db.backref('videos', lazy='dynamic'))

    @property
    def cover_url(self):
        if self.cover_image:
            return f'covers/{self.cover_image}'
        return None

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
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    user = db.relationship('User', backref='danmakus', lazy=True)
    video = db.relationship('Video', backref='danmakus', lazy=True)


class VideoLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='uq_video_like'),)


class VideoCoin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    count = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='uq_video_coin'),)


class VideoFavorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='uq_video_fav'),)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)


class VideoView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False, index=True)
    viewed_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    actor = db.relationship('User', foreign_keys=[actor_id])
    video = db.relationship('Video')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    user = db.relationship('User', backref='comments', lazy=True)
    video = db.relationship('Video', backref='comments', lazy=True)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)
    likes = db.relationship('CommentLike', backref='comment', lazy='dynamic', cascade='all, delete-orphan')


class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))
    __table_args__ = (db.UniqueConstraint('user_id', 'comment_id', name='uq_comment_like'),)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    category = db.Column(db.String(20), default='综合', index=True)
    cover_image = db.Column(db.String(300), default='')
    embed_url = db.Column(db.String(500), default='')
    play_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    @property
    def cover_url(self):
        if self.cover_image:
            return f'covers/{self.cover_image}'
        return None

    @property
    def is_external(self):
        return self.embed_url.startswith('http://') or self.embed_url.startswith('https://')


# ── 通知 ──────────────────────────────────────────────────

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    type = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    link = db.Column(db.String(300), default='')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    actor = db.relationship('User', foreign_keys=[actor_id])


def push_notification(user_id, actor_id, ntype, message, link=''):
    if actor_id and user_id == actor_id:
        return
    existing = Notification.query.filter_by(
        user_id=user_id, actor_id=actor_id, type=ntype,
        is_read=False
    ).filter(Notification.created_at >= datetime.datetime.now(datetime.UTC)() - datetime.timedelta(hours=1)).first()
    if existing:
        existing.created_at = datetime.datetime.now(datetime.UTC)()
        existing.message = message
        existing.link = link
        return existing
    n = Notification(user_id=user_id, actor_id=actor_id, type=ntype, message=message, link=link)
    db.session.add(n)
    return n


# ── 播放列表 ──────────────────────────────────────────────

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), default='')
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    user = db.relationship('User', backref='playlists', lazy=True)
    videos = db.relationship('PlaylistVideo', backref='playlist', lazy='dynamic',
                             cascade='all, delete-orphan',
                             order_by='PlaylistVideo.position')


class PlaylistVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    position = db.Column(db.Integer, default=0)
    added_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))
    __table_args__ = (db.UniqueConstraint('playlist_id', 'video_id', name='uq_playlist_video'),)

    video = db.relationship('Video')


# ── 观看进度 ──────────────────────────────────────────────

class VideoProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False, index=True)
    position = db.Column(db.Float, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='uq_video_progress'),)


# ── 举报 ──────────────────────────────────────────────────

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False, index=True)
    reason = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='pending', index=True)
    handled_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    reporter = db.relationship('User', foreign_keys=[reporter_id])
    video = db.relationship('Video')


# ── 密码重置 ──────────────────────────────────────────────

class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('User')

    @classmethod
    def create_for(cls, user):
        token = secrets.token_urlsafe(32)
        expires = datetime.datetime.now(datetime.UTC)() + datetime.timedelta(hours=1)
        reset = cls(user_id=user.id, token=token, expires_at=expires)
        db.session.add(reset)
        return reset


# ── Webhook 回调日志 ─────────────────────────────────────

class WebhookLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    source = db.Column(db.String(100), default='')
    payload = db.Column(db.JSON, default=dict)
    signature_valid = db.Column(db.Boolean, default=False)
    processed = db.Column(db.Boolean, default=False)
    result = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))


# ── XP 奖励 ───────────────────────────────────────────────

XP_UPLOAD = 30
XP_COMMENT = 3
XP_DANMAKU = 1
XP_LIKE_RECEIVED = 2
XP_COIN_RECEIVED = 5
XP_DAILY_LOGIN = 5
XP_VIDEO_WATCHED = 1


def award_xp(user, amount):
    if not user or user.is_system:
        return
    user.xp = (user.xp or 0) + amount


# ── Feed 推送 ────────────────────────────────────────────

def push_feed(actor_id, action, video_id):
    actor = db.session.get(User, actor_id)
    if not actor:
        return
    for follower in actor.followers_ref:
        db.session.add(Feed(
            user_id=follower.id, actor_id=actor_id,
            action=action, video_id=video_id))


# ── 标签工具 ──────────────────────────────────────────────

def get_or_create_tags(tag_names):
    """根据名称列表获取或创建 Tag，返回 Tag 对象列表。"""
    result = []
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
            db.session.flush()
        result.append(tag)
    return result


def set_video_tags(video, tag_names):
    """用名称列表设置视频标签（替换旧标签）。"""
    video.tags = get_or_create_tags(tag_names)


# ── 图片校验 ──────────────────────────────────────────────

def validate_image_mime(file_storage):
    """使用 PIL 校验上传文件是否为真实图片。返回 (is_valid, mime_type)。"""
    try:
        from PIL import Image
        img = Image.open(file_storage.stream)
        img.verify()
        file_storage.stream.seek(0)
        fmt = img.format.lower() if img.format else ''
        mime_map = {
            'jpeg': 'image/jpeg', 'jpg': 'image/jpeg',
            'png': 'image/png', 'gif': 'image/gif',
            'bmp': 'image/bmp', 'webp': 'image/webp',
        }
        if fmt in mime_map:
            return True, mime_map[fmt]
        return True, f'image/{fmt}'
    except Exception:
        file_storage.stream.seek(0)
        return False, None


# ── 推荐引擎 ────────────────────────────────────────────

def _popularity_subs():
    """返回热度计算所需的三个子查询 (like, favorite, coin)。"""
    like_sub = (
        db.session.query(
            VideoLike.video_id,
            db.func.count().label('likes')
        )
        .group_by(VideoLike.video_id)
        .subquery()
    )
    fav_sub = (
        db.session.query(
            VideoFavorite.video_id,
            db.func.count().label('favorites')
        )
        .group_by(VideoFavorite.video_id)
        .subquery()
    )
    coin_sub = (
        db.session.query(
            VideoCoin.video_id,
            db.func.sum(VideoCoin.count).label('coins')
        )
        .group_by(VideoCoin.video_id)
        .subquery()
    )
    return like_sub, fav_sub, coin_sub


def _popularity_col(like_sub, fav_sub, coin_sub):
    """返回热度计算表达式和 popularity label。"""
    return (
        Video.views * 1 +
        db.func.coalesce(like_sub.c.likes, 0) * 2 +
        db.func.coalesce(fav_sub.c.favorites, 0) * 3 +
        db.func.coalesce(coin_sub.c.coins, 0) * 5
    ).label('popularity')


def _apply_popularity_joins(query, like_sub, fav_sub, coin_sub):
    return (query
        .outerjoin(like_sub, Video.id == like_sub.c.video_id)
        .outerjoin(fav_sub, Video.id == fav_sub.c.video_id)
        .outerjoin(coin_sub, Video.id == coin_sub.c.video_id))


def get_hot_videos(page=1, per_page=12):
    like_sub, fav_sub, coin_sub = _popularity_subs()
    pop = _popularity_col(like_sub, fav_sub, coin_sub)
    danmaku_sub = (
        db.session.query(
            Danmaku.video_id,
            db.func.count().label('danmaku_count')
        )
        .group_by(Danmaku.video_id)
        .subquery()
    )

    base = _apply_popularity_joins(
        db.session.query(
            Video,
            pop,
            db.func.coalesce(danmaku_sub.c.danmaku_count, 0).label('danmaku_count')
        ),
        like_sub, fav_sub, coin_sub
    ).outerjoin(danmaku_sub, Video.id == danmaku_sub.c.video_id)

    total = db.session.query(db.func.count(Video.id)).scalar()
    items = (base
        .order_by(db.text('popularity DESC'))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all())
    return items, total


def get_recommendations(user_id, limit=20):
    # 1. 获取用户最近观看视频的标签词频（直接用 SQL 聚合）
    top_tag_rows = (
        db.session.query(
            Tag.id, Tag.name, db.func.count(video_tags.c.video_id).label('cnt')
        )
        .select_from(VideoView)
        .join(video_tags, video_tags.c.video_id == VideoView.video_id)
        .join(Tag, Tag.id == video_tags.c.tag_id)
        .filter(VideoView.user_id == user_id)
        .group_by(Tag.id)
        .order_by(db.text('cnt DESC'))
        .limit(5)
        .all()
    )

    if not top_tag_rows:
        return _fallback_hot(limit)

    top_tag_ids = [r[0] for r in top_tag_rows]

    # 2. 已观看视频 ID
    watched_ids_sub = (
        db.session.query(VideoView.video_id)
        .filter(VideoView.user_id == user_id)
        .subquery()
    )

    # 3. 构建子查询
    like_sub, fav_sub, coin_sub = _popularity_subs()
    pop = _popularity_col(like_sub, fav_sub, coin_sub)
    danmaku_sub = (
        db.session.query(
            Danmaku.video_id,
            db.func.count().label('danmaku_count')
        )
        .group_by(Danmaku.video_id)
        .subquery()
    )

    # 4. 包含匹配标签且未观看的视频，按热度降序
    return _apply_popularity_joins(
        db.session.query(
            Video,
            pop,
            db.func.coalesce(danmaku_sub.c.danmaku_count, 0).label('danmaku_count')
        ),
        like_sub, fav_sub, coin_sub
    ).outerjoin(danmaku_sub, Video.id == danmaku_sub.c.video_id) \
     .join(video_tags, video_tags.c.video_id == Video.id) \
     .filter(video_tags.c.tag_id.in_(top_tag_ids)) \
     .filter(~Video.id.in_(watched_ids_sub)) \
     .order_by(db.text('popularity DESC')) \
     .limit(limit) \
     .all()


def _fallback_hot(limit):
    like_sub, fav_sub, coin_sub = _popularity_subs()
    pop = _popularity_col(like_sub, fav_sub, coin_sub)
    danmaku_sub = (
        db.session.query(
            Danmaku.video_id,
            db.func.count().label('danmaku_count')
        )
        .group_by(Danmaku.video_id)
        .subquery()
    )

    return _apply_popularity_joins(
        db.session.query(
            Video,
            pop,
            db.func.coalesce(danmaku_sub.c.danmaku_count, 0).label('danmaku_count')
        ),
        like_sub, fav_sub, coin_sub
    ).outerjoin(danmaku_sub, Video.id == danmaku_sub.c.video_id) \
     .order_by(db.text('popularity DESC')) \
     .limit(limit) \
     .all()


# ── 游戏种子数据 ──────────────────────────────────────────

def seed_games():
    from routes.games import GAME_CATEGORIES
    existing = {g.title for g in Game.query.all()}
    seed_data = [
        ('2048', '经典数字合并益智游戏！滑动方块，相同数字合并翻倍，挑战2048方块。简约设计，无限重玩，适合所有年龄段玩家。', '益智', '/static/games/2048.html'),
        ('贪吃蛇', '经典贪吃蛇游戏回归！控制小蛇吃食物变长，挑战最高分。随着蛇身越来越长，难度越来越大，你敢来挑战吗？', '休闲', '/static/games/snake.html'),
        ('俄罗斯方块', '永远的经典！不同形状的方块从天而降，旋转、移动、消除填满的行。考验反应力和空间想象力，看你能撑多久！', '益智', '/static/games/tetris.html'),
    ]
    added = 0
    for title, desc, cat, url in seed_data:
        if title in existing:
            continue
        if cat not in GAME_CATEGORIES:
            cat = '综合'
        db.session.add(Game(title=title, description=desc, category=cat, embed_url=url))
        added += 1
    if added:
        db.session.commit()
        logging.info('seed_games: 已添加 %d 款游戏', added)
