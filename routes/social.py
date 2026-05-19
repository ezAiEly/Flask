from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User

social_bp = Blueprint('social', __name__)


@social_bp.route('/api/user/<int:target_id>/follow', methods=['POST'])
def toggle_follow(target_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    user_id = session['user_id']
    if user_id == target_id:
        return jsonify({'error': '不能关注自己'}), 400

    user = User.query.get(user_id)
    target = User.query.get_or_404(target_id)

    if user.is_following(target):
        user.unfollow(target)
        db.session.commit()
        return jsonify({'following': False, 'follower_count': target.followers_ref.count()})
    else:
        user.follow(target)
        db.session.commit()
        return jsonify({'following': True, 'follower_count': target.followers_ref.count()})


@social_bp.route('/api/profile', methods=['GET'])
@jwt_required()
def api_profile():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'avatar': user.avatar
    })
