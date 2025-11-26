from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask_mail import Message
from app import db, mail
from app.models.user import User
from app.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from datetime import datetime
import logging

# Create blueprint
auth_bp = Blueprint('auth', __name__)

def _get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def _generate_reset_token(user):
    s = _get_serializer()
    return s.dumps(user.email, salt=current_app.config['PASSWORD_RESET_SALT'])

def _verify_reset_token(token):
    s = _get_serializer()
    max_age = current_app.config['PASSWORD_RESET_TOKEN_MAX_AGE']
    try:
        email = s.loads(token, salt=current_app.config['PASSWORD_RESET_SALT'], max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
    return User.query.filter_by(email=email).first()

def _send_reset_email(user):
    token = _generate_reset_token(user)
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    msg = Message('Reset Your My Diary Password', recipients=[user.email])
    msg.body = render_template('emails/reset_password.txt', user=user, reset_url=reset_url)
    msg.html = render_template('emails/reset_password.html', user=user, reset_url=reset_url)
    mail.send(msg)

@auth_bp.before_request
def log_auth_request():
    """Log authentication-related requests."""
    current_app.logger.info(f"Auth Request: {request.method} {request.url}")
    if current_user.is_authenticated:
        current_app.logger.info(f"Authenticated User: {current_user.username}")

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        current_app.logger.info(f'Authenticated user {current_user.username} attempted to access register page')
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        current_app.logger.info('Processing registration request')
        
        # Create new user using model's password helper to ensure consistent hashing
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            current_app.logger.info(f'New user registered: {user.username} ({user.email})')
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error during user registration: {str(e)}', exc_info=True)
            flash('An error occurred during registration. Please try again.', 'danger')
    
    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        current_app.logger.info(f'Already authenticated user {current_user.username} accessed login page')
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        current_app.logger.info(f'Login attempt for email: {form.email.data}')
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            current_app.logger.warning(f'Failed login attempt for email: {form.email.data}')
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if user has 2FA enabled
        if user.two_factor_enabled:
            # Log in user but require 2FA verification
            login_user(user, remember=form.remember_me.data)
            current_app.logger.info(f'User {user.username} logged in, 2FA required')
            
            # Store intended page and redirect to 2FA verification
            session['2fa_next'] = request.args.get('next') or url_for('main.dashboard')
            return redirect(url_for('two_factor.verify'))
        
        login_user(user, remember=form.remember_me.data)
        current_app.logger.info(f'User {user.username} logged in successfully')
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.dashboard')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            _send_reset_email(user)
            current_app.logger.info("Password reset email sent", extra={'email': user.email})
        flash('If that email exists in our system, we have sent password reset instructions.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', title='Forgot Password', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    user = _verify_reset_token(token)
    if not user:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated. Please log in with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', title='Reset Password', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    username = current_user.username
    logout_user()
    current_app.logger.info(f'User {username} logged out')
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))