from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask_mail import Message
from app import db, mail
from app.models.user import User
from app.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from app.utils.error_handler import handle_errors, AuthenticationError, ValidationError
from app.utils.security_enhancer import (
    PasswordSecurity, InputValidator, RateLimiter, 
    SecurityMonitor, require_csrf_token, rate_limit, validate_input
)
from datetime import datetime
import logging

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize security monitor
security_monitor = SecurityMonitor()

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
@rate_limit(limit=3, window=600)  # 3 registrations per 10 minutes
@validate_input({
    'username': {'required': True, 'type': 'username', 'min_length': 3, 'max_length': 30},
    'email': {'required': True, 'type': 'email', 'max_length': 120},
    'password': {'required': True, 'min_length': 8, 'max_length': 128}
})
@handle_errors("Registration failed. Please try again.", log_error=True)
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        current_app.logger.info(f'Authenticated user {current_user.username} attempted to access register page')
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        current_app.logger.info('Processing registration request')
        
        # Enhanced password strength validation
        password_validation = PasswordSecurity.validate_password_strength(
            form.password.data,
            {'username': form.username.data, 'email': form.email.data}
        )
        
        if not password_validation['is_strong']:
            for error in password_validation['errors']:
                flash(error, 'danger')
            return render_template('auth/register.html', title='Register', form=form)
        
        # Check for mass registration attempts
        if security_monitor.detect_mass_registration(request.remote_addr):
            current_app.security_logger.warning(f"Mass registration attempt from {request.remote_addr}")
            flash('Too many registration attempts. Please try again later.', 'danger')
            return render_template('auth/register.html', title='Register', form=form)
        
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
            
            # Log successful registration for security monitoring
            if hasattr(current_app, 'security_logger'):
                current_app.security_logger.info(f"User registration: {user.email} from {request.remote_addr}")
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error during user registration: {str(e)}', exc_info=True)
            flash('An error occurred during registration. Please try again.', 'danger')
    
    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(limit=10, window=900)  # 10 login attempts per 15 minutes
@validate_input({
    'email': {'required': True, 'type': 'email', 'max_length': 120},
    'password': {'required': True, 'min_length': 1, 'max_length': 128}
})
@handle_errors("Login failed. Please try again.", log_error=True)
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        current_app.logger.info(f'Already authenticated user {current_user.username} accessed login page')
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        current_app.logger.info(f'Login attempt for email: {form.email.data}')
        
        # Check for brute force attempts
        if security_monitor.detect_brute_force(request.remote_addr, form.email.data):
            current_app.security_logger.warning(f"Brute force attempt detected for {form.email.data} from {request.remote_addr}")
            flash('Too many failed login attempts. Please try again later.', 'danger')
            return render_template('auth/login.html', title='Sign In', form=form)
        
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            current_app.logger.warning(f'Failed login attempt for email: {form.email.data}')
            
            # Log failed login attempt for security monitoring
            if hasattr(current_app, 'security_logger'):
                current_app.security_logger.warning(f"Failed login: {form.email.data} from {request.remote_addr}")
            
            flash('Invalid email or password', 'danger')
            return render_template('auth/login.html', title='Sign In', form=form)
        
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