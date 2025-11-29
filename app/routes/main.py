from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, send_file, abort, session
from flask_wtf.csrf import csrf, CSRFError
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from dataclasses import asdict
from werkzeug.utils import secure_filename
from app import db
from app.models.entry import Entry
from app.models.media import Media
from app.models.user import User
from app.services.ai_features import ai_features
from app.services.media_service import save_media, delete_media, get_user_media, link_media_to_entry
from app.services.productivity_service import (
    get_user_productivity_stats, get_productivity_recommendations, 
    generate_calendar_events, update_user_goals
)
from app.services.social_service import (
    get_anonymous_public_entries, share_entry_anonymously, get_community_stats,
    get_trending_topics, get_inspiration_prompts, get_user_privacy_settings,
    update_privacy_settings, like_public_entry, report_public_entry
)
from app.services.security_service import (
    setup_2fa, verify_2fa_setup, verify_2fa_token, disable_2fa,
    backup_user_data, restore_user_data, get_security_settings,
    update_security_settings, generate_encryption_key
)
from app.services.i18n_service import (
    get_current_language, set_language, translate, get_supported_languages,
    get_language_direction, format_date, format_number
)
from app.utils.cookie_consent import CookieConsent
from app.utils.error_handler import handle_errors, safe_operation, DatabaseError, ValidationError
from app.utils.performance_optimizer import (
    monitor_performance, cache_function_result, 
    PaginationOptimizer, LazyLoader
)
from markdown import markdown
import os
import bleach

def _expand_semantic_query(query):
    """
    Expand a search query with semantic keywords for better matching.
    This is a simplified version - in production you'd use proper word embeddings.
    """
    # Define semantic keyword groups
    semantic_groups = {
        'happy': ['happy', 'joy', 'glad', 'pleased', 'delighted', 'cheerful', 'content', 'satisfied'],
        'sad': ['sad', 'unhappy', 'depressed', 'down', 'blue', 'melancholy', 'sorrowful', 'gloomy'],
        'angry': ['angry', 'mad', 'furious', 'irate', 'annoyed', 'frustrated', 'upset', 'resentful'],
        'work': ['work', 'job', 'career', 'office', 'business', 'employment', 'profession', 'task'],
        'family': ['family', 'parents', 'children', 'siblings', 'relatives', 'home', 'household'],
        'health': ['health', 'exercise', 'fitness', 'diet', 'wellness', 'medical', 'doctor', 'sick'],
        'stress': ['stress', 'anxiety', 'worry', 'tension', 'pressure', 'overwhelmed', 'nervous'],
        'success': ['success', 'achieve', 'accomplish', 'win', 'victory', 'triumph', 'goal', 'progress'],
        'relationship': ['relationship', 'love', 'romance', 'dating', 'marriage', 'partner', 'intimate'],
        'money': ['money', 'financial', 'income', 'salary', 'budget', 'expenses', 'wealth', 'cost'],
    }
    
    query_lower = query.lower()
    expanded_keywords = [query]  # Always include original query
    
    # Check if query matches any semantic group
    for key, keywords in semantic_groups.items():
        if key in query_lower or any(kw in query_lower for kw in keywords):
            expanded_keywords.extend(keywords)
            break
    
    return list(set(expanded_keywords))  # Remove duplicates
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
@monitor_performance(threshold=1.0)
def index():
    """Home page route."""
    current_app.logger.info('Rendering index page')
    if current_user.is_authenticated:
        current_app.logger.info(f'User {current_user.username} is authenticated, redirecting to dashboard')
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
@monitor_performance(threshold=2.0)
@cache_function_result(timeout=300, key_func=lambda: f"dashboard_data:{current_user.id}")
def dashboard():
    """User dashboard showing recent entries."""
    try:
        current_app.logger.info(f'Rendering dashboard for user: {current_user.username}')
        
        # Get search parameters
        search_query = request.args.get('search', '').strip()
        search_type = request.args.get('search_type', 'all')
        page = request.args.get('page', 1, type=int)
        
        # Date filters
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        
        # Other filters
        mood_filter = request.args.get('mood', '').strip()
        tag_filter = request.args.get('tag', '').strip()
        words_min = request.args.get('words_min', '').strip()
        words_max = request.args.get('words_max', '').strip()
        sort_by = request.args.get('sort', 'date_desc')

        # Base query for user's entries
        query = Entry.query.filter_by(user_id=current_user.id)

        # Apply search filter
        if search_query:
            current_app.logger.info(f'Searching for: {search_query} (type: {search_type})')
            
            if search_type == 'semantic':
                # Semantic search using word embeddings (simplified version)
                # In a real implementation, you'd use libraries like spaCy, sentence-transformers, or OpenAI embeddings
                # For now, we'll use keyword matching with synonyms
                semantic_keywords = _expand_semantic_query(search_query)
                semantic_filter = None
                for keyword in semantic_keywords:
                    keyword_filter = Entry.title.contains(keyword) | Entry.content.contains(keyword)
                    if semantic_filter is None:
                        semantic_filter = keyword_filter
                    else:
                        semantic_filter = semantic_filter | keyword_filter
                if semantic_filter:
                    query = query.filter(semantic_filter)
            elif search_type == 'title':
                query = query.filter(Entry.title.contains(search_query))
            elif search_type == 'content':
                query = query.filter(Entry.content.contains(search_query))
            else:  # 'all'
                search_filter = Entry.title.contains(search_query) | Entry.content.contains(search_query)
                query = query.filter(search_filter)

        # Apply date range filter
        if date_from:
            try:
                from datetime import datetime
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Entry.created_at >= date_from_dt)
                current_app.logger.info(f'Filtering from date: {date_from}')
            except ValueError:
                pass
                
        if date_to:
            try:
                from datetime import datetime
                date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
                # Add one day to make it inclusive
                from datetime import timedelta
                date_to_dt = date_to_dt + timedelta(days=1)
                query = query.filter(Entry.created_at < date_to_dt)
                current_app.logger.info(f'Filtering to date: {date_to}')
            except ValueError:
                pass

        # Apply mood filter
        if mood_filter:
            current_app.logger.info(f'Filtering by mood: {mood_filter}')
            query = query.filter(Entry.mood == mood_filter)

        # Apply tag filter
        if tag_filter:
            current_app.logger.info(f'Filtering by tag: {tag_filter}')
            from app.models.tag import Tag
            tag = Tag.query.filter_by(name=tag_filter).first()
            if tag:
                query = query.filter(Entry.tags.any(id=tag.id))

        # Apply word count filters
        if words_min:
            try:
                min_words = int(words_min)
                query = query.filter(Entry.word_count >= min_words)
                current_app.logger.info(f'Filtering min words: {min_words}')
            except ValueError:
                pass
                
        if words_max:
            try:
                max_words = int(words_max)
                query = query.filter(Entry.word_count <= max_words)
                current_app.logger.info(f'Filtering max words: {max_words}')
            except ValueError:
                pass

        # Apply sorting
        if sort_by == 'date_asc':
            query = query.order_by(Entry.created_at.asc())
        elif sort_by == 'title_asc':
            query = query.order_by(Entry.title.asc())
        elif sort_by == 'title_desc':
            query = query.order_by(Entry.title.desc())
        elif sort_by == 'words_desc':
            query = query.order_by(Entry.word_count.desc())
        elif sort_by == 'words_asc':
            query = query.order_by(Entry.word_count.asc())
        else:  # date_desc (default)
            query = query.order_by(Entry.created_at.desc())

        # Paginate results using optimized pagination
        pagination_data = PaginationOptimizer.get_paginated_query(query, page, per_page=10)
        entries = pagination_data

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

        current_app.logger.debug(f'Found {entries.get("total", 0)} entries for user {current_user.username}')
        onboarding_tasks = _build_onboarding_tasks(current_user, stats)
        available_tags = []
        if not search_query:
            from app.models.tag import Tag
            available_tags = Tag.query.join(Tag.entries).filter(Entry.user_id == current_user.id).distinct().all()
        
        # Pass all filter parameters to template for form persistence
        return render_template(
            'dashboard.html',
            entries=entries.get('items', []),  # Extract items from pagination dict
            pagination=entries,  # Pass pagination info separately
            search_query=search_query,
            search_type=search_type,
            mood_filter=mood_filter,
            tag_filter=tag_filter,
            date_from=date_from,
            date_to=date_to,
            words_min=words_min,
            words_max=words_max,
            sort_by=sort_by,
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
            tags = request.form.get('tags', '').strip()
            is_private = 'is_private' in request.form
            media_ids = request.form.getlist('media_ids')  # Get media IDs from form
            
            if not content:
                flash('Content is required.', 'danger')
                return render_template('write.html', 
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
            db.session.flush()  # Get the entry ID without committing
            
            # Link media to entry if provided
            if media_ids:
                success, error = link_media_to_entry(media_ids, entry.id, current_user.id)
                if error:
                    current_app.logger.error(f'Error linking media to entry: {error}')
            
            # Handle tags
            if tags:
                from app.models.tag import Tag
                tag_names = [tag.strip() for tag in tags.split(',') if tag.strip()]
                for tag_name in tag_names:
                    tag = Tag.query.filter_by(name=tag_name, user_id=current_user.id).first()
                    if not tag:
                        tag = Tag(name=tag_name, user_id=current_user.id)
                        db.session.add(tag)
                    entry.tags.append(tag)
            
            if current_user.mark_onboarding_task('first_entry_written'):
                db.session.add(current_user)
            db.session.commit()
            
            current_app.logger.info(f'New entry created by user: {current_user.username}')
            flash('Your diary entry has been saved!', 'success')
            return redirect(url_for('main.view_entry', entry_id=entry.id))
        
        # For GET requests, render the form with current time
        return render_template('write.html', 
                           template=template_type, 
                           selected_template=selected_template,
                           now=datetime.utcnow())

    except Exception as e:
        current_app.logger.error(f'Error in new_entry route: {str(e)}', exc_info=True)
        flash('An error occurred while loading the form.', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/transcribe-audio', methods=['POST'])
@login_required
def transcribe_audio():
    """Transcribe audio file to text."""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # For now, return a placeholder transcription
        # In a real implementation, you would integrate with:
        # - OpenAI Whisper API
        # - Google Speech-to-Text
        # - Azure Speech Services
        # - Or a local Whisper model
        
        # Placeholder transcription based on duration
        audio_file.seek(0, 2)  # Seek to end
        file_size = audio_file.tell()
        audio_file.seek(0)  # Reset to beginning
        
        # Estimate duration (very rough approximation for WebM audio)
        estimated_duration = file_size / (1024 * 10)  # Rough estimate
        
        placeholder_text = f"This is a placeholder transcription for your voice recording. "
        placeholder_text += f"The recording appears to be approximately {estimated_duration:.1f} seconds long. "
        placeholder_text += f"In a production environment, this would be replaced with actual AI-powered transcription using services like OpenAI Whisper, Google Speech-to-Text, or Azure Speech Services. "
        placeholder_text += f"The audio file size is {file_size / 1024:.1f} KB."
        
        return jsonify({
            'transcription': placeholder_text,
            'duration': estimated_duration,
            'file_size': file_size
        })
        
    except Exception as e:
        current_app.logger.error(f'Error in transcribe_audio route: {str(e)}', exc_info=True)
        return jsonify({'error': 'Transcription failed'}), 500

@main_bp.route('/ai/prompt', methods=['GET'])
@login_required
def get_ai_prompt():
    """Get personalized AI writing prompt."""
    try:
        current_mood = request.args.get('mood')
        
        # Get user's recent entries for personalization
        user_entries = Entry.query.filter_by(user_id=current_user.id)\
                                .order_by(Entry.created_at.desc())\
                                .limit(20).all()
        
        prompt_data = ai_features.get_personalized_prompt(user_entries, current_mood)
        
        return jsonify(prompt_data)
        
    except Exception as e:
        current_app.logger.error(f'Error in get_ai_prompt route: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to generate prompt'}), 500

@main_bp.route('/ai/suggestions', methods=['POST'])
@login_required
def get_ai_suggestions():
    """Get smart writing suggestions based on current text."""
    try:
        data = request.get_json()
        current_text = data.get('text', '')
        cursor_position = data.get('cursor_position', 0)
        
        suggestions = ai_features.get_smart_suggestions(current_text, cursor_position)
        
        return jsonify(suggestions)
        
    except Exception as e:
        current_app.logger.error(f'Error in get_ai_suggestions route: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to generate suggestions'}), 500

@main_bp.route('/ai/mood-insights', methods=['GET'])
@login_required
def get_mood_insights():
    """Get insights and recommendations for current mood."""
    try:
        mood = request.args.get('mood')
        if not mood:
            return jsonify({'error': 'Mood parameter required'}), 400
        
        # Get user's recent entries for context
        recent_entries = Entry.query.filter_by(user_id=current_user.id)\
                                  .order_by(Entry.created_at.desc())\
                                  .limit(10).all()
        
        insights = ai_features.get_mood_insights(mood)
        wellness_tips = ai_features.get_wellness_tips(mood, recent_entries)
        
        return jsonify({
            'insights': insights,
            'wellness_tips': wellness_tips,
            'mood': mood
        })
        
    except Exception as e:
        current_app.logger.error(f'Error in get_mood_insights route: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to get mood insights'}), 500

@main_bp.route('/ai/analyze-entry', methods=['POST'])
@login_required
def analyze_entry():
    """Analyze entry sentiment and provide insights."""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text.strip():
            return jsonify({'error': 'Text is required for analysis'}), 400
        
        sentiment_analysis = ai_features.analyze_entry_sentiment(text)
        suggestions = ai_features.get_smart_suggestions(text)
        
        return jsonify({
            'sentiment': sentiment_analysis,
            'suggestions': suggestions,
            'word_count': len(text.split())
        })
        
    except Exception as e:
        current_app.logger.error(f'Error in analyze_entry route: {str(e)}', exc_info=True)
        return jsonify({'error': 'Failed to analyze entry'}), 500

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
        tags = request.form.get('tags', '').strip()
        is_private = 'is_private' in request.form
        
        if not content:
            flash('Content is required.', 'danger')
            return render_template('edit_entry.html', entry=entry)
        
        # Update entry
        entry.title = title if title else None
        entry.content = content
        entry.mood = mood if mood else None
        entry.is_private = is_private
        entry.updated_at = datetime.utcnow()
        
        # Handle tags
        if tags:
            from app.models.tag import Tag
            tag_names = [tag.strip() for tag in tags.split(',') if tag.strip()]
            entry.tags.clear()
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name, user_id=current_user.id).first()
                if not tag:
                    tag = Tag(name=tag_name, user_id=current_user.id)
                    db.session.add(tag)
                entry.tags.append(tag)
        
        db.session.commit()
        
        flash('Your changes have been saved!', 'success')
        return redirect(url_for('main.view_entry', entry_id=entry.id))
    
    return render_template('edit_entry.html', entry=entry)

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
@csrf.exempt  # Exempt from CSRF protection for AJAX preview
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

@main_bp.route('/media/upload', methods=['POST'])
@login_required
def upload_media():
    """Handle file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        entry_id = request.form.get('entry_id', None)
        
        media, error = save_media(file, current_user.id, entry_id)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        
        return jsonify({
            'success': True,
            'media': media.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f'Error uploading media: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Upload failed'}), 500

@main_bp.route('/media/<int:media_id>/delete', methods=['POST'])
@login_required
def delete_media_route(media_id):
    """Delete a media file"""
    try:
        success, error = delete_media(media_id, current_user.id)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f'Error deleting media: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Delete failed'}), 500

@main_bp.route('/media')
@login_required
def media_gallery():
    """Display user's media gallery"""
    try:
        media_list = get_user_media(current_user.id)
        return render_template('media_gallery.html', media_list=media_list)
        
    except Exception as e:
        current_app.logger.error(f'Error loading media gallery: {str(e)}', exc_info=True)
        flash('Error loading media gallery', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    try:
        upload_dir = os.path.join(current_app.root_path, '..', 'uploads')
        return send_file(os.path.join(upload_dir, filename))
    except FileNotFoundError:
        abort(404)

@main_bp.route('/media/link-to-entry', methods=['POST'])
@login_required
def link_media_to_entry_route():
    """Link multiple media files to an entry"""
    try:
        data = request.get_json()
        media_ids = data.get('media_ids', [])
        entry_id = data.get('entry_id')
        
        if not entry_id:
            return jsonify({'success': False, 'error': 'Entry ID required'}), 400
        
        success, error = link_media_to_entry(media_ids, entry_id, current_user.id)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f'Error linking media to entry: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Link failed'}), 500

@main_bp.route('/productivity')
@login_required
def productivity_dashboard():
    """Display productivity dashboard with stats and insights."""
    try:
        stats = get_user_productivity_stats(current_user.id)
        recommendations = get_productivity_recommendations(current_user.id)
        
        return render_template('productivity.html', 
                             stats=stats, 
                             recommendations=recommendations)
        
    except Exception as e:
        current_app.logger.error(f'Error loading productivity dashboard: {str(e)}', exc_info=True)
        flash('Error loading productivity dashboard', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/productivity/goals', methods=['POST'])
@login_required
@handle_errors("Unable to update goals. Please try again.", log_error=True)
def update_goals():
    """Update user's writing goals."""
    daily_goal = request.form.get('daily_goal', type=int)
    weekly_goal = request.form.get('weekly_goal', type=int)
    
    success = update_user_goals(current_user.id, daily_goal, weekly_goal)
    
    if success:
        flash('Goals updated successfully!', 'success')
    else:
        flash('Error updating goals', 'danger')
        
    return redirect(url_for('main.productivity_dashboard'))

@main_bp.route('/api/productivity/stats')
@login_required
def api_productivity_stats():
    """API endpoint for productivity statistics."""
    try:
        stats = get_user_productivity_stats(current_user.id)
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        current_app.logger.error(f'Error getting productivity stats: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load stats'}), 500

@main_bp.route('/api/productivity/recommendations')
@login_required
def api_productivity_recommendations():
    """API endpoint for productivity recommendations."""
    try:
        recommendations = get_productivity_recommendations(current_user.id)
        return jsonify({'success': True, 'recommendations': recommendations})
        
    except Exception as e:
        current_app.logger.error(f'Error getting recommendations: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load recommendations'}), 500

@main_bp.route('/api/calendar/events/<int:year>/<int:month>')
@login_required
def api_calendar_events(year, month):
    """API endpoint for calendar events."""
    try:
        events = generate_calendar_events(current_user.id, year, month)
        return jsonify({'success': True, 'events': events})
        
    except Exception as e:
        current_app.logger.error(f'Error getting calendar events: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load events'}), 500

# Social Features Routes
@main_bp.route('/community')
@login_required
def community_feed():
    """Display community feed with anonymous public entries."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        entries = get_anonymous_public_entries(limit=per_page, offset=(page-1)*per_page)
        community_stats = get_community_stats()
        trending_topics = get_trending_topics(5)
        
        return render_template('community.html', 
                             entries=entries, 
                             community_stats=community_stats,
                             trending_topics=trending_topics,
                             page=page)
        
    except Exception as e:
        current_app.logger.error(f'Error loading community feed: {str(e)}', exc_info=True)
        flash('Error loading community feed', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/share-entry/<int:entry_id>', methods=['POST'])
@login_required
def share_entry(entry_id):
    """Share an entry anonymously to the community."""
    try:
        result = share_entry_anonymously(entry_id, current_user.id)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['error'], 'danger')
            
        return redirect(url_for('main.view_entry', entry_id=entry_id))
        
    except Exception as e:
        current_app.logger.error(f'Error sharing entry: {str(e)}', exc_info=True)
        flash('Error sharing entry', 'danger')
        return redirect(url_for('main.view_entry', entry_id=entry_id))

@main_bp.route('/privacy-settings')
@login_required
def privacy_settings():
    """Display privacy settings page."""
    try:
        settings = get_user_privacy_settings(current_user.id)
        return render_template('privacy_settings.html', settings=settings)
        
    except Exception as e:
        current_app.logger.error(f'Error loading privacy settings: {str(e)}', exc_info=True)
        flash('Error loading privacy settings', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/privacy-settings', methods=['POST'])
@login_required
def update_privacy():
    """Update user's privacy settings."""
    try:
        settings = {
            'auto_share_anonymous': 'auto_share_anonymous' in request.form,
            'allow_public_search': 'allow_public_search' in request.form,
            'show_in_community': 'show_in_community' in request.form,
            'default_privacy': 'default_privacy' in request.form
        }
        
        success = update_privacy_settings(current_user.id, settings)
        
        if success:
            flash('Privacy settings updated successfully!', 'success')
        else:
            flash('Error updating privacy settings', 'danger')
            
        return redirect(url_for('main.privacy_settings'))
        
    except Exception as e:
        current_app.logger.error(f'Error updating privacy settings: {str(e)}', exc_info=True)
        flash('Error updating privacy settings', 'danger')
        return redirect(url_for('main.privacy_settings'))

@main_bp.route('/api/community/entries')
@login_required
def api_community_entries():
    """API endpoint for community entries."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        entries = get_anonymous_public_entries(limit=per_page, offset=(page-1)*per_page)
        return jsonify({'success': True, 'entries': entries})
        
    except Exception as e:
        current_app.logger.error(f'Error getting community entries: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load entries'}), 500

@main_bp.route('/api/community/stats')
@login_required
def api_community_stats():
    """API endpoint for community statistics."""
    try:
        stats = get_community_stats()
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        current_app.logger.error(f'Error getting community stats: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load stats'}), 500

@main_bp.route('/api/community/trending')
@login_required
def api_trending_topics():
    """API endpoint for trending topics."""
    try:
        limit = request.args.get('limit', 10, type=int)
        topics = get_trending_topics(limit)
        return jsonify({'success': True, 'topics': topics})
        
    except Exception as e:
        current_app.logger.error(f'Error getting trending topics: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load topics'}), 500

@main_bp.route('/api/inspiration')
@login_required
def api_inspiration():
    """API endpoint for writing inspiration prompts."""
    try:
        prompts = get_inspiration_prompts()
        return jsonify({'success': True, 'prompts': prompts})
        
    except Exception as e:
        current_app.logger.error(f'Error getting inspiration prompts: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load prompts'}), 500

# Security Features Routes
@main_bp.route('/security')
@login_required
def security_settings():
    """Display security settings page."""
    try:
        settings = get_security_settings(current_user.id)
        return render_template('security_settings.html', settings=settings)
        
    except Exception as e:
        current_app.logger.error(f'Error loading security settings: {str(e)}', exc_info=True)
        flash('Error loading security settings', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/security/2fa/setup')
@login_required
def setup_2fa_page():
    """Setup 2FA page."""
    try:
        result = setup_2fa(current_user.id)
        
        if result['success']:
            return render_template('2fa_setup.html', 
                                 secret=result['secret'],
                                 qr_code=result['qr_code'],
                                 manual_key=result['manual_entry_key'])
        else:
            flash(result['error'], 'danger')
            return redirect(url_for('main.security_settings'))
        
    except Exception as e:
        current_app.logger.error(f'Error setting up 2FA: {str(e)}', exc_info=True)
        flash('Error setting up 2FA', 'danger')
        return redirect(url_for('main.security_settings'))

@main_bp.route('/security/2fa/verify', methods=['POST'])
@login_required
def verify_2fa():
    """Verify 2FA setup."""
    try:
        token = request.form.get('token', '').strip()
        
        if not token:
            flash('Token is required', 'danger')
            return redirect(url_for('main.setup_2fa_page'))
        
        result = verify_2fa_setup(current_user.id, token)
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('main.security_settings'))
        else:
            flash(result['error'], 'danger')
            return redirect(url_for('main.setup_2fa_page'))
        
    except Exception as e:
        current_app.logger.error(f'Error verifying 2FA: {str(e)}', exc_info=True)
        flash('Error verifying 2FA', 'danger')
        return redirect(url_for('main.setup_2fa_page'))

@main_bp.route('/security/2fa/disable', methods=['POST'])
@login_required
def disable_2fa_route():
    """Disable 2FA."""
    try:
        password = request.form.get('password', '')
        
        if not password:
            flash('Password is required', 'danger')
            return redirect(url_for('main.security_settings'))
        
        result = disable_2fa(current_user.id, password)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['error'], 'danger')
            
        return redirect(url_for('main.security_settings'))
        
    except Exception as e:
        current_app.logger.error(f'Error disabling 2FA: {str(e)}', exc_info=True)
        flash('Error disabling 2FA', 'danger')
        return redirect(url_for('main.security_settings'))

@main_bp.route('/security/backup')
@login_required
def create_backup():
    """Create encrypted backup of user data."""
    try:
        # Get user's encryption key (or generate from password)
        user = User.query.get(current_user.id)
        if user.encryption_key:
            encryption_key = user.encryption_key.encode()
        else:
            # Generate from user password hash (simplified)
            encryption_key = generate_encryption_key(user.password_hash[:32])
        
        result = backup_user_data(current_user.id, encryption_key)
        
        if result['success']:
            # Return file download
            from flask import Response
            backup_data = result['backup_data']
            filename = result['filename']
            
            response = Response(backup_data, mimetype='application/octet-stream')
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        else:
            flash(result['error'], 'danger')
            return redirect(url_for('main.security_settings'))
        
    except Exception as e:
        current_app.logger.error(f'Error creating backup: {str(e)}', exc_info=True)
        flash('Error creating backup', 'danger')
        return redirect(url_for('main.security_settings'))

@main_bp.route('/security/restore', methods=['POST'])
@login_required
def restore_backup():
    """Restore user data from backup."""
    try:
        if 'backup_file' not in request.files:
            flash('No backup file selected', 'danger')
            return redirect(url_for('main.security_settings'))
        
        backup_file = request.files['backup_file']
        if backup_file.filename == '':
            flash('No backup file selected', 'danger')
            return redirect(url_for('main.security_settings'))
        
        backup_data = backup_file.read().decode('utf-8')
        
        # Get user's encryption key
        user = User.query.get(current_user.id)
        if user.encryption_key:
            encryption_key = user.encryption_key.encode()
        else:
            encryption_key = generate_encryption_key(user.password_hash[:32])
        
        result = restore_user_data(backup_data, encryption_key, current_user.id)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['error'], 'danger')
            
        return redirect(url_for('main.security_settings'))
        
    except Exception as e:
        current_app.logger.error(f'Error restoring backup: {str(e)}', exc_info=True)
        flash('Error restoring backup', 'danger')
        return redirect(url_for('main.security_settings'))

@main_bp.route('/security/settings', methods=['POST'])
@login_required
def update_security():
    """Update security settings."""
    try:
        settings = {
            'encryption_enabled': 'encryption_enabled' in request.form
        }
        
        result = update_security_settings(current_user.id, settings)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['error'], 'danger')
            
        return redirect(url_for('main.security_settings'))
        
    except Exception as e:
        current_app.logger.error(f'Error updating security settings: {str(e)}', exc_info=True)
        flash('Error updating security settings', 'danger')
        return redirect(url_for('main.security_settings'))

@main_bp.route('/api/security/settings')
@login_required
def api_security_settings():
    """API endpoint for security settings."""
    try:
        settings = get_security_settings(current_user.id)
        return jsonify({'success': True, 'settings': settings})
        
    except Exception as e:
        current_app.logger.error(f'Error getting security settings: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load settings'}), 500

# Internationalization Routes
@main_bp.route('/language')
@login_required
def language_settings():
    """Display language settings page."""
    try:
        current_lang = get_current_language()
        supported_languages = get_supported_languages()
        user_timezone = getattr(current_user, 'timezone', 'UTC')
        
        return render_template('language_settings.html', 
                             current_language=current_lang,
                             supported_languages=supported_languages,
                             user_timezone=user_timezone)
        
    except Exception as e:
        current_app.logger.error(f'Error loading language settings: {str(e)}', exc_info=True)
        flash('Error loading language settings', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/language/set', methods=['POST'])
@login_required
def set_user_language():
    """Set user language preference."""
    try:
        language = request.form.get('language', 'en')
        timezone = request.form.get('timezone', 'UTC')
        
        # Validate language
        supported_languages = get_supported_languages()
        if language not in supported_languages:
            flash('Invalid language selection', 'danger')
            return redirect(url_for('main.language_settings'))
        
        # Set language
        success = set_language(language)
        
        # Update user timezone
        if success:
            current_user.timezone = timezone
            db.session.commit()
            flash('Language settings updated successfully!', 'success')
        else:
            flash('Error updating language settings', 'danger')
            
        return redirect(url_for('main.language_settings'))
        
    except Exception as e:
        current_app.logger.error(f'Error setting language: {str(e)}', exc_info=True)
        flash('Error updating language settings', 'danger')
        return redirect(url_for('main.language_settings'))

@main_bp.route('/api/language/translate')
@login_required
def api_translate():
    """API endpoint for translation."""
    try:
        key = request.args.get('key')
        language = request.args.get('language', get_current_language())
        
        if not key:
            return jsonify({'success': False, 'error': 'Translation key required'}), 400
        
        translation = translate(key, language)
        return jsonify({'success': True, 'translation': translation})
        
    except Exception as e:
        current_app.logger.error(f'Error translating: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Translation failed'}), 500

@main_bp.route('/api/language/info')
@login_required
def api_language_info():
    """API endpoint for language information."""
    try:
        current_lang = get_current_language()
        supported_languages = get_supported_languages()
        direction = get_language_direction(current_lang)
        
        return jsonify({
            'success': True,
            'current_language': current_lang,
            'supported_languages': supported_languages,
            'direction': direction
        })
        
    except Exception as e:
        current_app.logger.error(f'Error getting language info: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load language info'}), 500

# Add context processor for templates
@main_bp.app_context_processor
def inject_i18n():
    """Inject i18n functions into template context."""
    return {
        'translate': translate,
        'get_current_language': get_current_language,
        'get_language_direction': get_language_direction,
        'format_date': format_date,
        'format_number': format_number,
        'get_supported_languages': get_supported_languages
    }

# Cookie Consent Routes
@main_bp.route('/cookie-consent')
def cookie_consent():
    """Display cookie consent page."""
    try:
        return render_template('cookie_consent.html', 
                             categories=CookieConsent.CATEGORIES,
                             current_preferences=CookieConsent.get_preferences(),
                             has_consent=CookieConsent.has_consent())
    except Exception as e:
        current_app.logger.error(f'Error loading cookie consent: {str(e)}', exc_info=True)
        return redirect(url_for('main.dashboard'))

@main_bp.route('/cookie-consent/save', methods=['POST'])
@csrf.exempt  # Exempt from CSRF protection for cookie consent
def save_cookie_consent():
    """Save cookie consent preferences."""
    try:
        preferences = {
            'necessary': True,  # Always required
            'analytics': request.form.get('analytics') == 'on',
            'marketing': request.form.get('marketing') == 'on',
            'personalization': request.form.get('personalization') == 'on'
        }
        
        CookieConsent.set_consent(preferences)
        
        # Redirect back to where they came from
        next_page = request.form.get('next', url_for('main.dashboard'))
        return redirect(next_page)
        
    except Exception as e:
        current_app.logger.error(f'Error saving cookie consent: {str(e)}', exc_info=True)
        flash('Error saving cookie preferences', 'danger')
        return redirect(url_for('main.cookie_consent'))

@main_bp.route('/cookie-consent/update', methods=['POST'])
@login_required
def update_cookie_consent():
    """Update existing cookie consent preferences."""
    try:
        preferences = {
            'necessary': True,  # Always required
            'analytics': request.form.get('analytics') == 'on',
            'marketing': request.form.get('marketing') == 'on',
            'personalization': request.form.get('personalization') == 'on'
        }
        
        if CookieConsent.update_preferences(preferences):
            flash('Cookie preferences updated successfully', 'success')
        else:
            flash('No consent found to update', 'warning')
            
        return redirect(url_for('main.privacy_settings'))
        
    except Exception as e:
        current_app.logger.error(f'Error updating cookie consent: {str(e)}', exc_info=True)
        flash('Error updating cookie preferences', 'danger')
        return redirect(url_for('main.privacy_settings'))

@main_bp.route('/cookie-consent/withdraw', methods=['POST'])
@login_required
def withdraw_cookie_consent():
    """Withdraw cookie consent (GDPR right)."""
    try:
        CookieConsent.withdraw_consent()
        flash('Cookie consent withdrawn. Some features may be limited.', 'info')
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        current_app.logger.error(f'Error withdrawing cookie consent: {str(e)}', exc_info=True)
        flash('Error withdrawing consent', 'danger')
        return redirect(url_for('main.privacy_settings'))

@main_bp.route('/api/cookie-consent')
def api_cookie_consent():
    """API endpoint for cookie consent status."""
    try:
        return jsonify({
            'success': True,
            'has_consent': CookieConsent.has_consent(),
            'preferences': CookieConsent.get_preferences(),
            'consent_date': CookieConsent.get_consent_date(),
            'categories': CookieConsent.CATEGORIES
        })
    except Exception as e:
        current_app.logger.error(f'Error getting cookie consent: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to get consent status'}), 500

# Add cookie consent to template context
@main_bp.app_context_processor
def inject_cookie_consent():
    """Inject cookie consent data into template context."""
    return {
        'cookie_consent': CookieConsent,
        'can_use_analytics': CookieConsent.can_use_analytics(),
        'can_use_marketing': CookieConsent.can_use_marketing(),
        'can_use_personalization': CookieConsent.can_use_personalization()
    }

@main_bp.route('/api/community/like/<int:entry_id>', methods=['POST'])
@login_required
def api_community_like(entry_id):
    """API endpoint for liking community entries."""
    try:
        success = like_public_entry(current_user.id, entry_id)
        if success:
            return jsonify({'success': True, 'message': 'Entry liked successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to like entry'}), 400
    except Exception as e:
        current_app.logger.error(f'Error liking entry {entry_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Server error'}), 500

@main_bp.route('/api/community/report/<int:entry_id>', methods=['POST'])
@login_required
def api_community_report(entry_id):
    """API endpoint for reporting community entries."""
    try:
        success = report_public_entry(current_user.id, entry_id)
        if success:
            return jsonify({'success': True, 'message': 'Entry reported successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to report entry'}), 400
    except Exception as e:
        current_app.logger.error(f'Error reporting entry {entry_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Server error'}), 500
