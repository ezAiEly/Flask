from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
from flask_jwt_extended import create_access_token
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login-page')
def login_page():
    return render_template('login.html')


@auth_bp.route('/register-page')
def register_page():
    return render_template('register.html')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
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
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '缺少用户名或密码'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': '用户名或密码错误'}), 401

    session['user_id'] = user.id
    session['username'] = user.username

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
    user = User.query.get(session['user_id'])
    if not user.check_password(old_pw):
        return jsonify({'error': '原密码错误'}), 403
    user.set_password(new_pw)
    db.session.commit()
    return jsonify({'message': '密码修改成功'})
