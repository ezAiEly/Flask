import os
import uuid
from flask import (Blueprint, render_template, request, session,
                   redirect, url_for, flash, jsonify, current_app)
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Video, Danmaku, VideoLike, VideoCoin, VideoFavorite
from models import allowed_video_file, push_feed, get_video_duration

video_bp = Blueprint('video', __name__)


@video_bp.route('/video/<int:video_id>')
def video_page(video_id):
    video = Video.query.get_or_404(video_id)
    video.views += 1
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

            video = Video(
                title=title,
                description=description,
                filename=filename,
                user_id=session['user_id']
            )
            db.session.add(video)
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
    video = Video.query.get_or_404(video_id)
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
    video = Video.query.get_or_404(video_id)
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
    Video.query.get_or_404(video_id)

    existing = VideoLike.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        count = VideoLike.query.filter_by(video_id=video_id).count()
        return jsonify({'liked': False, 'like_count': count})

    db.session.add(VideoLike(user_id=user_id, video_id=video_id))
    db.session.commit()
    push_feed(user_id, 'like', video_id)
    db.session.commit()
    count = VideoLike.query.filter_by(video_id=video_id).count()
    return jsonify({'liked': True, 'like_count': count})


@video_bp.route('/api/video/<int:video_id>/coin', methods=['POST'])
def coin_video(video_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    user_id = session['user_id']
    Video.query.get_or_404(video_id)

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
        db.session.commit()
        push_feed(user_id, 'coin', video_id)
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
    Video.query.get_or_404(video_id)

    existing = VideoFavorite.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        count = VideoFavorite.query.filter_by(video_id=video_id).count()
        return jsonify({'favorited': False, 'favorite_count': count})

    db.session.add(VideoFavorite(user_id=user_id, video_id=video_id))
    db.session.commit()
    push_feed(user_id, 'favorite', video_id)
    db.session.commit()
    count = VideoFavorite.query.filter_by(video_id=video_id).count()
    return jsonify({'favorited': True, 'favorite_count': count})
