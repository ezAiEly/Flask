from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
from flask_jwt_extended import create_access_token
import datetime
from models import db, User, PasswordResetToken, award_xp, XP_DAILY_LOGIN
from extensions import limiter
from utils.captcha_utils import generate_captcha

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/captcha')
def get_captcha():
    img_base64, answer = generate_captcha()
    session['captcha_answer'] = answer
    return jsonify({'captcha': f'data:image/png;base64,{img_base64}'})


@auth_bp.route('/login-page')
def login_page():
    return render_template('login.html')


@auth_bp.route('/register-page')
def register_page():
    return render_template('register.html')


@auth_bp.route('/register', methods=['POST'])
@limiter.limit('5 per minute')
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    from flask import current_app
    if not current_app.config.get('TESTING'):
        captcha_input = (data.get('captcha') or '').lower()
        expected = session.pop('captcha_answer', None)
        if not expected or captcha_input != expected:
            return jsonify({'error': '验证码错误'}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password:
        return jsonify({'error': '缺少必要字段：username, email, password'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '邮箱已被注册'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    session['username'] = user.username
    access_token = create_access_token(identity=str(user.id))
    return jsonify({'message': '注册成功', 'access_token': access_token}), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit('10 per minute')
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '缺少用户名或密码'}), 400

    from flask import current_app
    if not current_app.config.get('TESTING'):
        captcha_input = (data.get('captcha') or '').lower()
        expected = session.pop('captcha_answer', None)
        if not expected or captcha_input != expected:
            return jsonify({'error': '验证码错误'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': '用户名或密码错误'}), 401

    session['user_id'] = user.id
    session['username'] = user.username

    # Daily login XP (once per day)
    last_login = user.preferences.get('last_login_date') if user.preferences else None
    today = datetime.date.today().isoformat()
    if last_login != today:
        award_xp(user, XP_DAILY_LOGIN)
        if not user.preferences:
            user.preferences = {}
        user.preferences['last_login_date'] = today

    access_token = create_access_token(identity=str(user.id))
    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('已成功退出登录', 'info')
    return redirect(url_for('auth.login_page'))


@auth_bp.route('/api/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    data = request.get_json()
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    if not old_pw or not new_pw:
        return jsonify({'error': '请填写原密码和新密码'}), 400
    if len(new_pw) < 6:
        return jsonify({'error': '新密码至少6位'}), 400
    user = db.session.get(User, session['user_id'])
    if not user.check_password(old_pw):
        return jsonify({'error': '原密码错误'}), 403
    user.set_password(new_pw)
    db.session.commit()
    return jsonify({'message': '密码修改成功'})


# ── 密码重置 ─────────────────────────────────────────────

@auth_bp.route('/api/forgot-password', methods=['POST'])
@limiter.limit('3 per hour')
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': '请输入邮箱'}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': '该邮箱未注册'}), 404
    reset = PasswordResetToken.create_for(user)
    db.session.commit()
    return jsonify({
        'message': '重置链接已生成',
        'reset_token': reset.token,
        'debug_url': f'/auth/reset-password?token={reset.token}'
    })


@auth_bp.route('/api/reset-password', methods=['POST'])
@limiter.limit('5 per hour')
def reset_password():
    data = request.get_json() or {}
    token_str = data.get('token', '').strip()
    new_pw = data.get('new_password', '')
    if not token_str or not new_pw:
        return jsonify({'error': '缺少 token 或新密码'}), 400
    if len(new_pw) < 6:
        return jsonify({'error': '新密码至少6位'}), 400
    reset = PasswordResetToken.query.filter_by(token=token_str, used=False).first()
    if not reset or reset.expires_at < datetime.datetime.utcnow():
        return jsonify({'error': '链接已过期或无效'}), 400
    user = db.session.get(User, reset.user_id)
    user.set_password(new_pw)
    reset.used = True
    db.session.commit()
    return jsonify({'message': '密码重置成功，请重新登录'})
