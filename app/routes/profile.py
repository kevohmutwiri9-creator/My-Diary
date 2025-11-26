"""Profile management routes."""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
from app import db
from app.models import User
from app.services.upload_service import upload_profile_picture, delete_profile_picture
import os

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile')
@login_required
def view_profile():
    """View user profile."""
    return render_template('profile/view.html', user=current_user)


@profile_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile."""
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip()
        bio = request.form.get('bio', '').strip()
        
        # Validate username
        if not username:
            flash('Username is required.', 'danger')
            return redirect(url_for('profile.edit_profile'))
        
        # Check if username is already taken by another user
        existing_user = User.query.filter(
            User.username == username,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            flash('Username is already taken.', 'danger')
            return redirect(url_for('profile.edit_profile'))
        
        # Update user profile
        current_user.username = username
        current_user.bio = bio
        db.session.commit()
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.view_profile'))
    
    return render_template('profile/edit.html', user=current_user)


@profile_bp.route('/profile/upload-picture', methods=['POST'])
@login_required
def upload_picture():
    """Upload profile picture."""
    if 'profile_picture' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    # Upload new profile picture
    filename, error = upload_profile_picture(file, current_user.id)
    
    if error:
        return jsonify({'success': False, 'message': error}), 400
    
    # Delete old profile picture if it exists
    if current_user.profile_picture:
        delete_profile_picture(current_user.profile_picture)
    
    # Update user profile
    current_user.update_profile_picture(filename)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Profile picture updated successfully!',
        'url': current_user.get_profile_picture_url()
    })


@profile_bp.route('/profile/remove-picture', methods=['POST'])
@login_required
def remove_picture():
    """Remove profile picture."""
    if current_user.profile_picture:
        delete_profile_picture(current_user.profile_picture)
        current_user.profile_picture = None
        db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Profile picture removed successfully!',
        'url': current_user.get_profile_picture_url()
    })


@profile_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Validate input
    if not all([current_password, new_password, confirm_password]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('profile.edit_profile'))
    
    # Check current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('profile.edit_profile'))
    
    # Check new passwords match
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('profile.edit_profile'))
    
    # Validate new password strength
    try:
        current_user.validate_password_strength(new_password)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('profile.edit_profile'))
    
    # Update password
    current_user.set_password(new_password)
    current_user.last_password_change = datetime.utcnow()
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile.edit_profile'))


@profile_bp.route('/profile/<username>')
@login_required
def public_profile(username):
    """View public profile of another user."""
    user = User.query.filter_by(username=username).first_or_404()
    
    # Check if user allows public profile viewing
    if not user.allow_public_search and user.id != current_user.id:
        flash('This profile is private.', 'info')
        return redirect(url_for('main.dashboard'))
    
    # Get user's public entries
    from app.models import Entry
    public_entries = Entry.query.filter_by(
        user_id=user.id,
        is_private=False
    ).order_by(Entry.created_at.desc()).limit(10).all()
    
    return render_template('profile/public.html', user=user, entries=public_entries)
