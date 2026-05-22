import os
import uuid
import datetime
from flask import (Blueprint, render_template, request, session, abort,
                   redirect, url_for, flash, jsonify, current_app)
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Video, Danmaku, VideoLike, VideoCoin, VideoFavorite, VideoView, Tag, Comment, CommentLike
from models import allowed_video_file, push_feed, get_video_duration, set_video_tags
from models import get_recommendations, _fallback_hot, get_hot_videos
from models import VideoProgress, Report, Notification
from models import push_notification, award_xp
from models import XP_COMMENT, XP_DANMAKU, XP_VIDEO_WATCHED

video_bp = Blueprint('video', __name__)


@video_bp.route('/video/<int:video_id>')
def video_page(video_id):
    video = db.session.get(Video, video_id)
    if video is None:
        abort(404)
    video.views += 1

    user_id = session.get('user_id')
    if user_id:
        existing = VideoView.query.filter_by(
            user_id=user_id, video_id=video_id
        ).first()
        if existing:
            existing.viewed_at = datetime.datetime.now(datetime.UTC)
        else:
            db.session.add(VideoView(user_id=user_id, video_id=video_id))
            viewer = db.session.get(User, user_id)
            award_xp(viewer, XP_VIDEO_WATCHED)

    db.session.commit()
    return render_template('video.html', video=video)


@video_bp.route('/upload-video', methods=['GET', 'POST'])
def upload_video():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_page', next=request.path))

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
            upload_folder = current_app.config['VIDEO_UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(upload_folder, filename))

            category = request.form.get('category', '').strip()
            if category not in CATEGORIES:
                category = ''

            video = Video(
                title=title,
                description=description,
                filename=filename,
                category=category,
                user_id=session['user_id']
            )
            db.session.add(video)
            db.session.flush()

            # Handle cover image
            cover_file = request.files.get('cover_file')
            cover_dir = os.path.join(current_app.static_folder, 'covers')
            os.makedirs(cover_dir, exist_ok=True)
            if cover_file and cover_file.filename:
                ext = cover_file.filename.rsplit('.', 1)[-1].lower()
                if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                    cover_name = f"{filename.rsplit('.', 1)[0]}.{ext}"
                    cover_file.save(os.path.join(cover_dir, cover_name))
                    video.cover_image = cover_name
            if not video.cover_image:
                # Try ffmpeg thumbnail extraction at 3s
                try:
                    import subprocess
                    video_path = os.path.join(upload_folder, filename)
                    cover_name = f"{filename.rsplit('.', 1)[0]}.jpg"
                    cover_path = os.path.join(cover_dir, cover_name)
                    subprocess.run(
                        ['ffmpeg', '-i', video_path, '-ss', '00:00:03',
                         '-vframes', '1', '-q:v', '2', cover_path, '-y'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=30
                    )
                    if os.path.exists(cover_path):
                        video.cover_image = cover_name
                except Exception:
                    pass

            tags_raw = request.form.get('tags', '').strip()
            if tags_raw:
                tag_names = [t.strip() for t in tags_raw.split(',') if t.strip()]
                set_video_tags(video, tag_names)

            db.session.commit()
            flash('视频上传成功！', 'success')
            push_feed(session['user_id'], 'upload', video.id)
            db.session.commit()
            return redirect(url_for('video.video_page', video_id=video.id))
        else:
            flash('不支持的视频格式（支持 mp4, webm, mkv, avi, mov, flv）', 'error')
            return redirect(request.url)

    return render_template('upload_video.html')


@video_bp.route('/video/<int:video_id>/delete', methods=['POST'])
def delete_video(video_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login_page', next=request.path))
    video = db.session.get(Video, video_id)
    if video is None:
        abort(404)
    if video.user_id != session['user_id']:
        flash('无权删除此视频', 'error')
        return redirect(url_for('video.video_page', video_id=video_id))
    Danmaku.query.filter_by(video_id=video_id).delete()
    filepath = os.path.join(current_app.config['VIDEO_UPLOAD_FOLDER'], video.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(video)
    db.session.commit()
    flash('视频已删除', 'info')
    return redirect(url_for('main.index'))


# ── 搜索 ─────────────────────────────────────────────────

@video_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    if not query:
        return render_template('search.html', query='', videos=[], page=1, has_more=False)

    pattern = f'%{query}%'
    base_q = (Video.query
              .filter(Video.title.like(pattern) | Video.description.like(pattern))
              .order_by(Video.views.desc()))

    total = base_q.count()
    videos = base_q.offset(offset).limit(per_page + 1).all()
    has_more = len(videos) > per_page
    videos = videos[:per_page]

    return render_template('search.html', query=query, videos=videos,
                           page=page, has_more=has_more, total=total)


@video_bp.route('/api/search')
def search_api():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 20, type=int), 50)
    offset = (page - 1) * limit

    if not query:
        return jsonify({'videos': [], 'page': 1, 'has_more': False})

    pattern = f'%{query}%'
    base_q = (Video.query
              .filter(Video.title.like(pattern) | Video.description.like(pattern))
              .order_by(Video.views.desc()))

    total = base_q.count()
    items = base_q.offset(offset).limit(limit + 1).all()
    has_more = len(items) > limit
    items = items[:limit]

    return jsonify({
        'videos': [_serialize_video(v) for v in items],
        'page': page,
        'total': total,
        'has_more': has_more,
    })


# ── 弹幕 REST API ────────────────────────────────────────

@video_bp.route('/api/videos/<int:video_id>/danmakus')
def get_danmakus(video_id):
    danmakus = (Danmaku.query
                .filter_by(video_id=video_id)
                .order_by(Danmaku.play_time.asc())
                .all())
    return jsonify({
        'danmakus': [{
            'id': d.id, 'video_id': d.video_id,
            'user_id': d.user_id, 'username': d.user.username,
            'avatar': d.user.avatar, 'content': d.content,
            'play_time': d.play_time, 'color': d.color,
            'mode': d.mode, 'created_at': d.created_at.isoformat()
        } for d in danmakus]
    })


# ── 视频互动 API ─────────────────────────────────────────

@video_bp.route('/api/video/<int:video_id>/interactions')
def get_interactions(video_id):
    video = db.session.get(Video, video_id)
    if video is None:
        abort(404)
    user_id = session.get('user_id')

    total_coins = db.session.query(
        db.func.coalesce(db.func.sum(VideoCoin.count), 0)
    ).filter_by(video_id=video_id).scalar()

    data = {
        'like_count': VideoLike.query.filter_by(video_id=video_id).count(),
        'coin_count': int(total_coins),
        'favorite_count': VideoFavorite.query.filter_by(video_id=video_id).count(),
    }

    if user_id:
        data['liked'] = VideoLike.query.filter_by(user_id=user_id, video_id=video_id).first() is not None
        coin = VideoCoin.query.filter_by(user_id=user_id, video_id=video_id).first()
        data['coined'] = coin is not None
        data['my_coins'] = coin.count if coin else 0
        data['favorited'] = VideoFavorite.query.filter_by(user_id=user_id, video_id=video_id).first() is not None

    return jsonify(data)


@video_bp.route('/api/video/<int:video_id>/like', methods=['POST'])
def toggle_like(video_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    user_id = session['user_id']
    video = db.session.get(Video, video_id)
    if video is None:
        abort(404)

    existing = VideoLike.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        count = VideoLike.query.filter_by(video_id=video_id).count()
        return jsonify({'liked': False, 'like_count': count})

    db.session.add(VideoLike(user_id=user_id, video_id=video_id))
    push_feed(user_id, 'like', video_id)
    push_notification(video.user_id, user_id, 'like',
        f'{session.get("username", "有人")} 赞了你的视频《{video.title}》',
        f'/video/{video_id}')
    author = db.session.get(User, video.user_id)
    award_xp(author, 2)  # XP_LIKE_RECEIVED
    db.session.commit()
    count = VideoLike.query.filter_by(video_id=video_id).count()
    return jsonify({'liked': True, 'like_count': count})


@video_bp.route('/api/video/<int:video_id>/coin', methods=['POST'])
def coin_video(video_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    user_id = session['user_id']
    video = db.session.get(Video, video_id)
    if video is None:
        abort(404)

    data = request.get_json() or {}
    count = data.get('count', 1)
    if count not in (1, 2):
        return jsonify({'error': '投币数只能是1或2'}), 400

    existing = VideoCoin.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing:
        existing.count = count
        db.session.commit()
    else:
        db.session.add(VideoCoin(user_id=user_id, video_id=video_id, count=count))
        push_feed(user_id, 'coin', video_id)
        push_notification(video.user_id, user_id, 'coin',
            f'{session.get("username", "有人")} 给你的视频《{video.title}》投了 {count} 枚硬币',
            f'/video/{video_id}')
        author = db.session.get(User, video.user_id)
        award_xp(author, 5)  # XP_COIN_RECEIVED
        db.session.commit()

    total_coins = db.session.query(
        db.func.coalesce(db.func.sum(VideoCoin.count), 0)
    ).filter_by(video_id=video_id).scalar()
    return jsonify({'coined': True, 'coin_count': count, 'total_coins': int(total_coins)})


@video_bp.route('/api/video/<int:video_id>/favorite', methods=['POST'])
def toggle_favorite(video_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    user_id = session['user_id']
    video = db.session.get(Video, video_id)
    if video is None:
        abort(404)

    existing = VideoFavorite.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        count = VideoFavorite.query.filter_by(video_id=video_id).count()
        return jsonify({'favorited': False, 'favorite_count': count})

    db.session.add(VideoFavorite(user_id=user_id, video_id=video_id))
    push_feed(user_id, 'favorite', video_id)
    push_notification(video.user_id, user_id, 'favorite',
        f'{session.get("username", "有人")} 收藏了你的视频《{video.title}》',
        f'/video/{video_id}')
    db.session.commit()
    count = VideoFavorite.query.filter_by(video_id=video_id).count()
    return jsonify({'favorited': True, 'favorite_count': count})


# ── 评论 API ─────────────────────────────────────────────

def _serialize_comment(c, user_id):
    return {
        'id': c.id,
        'content': c.content,
        'parent_id': c.parent_id,
        'created_at': c.created_at.isoformat(),
        'user': {
            'id': c.user.id,
            'username': c.user.username,
            'avatar': c.user.avatar,
        },
        'like_count': c.likes.count() if hasattr(c, 'likes') else
                      CommentLike.query.filter_by(comment_id=c.id).count(),
        'liked': user_id is not None and
                 CommentLike.query.filter_by(user_id=user_id, comment_id=c.id).first() is not None,
    }


@video_bp.route('/api/video/<int:video_id>/comments')
def get_comments(video_id):
    video = db.session.get(Video, video_id)
    if video is None:
        abort(404)
    user_id = session.get('user_id')
    sort = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 20, type=int), 50)
    offset = (page - 1) * limit

    base = Comment.query.filter_by(video_id=video_id, parent_id=None)

    if sort == 'hottest':
        comments = (base.outerjoin(CommentLike, CommentLike.comment_id == Comment.id)
                    .group_by(Comment.id)
                    .order_by(db.func.count(CommentLike.id).desc(), Comment.created_at.desc())
                    .offset(offset).limit(limit + 1).all())
    else:
        comments = base.order_by(Comment.created_at.desc()).offset(offset).limit(limit + 1).all()

    has_more = len(comments) > limit
    comments = comments[:limit]

    # Load replies for each comment
    result = []
    for c in comments:
        item = _serialize_comment(c, user_id)
        item['replies'] = [_serialize_comment(r, user_id)
                          for r in Comment.query.filter_by(parent_id=c.id)
                          .order_by(Comment.created_at.asc()).limit(5).all()]
        item['reply_count'] = Comment.query.filter_by(parent_id=c.id).count()
        result.append(item)

    return jsonify({'comments': result, 'page': page, 'has_more': has_more})


@video_bp.route('/api/video/<int:video_id>/comments', methods=['POST'])
def create_comment(video_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    user_id = session['user_id']
    data = request.get_json() or {}
    content = (data.get('content', '') or '').strip()
    if not content:
        return jsonify({'error': '评论内容不能为空'}), 400
    if len(content) > 1000:
        return jsonify({'error': '评论不能超过1000字'}), 400

    video = db.session.get(Video, video_id)
    if video is None:
        abort(404)

    comment = Comment(user_id=user_id, video_id=video_id, content=content)
    db.session.add(comment)
    user = db.session.get(User, user_id)
    award_xp(user, XP_COMMENT)
    push_notification(video.user_id, user_id, 'comment',
        f'{session.get("username", "有人")} 评论了你的视频《{video.title}》',
        f'/video/{video_id}')
    db.session.commit()

    return jsonify(_serialize_comment(comment, user_id)), 201


@video_bp.route('/api/comments/<int:comment_id>/reply', methods=['POST'])
def reply_comment(comment_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    parent = db.session.get(Comment, comment_id)
    if parent is None:
        abort(404)

    data = request.get_json() or {}
    content = (data.get('content', '') or '').strip()
    if not content:
        return jsonify({'error': '回复内容不能为空'}), 400
    if len(content) > 1000:
        return jsonify({'error': '回复不能超过1000字'}), 400

    user_id = session['user_id']
    reply = Comment(user_id=user_id, video_id=parent.video_id,
                    content=content, parent_id=comment_id)
    db.session.add(reply)
    award_xp(db.session.get(User, user_id), XP_COMMENT)
    if parent.user_id != user_id:
        push_notification(parent.user_id, user_id, 'reply',
            f'{session.get("username", "有人")} 回复了你的评论',
            f'/video/{parent.video_id}')
    db.session.commit()

    return jsonify(_serialize_comment(reply, user_id)), 201


@video_bp.route('/api/comments/<int:comment_id>/like', methods=['POST'])
def toggle_comment_like(comment_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    user_id = session['user_id']
    comment = db.session.get(Comment, comment_id)
    if comment is None:
        abort(404)

    existing = CommentLike.query.filter_by(user_id=user_id, comment_id=comment_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'liked': False, 'like_count': CommentLike.query.filter_by(comment_id=comment_id).count()})

    db.session.add(CommentLike(user_id=user_id, comment_id=comment_id))
    db.session.commit()
    return jsonify({'liked': True, 'like_count': CommentLike.query.filter_by(comment_id=comment_id).count()})


# ── 序列化辅助 ───────────────────────────────────────────

def _serialize_video(v):
    return {
        'id': v.id,
        'title': v.title,
        'description': v.description,
        'filename': v.filename,
        'src': v.src,
        'duration': v.duration,
        'duration_hms': v.duration_hms,
        'cover_image': v.cover_image,
        'category': v.category,
        'views': v.views,
        'tags': [t.name for t in v.tags] if v.tags else [],
        'created_at': v.created_at.isoformat(),
        'author': {
            'id': v.user.id,
            'username': v.user.username,
            'avatar': v.user.avatar,
        },
    }


# ── 分类 ─────────────────────────────────────────────────

CATEGORIES = ['动画', '音乐', '游戏', '知识', '科技', '生活', '时尚', '娱乐']
CATEGORY_ICONS = {
    '动画': 'fa-film', '音乐': 'fa-music', '游戏': 'fa-gamepad',
    '知识': 'fa-graduation-cap', '科技': 'fa-microchip',
    '生活': 'fa-heart', '时尚': 'fa-tshirt', '娱乐': 'fa-laugh',
}


@video_bp.route('/category/<category_name>')
def category_page(category_name):
    if category_name not in CATEGORIES:
        abort(404)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    base = (Video.query.filter_by(category=category_name)
            .order_by(Video.views.desc()))
    total = base.count()
    videos = base.offset(offset).limit(per_page + 1).all()
    has_more = len(videos) > per_page
    videos = videos[:per_page]

    return render_template('category.html', category_name=category_name,
                           videos=videos, page=page, has_more=has_more,
                           total=total, category_icon=CATEGORY_ICONS.get(category_name, 'fa-folder'))


@video_bp.route('/api/categories')
def api_categories():
    return jsonify({
        cat: Video.query.filter_by(category=cat).count()
        for cat in CATEGORIES
    })


# ── 推荐 API ─────────────────────────────────────────────

@video_bp.route('/api/videos/recommend')
def recommend_videos():
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 12, type=int), 50)
    offset = (page - 1) * limit

    fn = get_recommendations if user_id else _fallback_hot
    result = fn(user_id, limit * page) if user_id else _fallback_hot(limit * page)
    # 切片实现分页
    items = result[offset:offset + limit]
    has_more = len(result) > offset + limit

    return jsonify({
        'videos': [{
            **_serialize_video(v),
            'danmaku_count': danmaku_count,
        } for v, _pop, danmaku_count in items],
        'page': page,
        'has_more': has_more,
    })


# ── 热门 API ─────────────────────────────────────────────

@video_bp.route('/api/videos/hot')
def hot_videos():
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 12, type=int), 50)

    items, total = get_hot_videos(page=page, per_page=limit)

    return jsonify({
        'videos': [{
            **_serialize_video(v),
            'danmaku_count': danmaku_count,
        } for v, _pop, danmaku_count in items],
        'page': page,
        'total': total,
        'has_more': (page * limit) < total,
    })


# ── 观看进度 ─────────────────────────────────────────────

@video_bp.route('/api/video/<int:video_id>/progress', methods=['GET'])
def get_progress(video_id):
    if 'user_id' not in session:
        return jsonify({'position': 0})
    vp = VideoProgress.query.filter_by(user_id=session['user_id'], video_id=video_id).first()
    return jsonify({'position': vp.position if vp else 0})


@video_bp.route('/api/video/<int:video_id>/progress', methods=['POST'])
def save_progress(video_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    data = request.get_json() or {}
    position = max(0, float(data.get('position', 0)))
    vp = VideoProgress.query.filter_by(user_id=session['user_id'], video_id=video_id).first()
    if vp:
        vp.position = position
        vp.updated_at = datetime.datetime.now(datetime.UTC)
    else:
        vp = VideoProgress(user_id=session['user_id'], video_id=video_id, position=position)
        db.session.add(vp)
    db.session.commit()
    return jsonify({'success': True})


# ── 举报 ─────────────────────────────────────────────────

@video_bp.route('/api/video/<int:video_id>/report', methods=['POST'])
def report_video(video_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    video = Video.query.get_or_404(video_id)
    if str(video.user_id) == str(session['user_id']):
        return jsonify({'error': '不能举报自己的视频'}), 400
    data = request.get_json() or {}
    reason = data.get('reason', '').strip()
    if not reason:
        return jsonify({'error': '请选择举报原因'}), 400
    existing = Report.query.filter_by(reporter_id=session['user_id'], video_id=video_id, status='pending').first()
    if existing:
        return jsonify({'error': '你已举报过该视频，请等待处理'}), 409
    r = Report(
        reporter_id=session['user_id'],
        video_id=video_id,
        reason=reason,
        description=data.get('description', '').strip()
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({'message': '举报已提交，感谢你的反馈'})
