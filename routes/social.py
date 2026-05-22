from flask import Blueprint, request, jsonify, session, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, push_notification

social_bp = Blueprint('social', __name__)


@social_bp.route('/api/user/<int:target_id>/follow', methods=['POST'])
def toggle_follow(target_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    user_id = session['user_id']
    if user_id == target_id:
        return jsonify({'error': '不能关注自己'}), 400

    user = db.session.get(User, user_id)
    target = db.session.get(User, target_id)
    if target is None:
        abort(404)

    if user.is_following(target):
        user.unfollow(target)
        db.session.commit()
        return jsonify({'following': False, 'follower_count': target.followers_ref.count()})
    else:
        user.follow(target)
        push_notification(target_id, user_id, 'follow',
            f'{user.username} 关注了你', f'/user/{user.username}')
        db.session.commit()
        return jsonify({'following': True, 'follower_count': target.followers_ref.count()})


@social_bp.route('/api/profile', methods=['GET'])
@jwt_required()
def api_profile():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'avatar': user.avatar
    })
