from flask import request, session
from flask_socketio import emit, join_room
from flask_jwt_extended import decode_token
from models import db, User, Danmaku, award_xp, XP_DANMAKU

chat_history = []
MAX_CHAT_HISTORY = 200


def register_events(socketio):
    @socketio.on('join')
    def handle_join(data):
        video_id = data.get('video_id')
        if video_id:
            join_room(f'video_{video_id}')

    @socketio.on('join_chat')
    def handle_join_chat():
        join_room('chat_room')
        emit('chat_history', chat_history[-50:])

    @socketio.on('send_message')
    def handle_chat_message(data):
        from datetime import datetime
        import uuid
        if not data.get('message', '').strip():
            return
        username = 'Guest'
        avatar = None
        if session.get('user_id'):
            user = db.session.get(User, session['user_id'])
            if user:
                username = user.username
                avatar = user.avatar
        msg = {
            'id': str(uuid.uuid4())[:8],
            'username': username,
            'avatar': avatar,
            'message': data['message'][:500],
            'time': datetime.utcnow().strftime('%H:%M:%S'),
        }
        chat_history.append(msg)
        if len(chat_history) > MAX_CHAT_HISTORY:
            del chat_history[:-MAX_CHAT_HISTORY]
        emit('new_message', msg, room='chat_room')

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
        award_xp(user, XP_DANMAKU)
        db.session.commit()

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
