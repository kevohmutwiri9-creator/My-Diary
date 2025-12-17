"""Main application routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app import db
from app.models.entry import Entry
from app.models.user import User

# Try to import Goal model with error handling
try:
    from app.models.goal import Goal
    _GOAL_AVAILABLE = True
except ImportError:
    Goal = None
    _GOAL_AVAILABLE = False

from app.services.adsense import adsense_service
from app.forms import AdSettingsForm, EntryForm # Import EntryForm
from datetime import datetime, timedelta
import logging

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # Fetch a few recent public entries for the homepage
    public_entries = Entry.query.filter_by(is_private=False).order_by(Entry.created_at.desc()).limit(5).all()
    
    return render_template('index.html', public_entries=public_entries)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page."""
    # Get user's recent entries
    recent_entries = current_user.entries.order_by(Entry.created_at.desc()).limit(5).all()
    
    # Get statistics
    total_entries = current_user.entries.count()
    total_words = sum(entry.word_count for entry in current_user.entries.all() if entry.word_count)
    
    # Get active goals (with error handling)
    active_goals = []
    if _GOAL_AVAILABLE and Goal:
        active_goals = Goal.query.filter_by(
            user_id=current_user.id, 
            status='active'
        ).all()
    
    # Get mood distribution
    mood_data = {}
    for entry in current_user.entries.all():
        if entry.mood:
            mood_data[entry.mood] = mood_data.get(entry.mood, 0) + 1
    
    # Streak calculation
    streak_count = current_user.streak_count or 0
    
    # AdSense configuration
    ad_config = adsense_service.get_ad_config()
    
    return render_template('dashboard.html',
                         recent_entries=recent_entries,
                         total_entries=total_entries,
                         total_words=total_words,
                         active_goals=active_goals,
                         mood_data=mood_data,
                         streak_count=streak_count,
                         ad_config=ad_config)

@main_bp.route('/entries')
@login_required
def entries():
    """List all entries."""
    page = request.args.get('page', 1, type=int)
    entries = current_user.entries.order_by(Entry.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('entries.html', entries=entries)

@main_bp.route('/entry/<int:id>')
@login_required
def view_entry(id):
    """View a specific entry."""
    entry = Entry.query.get_or_404(id)
    
    # Check if user owns this entry
    if entry.user_id != current_user.id:
        flash('You can only view your own entries.', 'warning')
        return redirect(url_for('main.entries'))
    
    return render_template('view_entry.html', entry=entry)

@main_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_entry():
    """Create a new entry."""
    form = EntryForm()
    if form.validate_on_submit():
        entry = Entry(title=form.title.data, 
                      content=form.content.data, 
                      is_public=form.is_public.data, # Save is_public status
                      user_id=current_user.id)
        db.session.add(entry)
        db.session.commit()
        flash('Your entry has been created!', 'success')
        return redirect(url_for('main.view_entry', id=entry.id))
    return render_template('new_entry.html', form=form)

@main_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    """Edit an entry."""
    entry = Entry.query.get_or_404(id)
    
    # Check if user owns this entry
    if entry.user_id != current_user.id:
        flash('You can only edit your own entries.', 'warning')
        return redirect(url_for('main.entries'))
    
    form = EntryForm(obj=entry)
    if form.validate_on_submit():
        form.populate_obj(entry)
        db.session.commit()
        flash('Your entry has been updated!', 'success')
        return redirect(url_for('main.view_entry', id=entry.id))
    
    return render_template('edit_entry.html', form=form, entry=entry)

@main_bp.route('/settings')
@login_required
def settings():
    """User settings page."""
    # Initialize forms
    ad_form = AdSettingsForm()
    
    # Set current values
    ad_form.allow_ads.data = current_user.allow_ads
    
    # AdSense configuration
    ad_config = adsense_service.get_ad_config()
    ad_validation = adsense_service.validate_adSense_config()
    
    return render_template('settings.html',
                         ad_form=ad_form,
                         ad_config=ad_config,
                         ad_validation=ad_validation)

@main_bp.route('/settings/update_ads', methods=['POST'])
@login_required
def update_ad_settings():
    """Update ad preferences."""
    ad_form = AdSettingsForm()
    
    if ad_form.validate_on_submit():
        if adsense_service.update_user_preference(current_user, ad_form.allow_ads.data):
            flash('Ad preferences updated successfully!', 'success')
        else:
            flash('Failed to update ad preferences.', 'error')
    else:
        flash('Invalid form submission.', 'error')
    
    return redirect(url_for('main.settings'))

@main_bp.route('/search')
@login_required
def search():
    """Search entries."""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    if not query:
        entries = current_user.entries.order_by(Entry.created_at.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
    else:
        # Simple search implementation
        entries = current_user.entries.filter(
            Entry.content.contains(query) | 
            Entry.title.contains(query)
        ).order_by(Entry.created_at.desc()).paginate(
            page=page, per_page=10, error_out=False
        )
    
    return render_template('search.html', entries=entries, query=query)

@main_bp.route('/analytics')
@login_required
def analytics():
    """Analytics page."""
    # Get analytics data
    total_entries = current_user.entries.count()
    
    # Get entries from last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_entries = current_user.entries.filter(
        Entry.created_at >= thirty_days_ago
    ).all()
    
    # Calculate statistics
    mood_counts = {}
    word_counts = []
    
    for entry in recent_entries:
        # Mood tracking
        if entry.mood:
            mood_counts[entry.mood] = mood_counts.get(entry.mood, 0) + 1
        
        # Word count tracking
        if entry.word_count:
            word_counts.append(entry.word_count)
    
    # Calculate averages
    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
    
    return render_template('analytics.html',
                         total_entries=total_entries,
                         recent_entries=len(recent_entries),
                         mood_counts=mood_counts,
                         avg_words=avg_words)

@main_bp.route('/goals')
@login_required
def goals():
    """Goals page."""
    active_goals = []
    completed_goals = []
    
    if _GOAL_AVAILABLE and Goal:
        active_goals = Goal.query.filter_by(
            user_id=current_user.id,
            status='active'
        ).all()
        
        completed_goals = Goal.query.filter_by(
            user_id=current_user.id,
            status='completed'
        ).all()
    
    return render_template('goals.html',
                         active_goals=active_goals,
                         completed_goals=completed_goals)

@main_bp.route('/adsense-status')
@login_required
def adsense_status():
    """AdSense status page."""
    ad_config = adsense_service.get_ad_config()
    ad_validation = adsense_service.validate_adSense_config()
    ad_stats = adsense_service.get_ad_stats(current_user)
    
    return render_template('adsense_status.html',
                         ad_config=ad_config,
                         ad_validation=ad_validation,
                         ad_stats=ad_stats)

@main_bp.route('/help')
def help():
    """Help page."""
    return render_template('help.html')

@main_bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')

@main_bp.route('/contact')
def contact():
    """Contact page."""
    return render_template('contact.html')

@main_bp.route('/privacy')
def privacy():
    """Privacy policy page."""
    return render_template('privacy.html')

@main_bp.route('/terms')
def terms():
    """Terms of service page."""
    return render_template('terms.html')

# Error handlers
@main_bp.app_errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404

@main_bp.app_errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    return render_template('errors/500.html'), 500

@main_bp.app_errorhandler(403)
def forbidden_error(error):
    """Handle 403 errors."""
    return render_template('errors/403.html'), 403

# Context processors
@main_bp.app_context_processor
def inject_ad_vars():
    """Inject AdSense variables into templates."""
    return {
        'adsense_service': adsense_service,
        'ad_config': adsense_service.get_ad_config()
    }
