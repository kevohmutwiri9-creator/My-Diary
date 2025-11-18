from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, send_file, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from dataclasses import asdict
from app import db
from app.models.entry import Entry
from markdown import markdown
import os
import bleach
import logging
import io
import json
import zipfile

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/ads.txt')
def ads_txt():
    """Serve the ads.txt file for AdSense verification"""
    try:
        ads_txt_path = os.path.join(current_app.root_path, '..', 'ads.txt')
        if os.path.exists(ads_txt_path):
            return send_file(ads_txt_path, mimetype='text/plain')
        else:
            abort(404)
    except Exception as e:
        current_app.logger.error(f"Error serving ads.txt: {str(e)}")
        abort(500)

# Import markdown_to_html from utils
from app.utils.filters import markdown_to_html
from app.forms import AdSettingsForm, ReminderSettingsForm
from app.services.analytics import build_dashboard_analytics

@main_bp.before_request
def log_request_info():
    """Log details about each request."""
    current_app.logger.info(f"Request: {request.method} {request.url}")
    if current_user.is_authenticated:
        current_app.logger.info(f"User: {current_user.username} (ID: {current_user.id})")

@main_bp.route('/')
def index():
    """Home page route."""
    current_app.logger.info('Rendering index page')
    if current_user.is_authenticated:
        current_app.logger.info(f'User {current_user.username} is authenticated, redirecting to dashboard')
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing recent entries."""
    try:
        current_app.logger.info(f'Rendering dashboard for user: {current_user.username}')

        # Get search query from request
        search_query = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)

        # Base query for user's entries
        query = Entry.query.filter_by(user_id=current_user.id)

        # Apply search filter if search query exists
        if search_query:
            current_app.logger.info(f'Searching for: {search_query}')
            # Search in both title and content fields
            search_filter = Entry.title.contains(search_query) | Entry.content.contains(search_query)
            query = query.filter(search_filter)

        # Apply mood filter if specified
        mood_filter = request.args.get('mood', '').strip()
        if mood_filter:
            current_app.logger.info(f'Filtering by mood: {mood_filter}')
            query = query.filter(Entry.mood == mood_filter)

        # Order by creation date (newest first) and paginate
        entries = query.order_by(Entry.created_at.desc())\
                      .paginate(page=page, per_page=10, error_out=False)

        analytics = build_dashboard_analytics(current_user.id)

        stats = dict(analytics['stats'])
        stats['recent_entries'] = analytics['streaks'].get('entries_this_week', 0)
        stats['streak_count'] = analytics['streaks'].get('current', 0)
        stats['best_streak'] = analytics['streaks'].get('best', 0)

        latest_entry = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.created_at.desc()).first()
        if latest_entry and latest_entry.created_at:
            stats['last_entry_at'] = latest_entry.created_at
        else:
            stats['last_entry_at'] = None

        current_app.logger.debug(f'Found {entries.total} entries for user {current_user.username}')
        onboarding_tasks = _build_onboarding_tasks(current_user, stats)
        available_tags = []
        if not search_query:
            from app.models.tag import Tag
            available_tags = Tag.query.join(Tag.entries).filter(Entry.user_id == current_user.id).distinct().all()

        return render_template(
            'dashboard.html',
            entries=entries,
            search_query=search_query,
            mood_filter=mood_filter,
            stats=stats,
            analytics=analytics,
            available_tags=available_tags,
            onboarding_tasks=onboarding_tasks
        )

    except Exception as e:
        current_app.logger.error(f'Error in dashboard route: {str(e)}', exc_info=True)
        flash('An error occurred while loading the dashboard.', 'danger')
        return redirect(url_for('main.index'))


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    """Allow users to manage account preferences."""
    ad_form = AdSettingsForm(obj=current_user)
    reminder_form = ReminderSettingsForm(obj=current_user)

    if request.method == 'POST':
        if 'submit_ads' in request.form and ad_form.validate():
            current_user.allow_ads = ad_form.allow_ads.data
            if current_user.mark_onboarding_task('updated_ad_preferences'):
                db.session.add(current_user)
            db.session.commit()
            flash('Ad preferences updated.', 'success')
            return redirect(url_for('main.account_settings'))

        if 'submit_reminders' in request.form and reminder_form.validate():
            current_user.reminder_opt_in = reminder_form.reminder_opt_in.data
            current_user.reminder_frequency = reminder_form.reminder_frequency.data
            if current_user.reminder_opt_in:
                if current_user.mark_onboarding_task('enabled_reminders'):
                    db.session.add(current_user)
            db.session.commit()
            flash('Reminder settings saved.', 'success')
            return redirect(url_for('main.account_settings'))

    return render_template('settings.html', ad_form=ad_form, reminder_form=reminder_form)

@main_bp.route('/entry/new', methods=['GET', 'POST'])
@login_required
def new_entry():
    """Create a new diary entry."""
    try:
        template_type = request.args.get('template', 'blank')
        selected_template = None

        # Default templates
        default_templates = {
            'gratitude_journal': {'name': 'Gratitude Journal', 'description': 'What are you grateful for today?', 'category': 'Reflection', 'icon': 'bi-heart', 'template_content': 'Today I am grateful for...'},
            'daily_reflection': {'name': 'Daily Reflection', 'description': 'Reflect on your day', 'category': 'Reflection', 'icon': 'bi-lightbulb', 'template_content': 'Today was...'},
            'goal_setting': {'name': 'Goal Setting', 'description': 'Set your goals', 'category': 'Productivity', 'icon': 'bi-bullseye', 'template_content': 'My goals for today are...'},
            'mood_check_in': {'name': 'Mood Check-in', 'description': 'How are you feeling?', 'category': 'Wellness', 'icon': 'bi-emoji-smile', 'template_content': 'I am feeling...'},
            'creative_writing': {'name': 'Creative Writing', 'description': 'Let your creativity flow', 'category': 'Creative', 'icon': 'bi-brush', 'template_content': 'Once upon a time...'},
            'learning_growth': {'name': 'Learning & Growth', 'description': 'What did you learn?', 'category': 'Growth', 'icon': 'bi-book', 'template_content': 'Today I learned...'},
            'dream_journal': {'name': 'Dream Journal', 'description': 'Record your dreams', 'category': 'Personal', 'icon': 'bi-moon-stars', 'template_content': 'Last night I dreamed...'},
            'quick_notes': {'name': 'Quick Notes', 'description': 'Quick thoughts', 'category': 'Notes', 'icon': 'bi-lightning', 'template_content': 'Note to self...'}
        }

        if template_type in default_templates:
            selected_template = default_templates[template_type]

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            mood = request.form.get('mood', '').strip()
            is_private = 'is_private' in request.form
            
            if not content:
                flash('Content is required.', 'danger')
                return render_template('entry.html', 
                                   template=template_type, 
                                   selected_template=selected_template,
                                   now=datetime.utcnow())
            
            # Create new entry
            entry = Entry(
                title=title if title else None,
                content=content,
                mood=mood if mood else None,
                is_private=is_private,
                user_id=current_user.id
            )
            
            db.session.add(entry)
            if current_user.mark_onboarding_task('first_entry_written'):
                db.session.add(current_user)
            db.session.commit()
            
            current_app.logger.info(f'New entry created by user: {current_user.username}')
            flash('Your diary entry has been saved!', 'success')
            return redirect(url_for('main.view_entry', entry_id=entry.id))
        
        # For GET requests, render the form with current time
        return render_template('entry.html', 
                           template=template_type, 
                           selected_template=selected_template,
                           now=datetime.utcnow())

    except Exception as e:
        current_app.logger.error(f'Error in new_entry route: {str(e)}', exc_info=True)
        flash('An error occurred while loading the form.', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/entry/<int:entry_id>')
@login_required
def view_entry(entry_id):
    """View a specific diary entry."""
    entry = Entry.query.get_or_404(entry_id)
    
    # Ensure the current user owns the entry
    if entry.user_id != current_user.id:
        flash('You do not have permission to view this entry.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Convert markdown to HTML
    html_content = markdown_to_html(entry.content)
    
    return render_template('view_entry.html', entry=entry, content=html_content)

@main_bp.route('/entry/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    """Edit an existing diary entry."""
    entry = Entry.query.get_or_404(entry_id)
    
    # Ensure the current user owns the entry
    if entry.user_id != current_user.id:
        flash('You do not have permission to edit this entry.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        mood = request.form.get('mood', '').strip()
        is_private = 'is_private' in request.form
        
        if not content:
            flash('Content is required.', 'danger')
            return render_template('write.html', 
                               title=entry.title, 
                               content=entry.content, 
                               mood=entry.mood, 
                               is_private=entry.is_private,
                               entry=entry)
        
        # Update entry
        entry.title = title if title else None
        entry.content = content
        entry.mood = mood if mood else None
        entry.is_private = is_private
        entry.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Your changes have been saved!', 'success')
        return redirect(url_for('main.view_entry', entry_id=entry.id))
    
    return render_template('write.html', 
                       title=entry.title, 
                       content=entry.content, 
                       mood=entry.mood, 
                       is_private=entry.is_private,
                       entry=entry)

@main_bp.route('/entry/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(entry_id):
    """Delete a diary entry."""
    entry = Entry.query.get_or_404(entry_id)
    
    # Ensure the current user owns the entry
    if entry.user_id != current_user.id:
        flash('You do not have permission to delete this entry.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    db.session.delete(entry)
    db.session.commit()
    
    flash('The entry has been deleted.', 'success')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/preview', methods=['POST'])
@login_required
def preview_markdown():
    """Preview markdown content as HTML."""
    content = request.form.get('content', '')
    if not content:
        return jsonify({'html': ''})

    html = markdown_to_html(content)
    return jsonify({'html': html})

@main_bp.route('/export/json')
@login_required
def export_entries_json():
    """Export all user entries as JSON."""
    try:
        current_app.logger.info(f'Exporting entries as JSON for user: {current_user.username}')

        # Get current filters from request
        search_query = request.args.get('search', '').strip()
        mood_filter = request.args.get('mood', '').strip()

        # Base query for user's entries
        query = Entry.query.filter_by(user_id=current_user.id)

        # Apply search filter if exists
        if search_query:
            search_filter = Entry.title.contains(search_query) | Entry.content.contains(search_query)
            query = query.filter(search_filter)

        # Apply mood filter if exists
        if mood_filter:
            query = query.filter(Entry.mood == mood_filter)

        # Get filtered entries
        entries = query.order_by(Entry.created_at.desc()).all()

        # Convert entries to JSON-serializable format
        entries_data = []
        for entry in entries:
            entries_data.append({
                'id': entry.id,
                'title': entry.title,
                'content': entry.content,
                'mood': entry.mood,
                'is_private': entry.is_private,
                'created_at': entry.created_at.isoformat() if entry.created_at else None,
                'updated_at': entry.updated_at.isoformat() if entry.updated_at else None
            })

        # Create JSON response
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'user': current_user.username,
            'total_entries': len(entries_data),
            'filters_applied': {
                'search': search_query if search_query else None,
                'mood': mood_filter if mood_filter else None
            },
            'entries': entries_data
        }

        # Return JSON file as download
        from flask import Response
        import json

        response = Response(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=diary_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'}
        )

        current_app.logger.info(f'Successfully exported {len(entries_data)} entries for user {current_user.username}')
        return response

    except Exception as e:
        current_app.logger.error(f'Error exporting entries: {str(e)}', exc_info=True)
        flash('An error occurred while exporting your entries.', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/entry/<int:entry_id>/export/json')
@login_required
def export_entry_json(entry_id):
    """Export a single entry as JSON."""
    try:
        entry = Entry.query.get_or_404(entry_id)

        # Ensure the current user owns the entry
        if entry.user_id != current_user.id:
            flash('You do not have permission to export this entry.', 'danger')
            return redirect(url_for('main.dashboard'))

        current_app.logger.info(f'Exporting entry {entry_id} as JSON for user: {current_user.username}')

        # Convert entry to JSON-serializable format
        entry_data = {
            'id': entry.id,
            'title': entry.title,
            'content': entry.content,
            'mood': entry.mood,
            'is_private': entry.is_private,
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
            'updated_at': entry.updated_at.isoformat() if entry.updated_at else None
        }

        # Create JSON response
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'user': current_user.username,
            'entry': entry_data
        }

        # Return JSON file as download
        from flask import Response
        import json

        response = Response(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=diary_entry_{entry_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'}
        )

        current_app.logger.info(f'Successfully exported entry {entry_id} for user {current_user.username}')
        return response

    except Exception as e:
        current_app.logger.error(f'Error exporting entry {entry_id}: {str(e)}', exc_info=True)
        flash('An error occurred while exporting this entry.', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/export/markdown')
@login_required
def export_entries_markdown():
    """Export all user entries as Markdown."""
    try:
        current_app.logger.info(f'Exporting entries as Markdown for user: {current_user.username}')

        # Get current filters from request
        search_query = request.args.get('search', '').strip()
        mood_filter = request.args.get('mood', '').strip()

        # Base query for user's entries
        query = Entry.query.filter_by(user_id=current_user.id)

        # Apply search filter if exists
        if search_query:
            search_filter = Entry.title.contains(search_query) | Entry.content.contains(search_query)
            query = query.filter(search_filter)

        # Apply mood filter if exists
        if mood_filter:
            query = query.filter(Entry.mood == mood_filter)

        # Get filtered entries
        entries = query.order_by(Entry.created_at.desc()).all()

        if not entries:
            flash('No entries to export.', 'info')
            return redirect(url_for('main.dashboard'))

        # Create markdown content
        markdown_content = f"# My Diary Export\n\n"
        markdown_content += f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        markdown_content += f"**Total Entries:** {len(entries)}\n"

        # Add filters info if any applied
        filters_applied = []
        if search_query:
            filters_applied.append(f"Search: '{search_query}'")
        if mood_filter:
            filters_applied.append(f"Mood: '{mood_filter}'")

        if filters_applied:
            markdown_content += f"**Filters Applied:** {' | '.join(filters_applied)}\n"

        markdown_content += "\n---\n\n"

        for entry in entries:
            markdown_content += f"## {entry.title or 'Untitled Entry'}\n\n"
            if entry.mood:
                markdown_content += f"**Mood:** {entry.mood}\n\n"
            markdown_content += f"**Date:** {entry.created_at.strftime('%B %d, %Y at %I:%M %p')}\n\n"
            if entry.updated_at and entry.updated_at != entry.created_at:
                markdown_content += f"**Updated:** {entry.updated_at.strftime('%B %d, %Y at %I:%M %p')}\n\n"
            markdown_content += f"{entry.content}\n\n"
            markdown_content += "---\n\n"

        # Return markdown file as download
        from flask import Response

        response = Response(
            markdown_content,
            mimetype='text/markdown',
            headers={'Content-Disposition': f'attachment; filename=diary_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'}
        )

        current_app.logger.info(f'Successfully exported {len(entries)} entries as Markdown for user {current_user.username}')
        return response

    except Exception as e:
        current_app.logger.error(f'Error exporting entries as Markdown: {str(e)}', exc_info=True)
        flash('An error occurred while exporting your entries.', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/backup/download')
@login_required
def download_backup():
    """Provide a single ZIP download containing all diary data."""
    try:
        current_app.logger.info(f'Generating full backup for user: {current_user.username}')

        export_time = datetime.utcnow()
        entries = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.created_at.desc()).all()

        entries_payload = [entry.to_dict() for entry in entries]

        metadata = {
            'generated_at': export_time.isoformat(),
            'app_version': current_app.config.get('VERSION', '1.0.0'),
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'allow_ads': current_user.allow_ads,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None
            },
            'counts': {
                'entries': len(entries_payload)
            }
        }

        markdown_sections = [
            '# My Diary Backup',
            f'**Generated:** {export_time.strftime("%Y-%m-%d %H:%M:%S UTC")}',
            f'**Total Entries:** {len(entries_payload)}',
            ''
        ]

        if entries:
            markdown_sections.append('---')
            for entry in entries:
                header = entry.title or 'Untitled Entry'
                markdown_sections.append(f'## {header}')
                markdown_sections.append(f'**Date:** {entry.created_at.strftime("%B %d, %Y %H:%M")}' if entry.created_at else '**Date:** Unknown')
                if entry.updated_at and entry.updated_at != entry.created_at:
                    markdown_sections.append(f'**Updated:** {entry.updated_at.strftime("%B %d, %Y %H:%M")}')
                if entry.mood:
                    markdown_sections.append(f'**Mood:** {entry.mood}')
                if entry.tags:
                    markdown_sections.append('**Tags:** ' + ', '.join(tag.name for tag in entry.tags))
                markdown_sections.append('')
                markdown_sections.append(entry.content)
                markdown_sections.append('')
                markdown_sections.append('---')
        else:
            markdown_sections.append('No entries yet. Start writing to build your history!')

        markdown_output = '\n'.join(markdown_sections)

        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('metadata.json', json.dumps(metadata, indent=2, ensure_ascii=False))
            archive.writestr('entries.json', json.dumps(entries_payload, indent=2, ensure_ascii=False))
            archive.writestr('entries.md', markdown_output)

        archive_buffer.seek(0)
        filename = f"my-diary-backup_{export_time.strftime('%Y%m%d_%H%M%S')}.zip"

        if current_user.mark_onboarding_task('backup_downloaded'):
            db.session.add(current_user)
            db.session.commit()

        current_app.logger.info(f'Backup archive ready for user {current_user.username} ({len(entries_payload)} entries)')
        return send_file(
            archive_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        current_app.logger.error(f'Error creating backup for user {current_user.username}: {str(e)}', exc_info=True)
        flash('We could not generate your backup. Please try again in a moment.', 'danger')
        return redirect(url_for('main.account_settings'))

@main_bp.route('/templates')
@login_required
def get_templates():
    """Get available templates for new entries."""
    try:
        from app.models.template import EntryTemplate

        # Get default system templates
        default_templates = EntryTemplate.get_default_templates()

        # Get user's custom templates
        custom_templates = EntryTemplate.query.filter_by(user_id=current_user.id)\
                                             .order_by(EntryTemplate.created_at.desc())\
                                             .all()

        # Convert default templates to template objects for consistent handling
        templates_data = []
        for template in default_templates:
            templates_data.append({
                'id': None,
                'name': template['name'],
                'description': template['description'],
                'category': template['category'],
                'icon': template['icon'],
                'template_content': template['template_content'],
                'is_default': True,
                'user_id': None
            })

        # Add custom templates
        for template in custom_templates:
            templates_data.append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'category': template.category,
                'icon': template.icon,
                'template_content': template.template_content,
                'is_default': False,
                'user_id': template.user_id
            })

        # Group templates by category
        categories = {}
        for template in templates_data:
            category = template['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(template)

        return jsonify({
            'success': True,
            'categories': categories,
            'total_templates': len(templates_data)
        })

    except Exception as e:
        current_app.logger.error(f'Error getting templates: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load templates'}), 500


def _build_onboarding_tasks(user, stats):
    tasks = [
        {
            'key': 'first_entry_written',
            'label': 'Write your first diary entry',
            'help': 'Capture anything about your day to unlock insights.',
            'cta_label': 'Write now',
            'cta_url': url_for('main.new_entry'),
            'completed': stats['total_entries'] > 0 or user.has_completed_task('first_entry_written')
        },
        {
            'key': 'enabled_reminders',
            'label': 'Enable writing reminders',
            'help': 'Get gentle nudges to keep your journaling habit on track.',
            'cta_label': 'Configure reminders',
            'cta_url': url_for('main.account_settings'),
            'completed': bool(user.reminder_opt_in or user.has_completed_task('enabled_reminders'))
        },
        {
            'key': 'explored_calendar',
            'label': 'Explore your calendar view',
            'help': 'See your entries on a monthly calendar to spot gaps.',
            'cta_label': 'Open calendar',
            'cta_url': url_for('main.calendar_view'),
            'completed': user.has_completed_task('explored_calendar')
        },
        {
            'key': 'backup_downloaded',
            'label': 'Download a secure backup',
            'help': 'Keep an offline copy of your diary for peace of mind.',
            'cta_label': 'Download backup',
            'cta_url': url_for('main.account_settings'),
            'completed': user.has_completed_task('backup_downloaded')
        }
    ]

    pending = [task for task in tasks if not task['completed']]
    completed = [task for task in tasks if task['completed']]

    return {
        'pending': pending,
        'completed': completed,
        'total': len(tasks)
    }

@main_bp.route('/calendar')
@login_required
def calendar_view():
    """Calendar view for browsing entries by date."""
    try:
        from datetime import datetime, date
        import calendar

        # Get current month/year from parameters or use current date
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)

        # Ensure valid month/year
        if not (1 <= month <= 12):
            month = datetime.now().month
        if not (2000 <= year <= 2100):
            year = datetime.now().year

        # Get first day of month and number of days
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Get all entries for the current user in this month
        entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.created_at >= first_day,
            Entry.created_at <= last_day
        ).order_by(Entry.created_at.desc()).all()

        # Group entries by date
        entries_by_date = {}
        for entry in entries:
            entry_date = entry.created_at.date()
            if entry_date not in entries_by_date:
                entries_by_date[entry_date] = []
            entries_by_date[entry_date].append(entry)

        # Generate calendar data
        cal = calendar.monthcalendar(year, month)
        calendar_data = []

        for week in cal:
            week_data = []
            for day in week:
                if day == 0:  # No date (empty cell)
                    week_data.append({
                        'day': None,
                        'date': None,
                        'entries': [],
                        'is_today': False,
                        'is_current_month': False
                    })
                else:
                    current_date = date(year, month, day)
                    today = date.today()

                    week_data.append({
                        'day': day,
                        'date': current_date,
                        'entries': entries_by_date.get(current_date, []),
                        'is_today': current_date == today,
                        'is_current_month': True
                    })
            calendar_data.append(week_data)

        # Navigation data
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        # Month statistics
        total_entries_this_month = len(entries)
        days_with_entries = len(entries_by_date)

        if current_user.mark_onboarding_task('explored_calendar'):
            db.session.add(current_user)
            db.session.commit()

        return render_template('calendar.html',
                             calendar_data=calendar_data,
                             current_month=month,
                             current_year=year,
                             month_name=calendar.month_name[month],
                             prev_month=prev_month,
                             prev_year=prev_year,
                             next_month=next_month,
                             next_year=next_year,
                             total_entries=total_entries_this_month,
                             days_with_entries=days_with_entries,
                             entries_by_date=entries_by_date)

    except Exception as e:
        current_app.logger.error(f'Error in calendar view: {str(e)}', exc_info=True)
        flash('An error occurred while loading the calendar.', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/api/welcome')
def api_welcome():
    """API endpoint that returns a welcome message with request metadata logging."""
    return jsonify({
        'message': 'Welcome to the Flask API Service!',
        'method': request.method,
        'path': request.path
    })

@main_bp.route('/calendar/entries/<date>')
@login_required
def calendar_entries_by_date(date):
    """Get entries for a specific date (AJAX endpoint)."""
    from datetime import datetime

    try:
        target_date = datetime.strptime(date, '%Y-%m-%d').date()

        entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            db.func.date(Entry.created_at) == target_date
        ).order_by(Entry.created_at.asc()).all()

        entries_data = [
            {
                'id': entry.id,
                'title': entry.title,
                'mood': entry.mood,
                'created_at': entry.created_at.isoformat() if entry.created_at else None,
                'preview': entry.content[:200] if entry.content else ''
            }
            for entry in entries
        ]

        return jsonify({'success': True, 'entries': entries_data})

    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400
    except Exception as e:
        current_app.logger.error(f'Error fetching calendar entries: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load entries for the selected date.'}), 500
