from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models.entry import Entry
from markdown import markdown
import bleach
import logging

# Create blueprint
main_bp = Blueprint('main', __name__)

# Import markdown_to_html from utils
from app.utils.filters import markdown_to_html

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

        # Get dashboard statistics
        from datetime import datetime, timedelta
        from sqlalchemy import func

        # Total entries count
        total_entries = Entry.query.filter_by(user_id=current_user.id).count()

        # Entries this month
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        entries_this_month = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.created_at >= start_of_month
        ).count()

        # Most common mood
        mood_stats = db.session.query(
            Entry.mood,
            func.count(Entry.mood).label('count')
        ).filter(
            Entry.user_id == current_user.id,
            Entry.mood.isnot(None)
        ).group_by(Entry.mood).order_by(func.count(Entry.mood).desc()).first()

        most_common_mood = mood_stats.mood if mood_stats else None

        # Recent entries (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.created_at >= week_ago
        ).count()

        stats = {
            'total_entries': total_entries,
            'entries_this_month': entries_this_month,
            'most_common_mood': most_common_mood,
            'recent_entries': recent_entries
        }

        current_app.logger.debug(f'Found {entries.total} entries for user {current_user.username}')
        return render_template('dashboard.html', entries=entries, search_query=search_query, mood_filter=mood_filter, stats=stats)

    except Exception as e:
        current_app.logger.error(f'Error in dashboard route: {str(e)}', exc_info=True)
        flash('An error occurred while loading the dashboard.', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/entry/new', methods=['GET', 'POST'])
@login_required
def new_entry():
    """Create a new diary entry."""
    try:
        # Handle template selection
        template_id = request.args.get('template')
        selected_template = None

        if request.method == 'GET' and template_id:
            from app.models.template import EntryTemplate

            # Try to find custom template first
            template = EntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
            if template:
                selected_template = {
                    'id': template.id,
                    'name': template.name,
                    'description': template.description,
                    'category': template.category,
                    'icon': template.icon,
                    'template_content': template.template_content
                }
            else:
                # Check default templates
                default_templates = EntryTemplate.get_default_templates()
                for default_template in default_templates:
                    # Match template names with URL parameter
                    template_url_param = template_id.lower().replace('_', ' ')
                    if default_template['name'].lower() == template_url_param:
                        selected_template = {
                            'id': None,
                            'name': default_template['name'],
                            'description': default_template['description'],
                            'category': default_template['category'],
                            'icon': default_template['icon'],
                            'template_content': default_template['template_content']
                        }
                        break

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            mood = request.form.get('mood', '').strip()
            is_private = 'is_private' in request.form
            
            if not content:
                flash('Content is required.', 'danger')
                return render_template('write.html', title=title, content=content, mood=mood, is_private=is_private, selected_template=selected_template)
            
            # Create new entry
            entry = Entry(
                title=title if title else None,
                content=content,
                mood=mood if mood else None,
                is_private=is_private,
                user_id=current_user.id
            )
            
            db.session.add(entry)
            db.session.commit()
            
            current_app.logger.info(f'New entry created by user: {current_user.username}')
            flash('Your diary entry has been saved!', 'success')
            return redirect(url_for('main.view_entry', entry_id=entry.id))
        
        # GET request - show empty form
        return render_template('write.html', selected_template=selected_template)
        
    except Exception as e:
        current_app.logger.error(f'Error in new entry route: {str(e)}', exc_info=True)
        flash('An error occurred while creating a new entry.', 'danger')
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

@main_bp.route('/calendar/entries/<date>')
@login_required
def calendar_entries_by_date(date):
    """Get entries for a specific date (AJAX endpoint)."""
    try:
        from datetime import datetime

        # Parse date
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400

        # Get entries for this date
        entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.created_at >= datetime.combine(target_date, datetime.min.time()),
            Entry.created_at < datetime.combine(target_date + timedelta(days=1), datetime.min.time())
        ).order_by(Entry.created_at.desc()).all()

        # Convert to JSON format
        entries_data = []
        for entry in entries:
            entries_data.append({
                'id': entry.id,
                'title': entry.title,
                'mood': entry.mood,
                'content_preview': entry.content[:150] + '...' if len(entry.content) > 150 else entry.content,
                'created_at': entry.created_at.strftime('%I:%M %p'),
                'url': url_for('main.view_entry', entry_id=entry.id)
            })

        return jsonify({
            'success': True,
            'date': target_date.strftime('%B %d, %Y'),
            'entries': entries_data,
            'total_entries': len(entries_data)
        })

    except Exception as e:
        current_app.logger.error(f'Error getting calendar entries: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load entries'}), 500