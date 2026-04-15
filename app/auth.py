from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User
from app.translations import t as translate

auth_bp = Blueprint('auth', __name__)


def admin_required(f):
    """Decorator that requires the current user to be an admin."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash(translate('flash.access_denied'), 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/set-language/<lang>')
def set_language(lang):
    if lang in ('en', 'de'):
        session['lang'] = lang
    return redirect(request.referrer or url_for('dashboard'))


@auth_bp.before_app_request
def check_password_change():
    """Redirect users who must change their password."""
    if current_user.is_authenticated and current_user.must_change_password:
        allowed_endpoints = ('auth.change_password', 'auth.logout', 'static')
        if request.endpoint and request.endpoint not in allowed_endpoints:
            return redirect(url_for('auth.change_password'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = db.session.query(User).filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            if user.must_change_password:
                return redirect(url_for('auth.change_password'))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))

        flash(translate('flash.invalid_credentials'), 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash(translate('flash.logged_out'), 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(current_password):
            flash(translate('flash.current_pw_wrong'), 'danger')
        elif len(new_password) < 8:
            flash(translate('flash.pw_too_short'), 'danger')
        elif new_password != confirm_password:
            flash(translate('flash.pw_mismatch'), 'danger')
        else:
            current_user.set_password(new_password)
            current_user.must_change_password = False
            db.session.commit()
            flash(translate('flash.pw_changed'), 'success')
            return redirect(url_for('dashboard'))

    return render_template('change_password.html')


@auth_bp.route('/users')
@admin_required
def users():
    all_users = db.session.query(User).order_by(User.username).all()
    return render_template('users.html', users=all_users)


@auth_bp.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    is_admin = request.form.get('is_admin') == 'on'

    if not username or not password:
        flash(translate('flash.user_pw_required'), 'danger')
        return redirect(url_for('auth.users'))

    existing = db.session.query(User).filter_by(username=username).first()
    if existing:
        flash(translate('flash.user_exists', name=username), 'danger')
        return redirect(url_for('auth.users'))

    user = User(
        username=username,
        is_admin=is_admin,
        must_change_password=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash(translate('flash.user_created', name=username), 'success')
    return redirect(url_for('auth.users'))


@auth_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash(translate('flash.user_not_found'), 'danger')
        return redirect(url_for('auth.users'))

    if user.id == current_user.id:
        flash(translate('flash.cant_delete_self'), 'danger')
        return redirect(url_for('auth.users'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(translate('flash.user_deleted', name=username), 'success')
    return redirect(url_for('auth.users'))


@auth_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash(translate('flash.user_not_found'), 'danger')
        return redirect(url_for('auth.users'))

    user.set_password('password')
    user.must_change_password = True
    db.session.commit()

    flash(translate('flash.pw_reset', name=user.username), 'success')
    return redirect(url_for('auth.users'))
