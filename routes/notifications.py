from flask import Blueprint, request, jsonify, session
from models import db, Notification

notif_bp = Blueprint('notifications', __name__)


@notif_bp.route('/api/notifications')
def list_notifications():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    page = request.args.get('page', 1, type=int)
    per_page = 20
    query = Notification.query.filter_by(user_id=session['user_id'])\
        .order_by(Notification.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'notifications': [{
            'id': n.id,
            'type': n.type,
            'message': n.message,
            'link': n.link,
            'is_read': n.is_read,
            'actor': {'id': n.actor.id, 'username': n.actor.username, 'avatar': n.actor.avatar} if n.actor else None,
            'created_at': n.created_at.isoformat()
        } for n in items],
        'unread_count': Notification.query.filter_by(user_id=session['user_id'], is_read=False).count(),
        'has_more': (page * per_page) < total
    })


@notif_bp.route('/api/notifications/unread-count')
def unread_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    count = Notification.query.filter_by(user_id=session['user_id'], is_read=False).count()
    return jsonify({'count': count})


@notif_bp.route('/api/notifications/<int:nid>/read', methods=['POST'])
def mark_read(nid):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    n = Notification.query.filter_by(id=nid, user_id=session['user_id']).first()
    if n:
        n.is_read = True
        db.session.commit()
    return jsonify({'success': True})


@notif_bp.route('/api/notifications/read-all', methods=['POST'])
def mark_all_read():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    Notification.query.filter_by(user_id=session['user_id'], is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})
