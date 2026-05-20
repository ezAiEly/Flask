import os
import logging
import datetime
from flask import (Blueprint, render_template, request, session,
                   redirect, url_for, flash, jsonify, current_app)
from werkzeug.utils import secure_filename
from models import db, User, Video, Feed, VideoView, allowed_file, validate_image_mime

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/contact', methods=['GET', 'POST'])
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


@main_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_page', next=request.path))
    user = db.session.get(User, session['user_id'])
    user_videos = Video.query.filter_by(user_id=user.id)\
        .order_by(Video.created_at.desc()).all()
    total_views = sum(v.views for v in user_videos)
    return render_template('profile.html',
        user=user, user_videos=user_videos, total_views=total_views)


@main_bp.route('/choose-avatar')
def choose_avatar():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_page', next=request.path))

    images_dir = os.path.join(current_app.static_folder, 'images')
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    images = []
    try:
        for filename in os.listdir(images_dir):
            if os.path.splitext(filename)[1].lower() in allowed_extensions:
                images.append(filename)
    except FileNotFoundError:
        flash('图片目录不存在', 'error')
        return redirect(url_for('main.profile'))
    return render_template('choose_avatar.html', images=images)


@main_bp.route('/upload-avatar', methods=['GET', 'POST'])
def upload_avatar():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_page', next=request.path))

    user = db.session.get(User, session['user_id'])

    images_dir = os.path.join(current_app.static_folder, 'images')
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    images = []
    try:
        for filename in os.listdir(images_dir):
            if os.path.splitext(filename)[1].lower() in allowed_extensions:
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
            valid, mime = validate_image_mime(file)
            if not valid:
                flash('文件不是有效的图片，请上传真实图片文件', 'error')
                return redirect(request.url)

            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"user_{user.id}.{ext}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            user.avatar = filename
            db.session.commit()
            flash('头像上传成功', 'success')
            return redirect(url_for('main.profile'))
        else:
            flash('不支持的文件类型', 'error')
            return redirect(request.url)

    return render_template('upload_avatar.html', images=images)


@main_bp.route('/set-avatar', methods=['POST'])
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

    full_path = os.path.join(current_app.static_folder, avatar_path)
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'error': '图片文件不存在'}), 404

    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    user.avatar = avatar_path
    db.session.commit()
    return jsonify({'success': True})


@main_bp.route('/user/<username>')
def user_space(username):
    space_user = User.query.filter_by(username=username).first_or_404()
    current_id = session.get('user_id')

    videos = Video.query.filter_by(user_id=space_user.id)\
        .order_by(Video.created_at.desc()).all()

    feed_items = Feed.query.filter_by(user_id=space_user.id)\
        .order_by(Feed.created_at.desc()).limit(30).all()

    is_following = False
    if current_id:
        viewer = db.session.get(User, current_id)
        is_following = viewer.is_following(space_user)

    return render_template('user_space.html',
        space_user=space_user,
        is_following=is_following,
        videos=videos,
        feed_items=feed_items)


@main_bp.route('/feed')
def my_feed():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_page', next=request.path))
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    base = Feed.query.filter_by(user_id=session['user_id'])\
        .order_by(Feed.created_at.desc())
    total = base.count()
    feeds = base.offset(offset).limit(per_page + 1).all()
    has_more = len(feeds) > per_page
    feeds = feeds[:per_page]

    return render_template('my_feed.html', feeds=feeds, page=page, has_more=has_more, total=total)


@main_bp.route('/api/feed')
def api_feed():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    feeds = Feed.query.filter_by(user_id=session['user_id'])\
        .order_by(Feed.created_at.desc()).limit(30).all()
    return jsonify({'feed': [{
        'id': f.id,
        'actor': f.actor.username,
        'actor_avatar': f.actor.avatar,
        'action': f.action,
        'video_id': f.video_id,
        'video_title': f.video.title if f.video else None,
        'created_at': f.created_at.isoformat()
    } for f in feeds]})


@main_bp.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login_page', next=request.path))
    user_id = session['user_id']
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    sub = (db.session.query(VideoView.video_id,
           db.func.max(VideoView.viewed_at).label('last_viewed'))
           .filter_by(user_id=user_id)
           .group_by(VideoView.video_id)
           .subquery())

    total = db.session.query(db.func.count()).select_from(sub).scalar()
    rows = (db.session.query(sub.c.video_id, sub.c.last_viewed)
            .order_by(sub.c.last_viewed.desc())
            .offset(offset).limit(per_page + 1).all())
    has_more = len(rows) > per_page
    rows = rows[:per_page]

    video_ids = [r.video_id for r in rows]
    videos_map = {v.id: v for v in Video.query.filter(Video.id.in_(video_ids)).all()} if video_ids else {}
    history_items = [(videos_map.get(r.video_id), r.last_viewed) for r in rows if r.video_id in videos_map]

    return render_template('history.html', history_items=history_items,
                           page=page, has_more=has_more, total=total or 0)


@main_bp.route('/api/history/clear', methods=['POST'])
def clear_history():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    VideoView.query.filter_by(user_id=session['user_id']).delete()
    db.session.commit()
    return jsonify({'success': True})


@main_bp.route('/routes')
def list_routes():
    import urllib.parse
    output = []
    for rule in current_app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {rule.rule} [{methods}]")
        output.append(line)
    return '<br>'.join(output)
