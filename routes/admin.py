from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from models import db, User, Video, Comment

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page', next=request.path))
        user = db.session.get(User, session['user_id'])
        if not user or not user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@admin_required
def dashboard():
    stats = {
        'users': User.query.count(),
        'videos': Video.query.count(),
        'comments': Comment.query.count(),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_videos = Video.query.order_by(Video.created_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html', stats=stats,
                           recent_users=recent_users, recent_videos=recent_videos)


@admin_bp.route('/users')
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users)


@admin_bp.route('/videos')
@admin_required
def videos():
    page = request.args.get('page', 1, type=int)
    videos = Video.query.order_by(Video.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/videos.html', videos=videos)


@admin_bp.route('/video/<int:video_id>/delete', methods=['POST'])
@admin_required
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    db.session.delete(video)
    db.session.commit()
    flash('Video deleted successfully', 'success')
    return redirect(url_for('admin.videos'))


@admin_bp.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'Admin status for {user.username}: {user.is_admin}', 'success')
    return redirect(url_for('admin.users'))
