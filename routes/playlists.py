from flask import Blueprint, request, jsonify, session
from models import db, Playlist, PlaylistVideo, Video

playlist_bp = Blueprint('playlists', __name__)


# ── Playlist CRUD ───────────────────────────────────────

@playlist_bp.route('/api/playlists')
def list_playlists():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    uid = request.args.get('user_id', session['user_id'], type=int)
    query = Playlist.query.filter_by(user_id=uid)
    if uid != session['user_id']:
        query = query.filter_by(is_public=True)
    playlists = query.order_by(Playlist.created_at.desc()).all()
    return jsonify({'playlists': [{
        'id': p.id, 'name': p.name, 'description': p.description,
        'is_public': p.is_public,
        'video_count': p.videos.count(),
        'user': {'id': p.user.id, 'username': p.user.username},
        'created_at': p.created_at.isoformat()
    } for p in playlists]})


@playlist_bp.route('/api/playlists', methods=['POST'])
def create_playlist():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': '请输入播放列表名称'}), 400
    p = Playlist(
        user_id=session['user_id'],
        name=data['name'].strip(),
        description=data.get('description', '').strip(),
        is_public=data.get('is_public', True)
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'id': p.id, 'name': p.name, 'message': '创建成功'}), 201


@playlist_bp.route('/api/playlists/<int:pid>', methods=['PUT'])
def update_playlist(pid):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    p = Playlist.query.filter_by(id=pid, user_id=session['user_id']).first()
    if not p:
        return jsonify({'error': '播放列表不存在'}), 404
    data = request.get_json() or {}
    if data.get('name'):
        p.name = data['name'].strip()
    if 'description' in data:
        p.description = data['description'].strip()
    if 'is_public' in data:
        p.is_public = data['is_public']
    db.session.commit()
    return jsonify({'message': '更新成功'})


@playlist_bp.route('/api/playlists/<int:pid>', methods=['DELETE'])
def delete_playlist(pid):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    p = Playlist.query.filter_by(id=pid, user_id=session['user_id']).first()
    if not p:
        return jsonify({'error': '播放列表不存在'}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({'message': '已删除'})


# ── Video management within playlist ────────────────────

@playlist_bp.route('/api/playlists/<int:pid>/videos')
def list_playlist_videos(pid):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    p = Playlist.query.get_or_404(pid)
    if not p.is_public and p.user_id != session['user_id']:
        return jsonify({'error': '无权访问'}), 403
    items = p.videos.order_by(PlaylistVideo.position).all()
    return jsonify({'videos': [{
        'id': pv.video.id, 'title': pv.video.title,
        'duration_hms': pv.video.duration_hms,
        'cover_url': pv.video.cover_url,
        'author': pv.video.user.username,
        'views': pv.video.views,
        'position': pv.position,
        'added_at': pv.added_at.isoformat()
    } for pv in items], 'playlist': {'id': p.id, 'name': p.name}})


@playlist_bp.route('/api/playlists/<int:pid>/videos', methods=['POST'])
def add_video_to_playlist(pid):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    p = Playlist.query.filter_by(id=pid, user_id=session['user_id']).first()
    if not p:
        return jsonify({'error': '播放列表不存在'}), 404
    data = request.get_json()
    vid = data.get('video_id')
    if not vid:
        return jsonify({'error': '缺少 video_id'}), 400
    video = Video.query.get(vid)
    if not video:
        return jsonify({'error': '视频不存在'}), 404
    if PlaylistVideo.query.filter_by(playlist_id=pid, video_id=vid).first():
        return jsonify({'error': '视频已在列表中'}), 409
    max_pos = db.session.query(db.func.max(PlaylistVideo.position))\
        .filter_by(playlist_id=pid).scalar() or 0
    pv = PlaylistVideo(playlist_id=pid, video_id=vid, position=max_pos + 1)
    db.session.add(pv)
    db.session.commit()
    return jsonify({'message': '已添加到播放列表'}), 201


@playlist_bp.route('/api/playlists/<int:pid>/videos/<int:vid>', methods=['DELETE'])
def remove_video_from_playlist(pid, vid):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    p = Playlist.query.filter_by(id=pid, user_id=session['user_id']).first()
    if not p:
        return jsonify({'error': '播放列表不存在'}), 404
    pv = PlaylistVideo.query.filter_by(playlist_id=pid, video_id=vid).first()
    if not pv:
        return jsonify({'error': '视频不在列表中'}), 404
    db.session.delete(pv)
    db.session.commit()
    return jsonify({'message': '已移除'})
