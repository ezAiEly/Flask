from flask import request
from flask_socketio import emit, join_room
from flask_jwt_extended import decode_token
from models import db, User, Danmaku


def register_events(socketio):
    @socketio.on('join')
    def handle_join(data):
        video_id = data.get('video_id')
        if video_id:
            join_room(f'video_{video_id}')

    @socketio.on('send_danmaku')
    def handle_send_danmaku(data):
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

        user = db.session.get(User, user_id)

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
