from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.user import User
from app.forms import LoginForm, RegistrationForm
from datetime import datetime
import logging

# Create blueprint
auth_bp = Blueprint('auth', __name__)

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
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data, method='sha256')
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
            
        login_user(user, remember=form.remember_me.data)
        current_app.logger.info(f'User {user.username} logged in successfully')
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.dashboard')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    username = current_user.username
    logout_user()
    current_app.logger.info(f'User {username} logged out')
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))