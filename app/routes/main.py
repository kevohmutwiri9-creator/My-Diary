from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, send_file, abort, session
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFError
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
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
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
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
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
@login_required
def preview_markdown():
    """Preview markdown content as HTML."""
    try:
        content = request.form.get('content', '')
        if not content:
            return jsonify({'html': ''})

        html = markdown_to_html(content)
        return jsonify({'html': html})
    except CSRFError:
        # Handle CSRF error gracefully for AJAX requests
        return jsonify({'error': 'CSRF token missing or invalid', 'html': ''}), 400

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
        
    except CSRFError:
        return jsonify({'success': False, 'error': 'CSRF token missing or invalid'}), 400
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
        
    except CSRFError:
        # Handle CSRF error gracefully - redirect back with message
        flash('Security token expired. Please try again.', 'warning')
        return redirect(request.referrer or url_for('main.dashboard'))
        
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

@main_bp.route('/theme/set', methods=['POST'])
@login_required
def set_theme():
    """Set user theme preference"""
    try:
        theme = request.json.get('theme', 'system')
        
        # Validate theme
        valid_themes = ['system', 'light', 'dark', 'high-contrast', 'ocean-blue', 'forest-green']
        if theme not in valid_themes:
            return jsonify({'success': False, 'message': 'Invalid theme'}), 400
        
        # Update user preference
        current_user.theme_preference = theme
        db.session.commit()
        
        return jsonify({'success': True, 'theme': theme})
        
    except Exception as e:
        current_app.logger.error(f'Error setting theme: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Server error'}), 500

@main_bp.route('/search')
@login_required
def search_entries():
    """Search diary entries with filters"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Filter options
    mood_filter = request.args.get('mood', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    tags_filter = request.args.get('tags', '').strip()
    
    try:
        # Base query
        entries_query = Entry.query.filter_by(user_id=current_user.id)
        
        # Apply text search
        if query:
            search_filter = db.or_(
                Entry.title.contains(query),
                Entry.content.contains(query)
            )
            entries_query = entries_query.filter(search_filter)
        
        # Apply mood filter
        if mood_filter:
            entries_query = entries_query.filter(Entry.mood == mood_filter)
        
        # Apply date filters
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                entries_query = entries_query.filter(Entry.created_at >= date_from_obj)
            except ValueError:
                pass  # Invalid date format, ignore
        
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                # Add one day to include the end date
                date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
                entries_query = entries_query.filter(Entry.created_at <= date_to_obj)
            except ValueError:
                pass  # Invalid date format, ignore
        
        # Apply tags filter
        if tags_filter:
            tag_names = [tag.strip() for tag in tags_filter.split(',') if tag.strip()]
            for tag_name in tag_names:
                entries_query = entries_query.filter(Entry.tags.any(Tag.name.contains(tag_name)))
        
        # Order by latest first
        entries_query = entries_query.order_by(Entry.created_at.desc())
        
        # Paginate
        pagination = entries_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get available moods for filter dropdown
        available_moods = db.session.query(Entry.mood).filter(
            Entry.user_id == current_user.id,
            Entry.mood.isnot(None)
        ).distinct().all()
        available_moods = [mood[0] for mood in available_moods if mood[0]]
        
        return render_template('search.html',
                             entries=pagination.items,
                             pagination=pagination,
                             query=query,
                             mood_filter=mood_filter,
                             date_from=date_from,
                             date_to=date_to,
                             tags_filter=tags_filter,
                             available_moods=available_moods,
                             total_results=pagination.total)
        
    except Exception as e:
        current_app.logger.error(f'Error searching entries: {str(e)}', exc_info=True)
        flash('Search failed. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard with writing statistics and insights"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, extract
        
        # Basic stats
        total_entries = Entry.query.filter_by(user_id=current_user.id).count()
        total_words = db.session.query(func.sum(func.length(Entry.content))).filter_by(user_id=current_user.id).scalar() or 0
        avg_words_per_entry = total_words // total_entries if total_entries > 0 else 0
        
        # This month's entries
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.created_at >= current_month_start
        ).count()
        
        # Writing streak
        entries = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.created_at.desc()).limit(30).all()
        current_streak = calculate_writing_streak(entries)
        
        # Mood analysis
        mood_data = db.session.query(
            Entry.mood,
            func.count(Entry.id).label('count')
        ).filter(
            Entry.user_id == current_user.id,
            Entry.mood.isnot(None)
        ).group_by(Entry.mood).all()
        
        # Daily writing pattern (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_data = db.session.query(
            func.date(Entry.created_at).label('date'),
            func.count(Entry.id).label('count')
        ).filter(
            Entry.user_id == current_user.id,
            Entry.created_at >= thirty_days_ago
        ).group_by(func.date(Entry.created_at)).all()
        
        # Most used tags
        tag_data = db.session.query(
            Tag.name,
            func.count(Entry.id).label('count')
        ).join(Entry.tags).filter(
            Entry.user_id == current_user.id
        ).group_by(Tag.name).order_by(func.count(Entry.id).desc()).limit(10).all()
        
        # Recent activity
        recent_entries = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.created_at.desc()).limit(5).all()
        
        # Monthly progress (last 6 months)
        monthly_data = []
        for i in range(6):
            month_start = (datetime.now().replace(day=1) - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            entries_count = Entry.query.filter(
                Entry.user_id == current_user.id,
                Entry.created_at >= month_start,
                Entry.created_at <= month_end
            ).count()
            
            monthly_data.append({
                'month': month_start.strftime('%b'),
                'count': entries_count
            })
        
        monthly_data.reverse()
        
        return render_template('analytics.html',
                             total_entries=total_entries,
                             total_words=total_words,
                             avg_words_per_entry=avg_words_per_entry,
                             this_month_entries=this_month_entries,
                             current_streak=current_streak,
                             mood_data=mood_data,
                             daily_data=daily_data,
                             tag_data=tag_data,
                             recent_entries=recent_entries,
                             monthly_data=monthly_data)
        
    except Exception as e:
        current_app.logger.error(f'Error loading analytics: {str(e)}', exc_info=True)
        flash('Analytics data unavailable. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

def calculate_writing_streak(entries):
    """Calculate current writing streak from entries"""
    if not entries:
        return 0
    
    streak = 0
    current_date = datetime.now().date()
    
    for entry in entries:
        entry_date = entry.created_at.date()
        
        if entry_date == current_date - timedelta(days=streak):
            streak += 1
        else:
            break
    
    return streak

@main_bp.route('/export')
@login_required
def export_entries():
    """Export diary entries in various formats"""
    export_format = request.args.get('format', 'json').lower()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    try:
        from datetime import datetime
        import json
        from io import BytesIO
        import zipfile
        
        # Base query
        entries_query = Entry.query.filter_by(user_id=current_user.id)
        
        # Apply date filters
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                entries_query = entries_query.filter(Entry.created_at >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
                entries_query = entries_query.filter(Entry.created_at <= date_to_obj)
            except ValueError:
                pass
        
        # Get entries
        entries = entries_query.order_by(Entry.created_at.desc()).all()
        
        if export_format == 'json':
            return export_as_json(entries)
        elif export_format == 'pdf':
            return export_as_pdf(entries)
        elif export_format == 'txt':
            return export_as_txt(entries)
        elif export_format == 'zip':
            return export_as_zip(entries)
        else:
            flash('Invalid export format', 'error')
            return redirect(url_for('main.dashboard'))
            
    except Exception as e:
        current_app.logger.error(f'Error exporting entries: {str(e)}', exc_info=True)
        flash('Export failed. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

def export_as_json(entries):
    """Export entries as JSON"""
    import json
    from datetime import datetime
    
    export_data = {
        'export_date': datetime.utcnow().isoformat(),
        'user': {
            'username': current_user.username,
            'email': current_user.email
        },
        'total_entries': len(entries),
        'entries': []
    }
    
    for entry in entries:
        entry_data = {
            'id': entry.id,
            'title': entry.title,
            'content': entry.content,
            'mood': entry.mood,
            'created_at': entry.created_at.isoformat(),
            'updated_at': entry.updated_at.isoformat() if entry.updated_at else None,
            'tags': [tag.name for tag in entry.tags]
        }
        export_data['entries'].append(entry_data)
    
    # Create JSON response
    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
    
    response = current_app.response_class(
        json_str,
        mimetype='application/json',
        direct_passthrough=True
    )
    
    filename = f"diary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    response.headers.set('Content-Disposition', f'attachment; filename={filename}')
    
    return response

def export_as_txt(entries):
    """Export entries as plain text"""
    from datetime import datetime
    
    content_lines = []
    content_lines.append(f"My Diary Export")
    content_lines.append(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    content_lines.append(f"User: {current_user.username} ({current_user.email})")
    content_lines.append(f"Total Entries: {len(entries)}")
    content_lines.append("=" * 50)
    content_lines.append("")
    
    for entry in entries:
        content_lines.append(f"Title: {entry.title or 'Untitled'}")
        content_lines.append(f"Date: {entry.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if entry.mood:
            content_lines.append(f"Mood: {entry.mood}")
        if entry.tags:
            content_lines.append(f"Tags: {', '.join([tag.name for tag in entry.tags])}")
        content_lines.append("-" * 30)
        content_lines.append(entry.content)
        content_lines.append("")
        content_lines.append("=" * 50)
        content_lines.append("")
    
    content = "\n".join(content_lines)
    
    response = current_app.response_class(
        content,
        mimetype='text/plain',
        direct_passthrough=True
    )
    
    filename = f"diary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    response.headers.set('Content-Disposition', f'attachment; filename={filename}')
    
    return response

def export_as_pdf(entries):
    """Export entries as PDF"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.colors import black, blue
        from datetime import datetime
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            textColor=black
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=6,
            textColor=blue
        )
        
        content_style = ParagraphStyle(
            'CustomContent',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=12,
            leading=14
        )
        
        story = []
        
        # Header
        story.append(Paragraph("My Diary Export", title_style))
        story.append(Paragraph(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", content_style))
        story.append(Paragraph(f"User: {current_user.username}", content_style))
        story.append(Paragraph(f"Total Entries: {len(entries)}", content_style))
        story.append(Spacer(1, 0.2*inch))
        
        for entry in entries:
            story.append(PageBreak())
            story.append(Paragraph(entry.title or 'Untitled', title_style))
            story.append(Paragraph(f"Date: {entry.created_at.strftime('%Y-%m-%d %H:%M:%S')}", heading_style))
            
            if entry.mood:
                story.append(Paragraph(f"Mood: {entry.mood}", heading_style))
            
            if entry.tags:
                tags_str = ', '.join([tag.name for tag in entry.tags])
                story.append(Paragraph(f"Tags: {tags_str}", heading_style))
            
            story.append(Spacer(1, 0.1*inch))
            
            # Clean content for PDF
            content = entry.content.replace('\n', '<br/>')
            story.append(Paragraph(content, content_style))
        
        doc.build(story)
        
        buffer.seek(0)
        
        response = current_app.response_class(
            buffer.getvalue(),
            mimetype='application/pdf',
            direct_passthrough=True
        )
        
        filename = f"diary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response.headers.set('Content-Disposition', f'attachment; filename={filename}')
        
        return response
        
    except ImportError:
        flash('PDF export not available. Please install reportlab library.', 'error')
        return redirect(url_for('main.dashboard'))

def export_as_zip(entries):
    """Export entries as ZIP with multiple formats"""
    import zipfile
    from io import BytesIO
    from datetime import datetime
    
    buffer = BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add JSON export
        json_response = export_as_json(entries)
        zip_file.writestr(f"diary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 
                          json_response.get_data())
        
        # Add TXT export
        txt_response = export_as_txt(entries)
        zip_file.writestr(f"diary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 
                          txt_response.get_data())
        
        # Try to add PDF export
        try:
            pdf_response = export_as_pdf(entries)
            zip_file.writestr(f"diary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", 
                              pdf_response.get_data())
        except:
            pass  # Skip PDF if not available
    
    buffer.seek(0)
    
    response = current_app.response_class(
        buffer.getvalue(),
        mimetype='application/zip',
        direct_passthrough=True
    )
    
    filename = f"diary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    response.headers.set('Content-Disposition', f'attachment; filename={filename}')
    
    return response

@main_bp.route('/goals')
@login_required
def goals():
    """Goal tracking and writing streaks management"""
    try:
        from datetime import datetime, timedelta
        
        # Get current goals
        daily_goal = current_user.daily_goal or 1
        weekly_goal = current_user.weekly_goal or 7
        
        # Calculate current progress
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        # Daily progress
        today_entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            func.date(Entry.created_at) == today
        ).count()
        
        # Weekly progress
        week_entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            func.date(Entry.created_at) >= week_start
        ).count()
        
        # Current streak (already implemented)
        entries = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.created_at.desc()).limit(30).all()
        current_streak = calculate_writing_streak(entries)
        
        # Longest streak
        all_entries = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.created_at.asc()).all()
        longest_streak = calculate_longest_streak(all_entries)
        
        # Goal achievement history
        goal_history = get_goal_achievement_history(current_user.id)
        
        # Recent achievements
        recent_achievements = check_recent_achievements(current_user, today_entries, week_entries, current_streak)
        
        return render_template('goals.html',
                             daily_goal=daily_goal,
                             weekly_goal=weekly_goal,
                             today_entries=today_entries,
                             week_entries=week_entries,
                             current_streak=current_streak,
                             longest_streak=longest_streak,
                             goal_history=goal_history,
                             recent_achievements=recent_achievements)
        
    except Exception as e:
        current_app.logger.error(f'Error loading goals: {str(e)}', exc_info=True)
        flash('Goals data unavailable. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/goals/update', methods=['POST'])
@login_required
def update_goals_settings():
    """Update user goals"""
    try:
        daily_goal = request.form.get('daily_goal', type=int)
        weekly_goal = request.form.get('weekly_goal', type=int)
        
        # Validate goals
        if daily_goal and (daily_goal < 1 or daily_goal > 10):
            flash('Daily goal must be between 1 and 10 entries', 'error')
            return redirect(url_for('main.goals'))
        
        if weekly_goal and (weekly_goal < 1 or weekly_goal > 50):
            flash('Weekly goal must be between 1 and 50 entries', 'error')
            return redirect(url_for('main.goals'))
        
        # Update user goals
        current_user.daily_goal = daily_goal or 1
        current_user.weekly_goal = weekly_goal or 7
        db.session.commit()
        
        flash('Goals updated successfully!', 'success')
        return redirect(url_for('main.goals'))
        
    except Exception as e:
        current_app.logger.error(f'Error updating goals: {str(e)}', exc_info=True)
        flash('Failed to update goals. Please try again.', 'error')
        return redirect(url_for('main.goals'))

def calculate_longest_streak(entries):
    """Calculate the longest writing streak from all entries"""
    if not entries:
        return 0
    
    longest_streak = 0
    current_streak = 1
    
    for i in range(1, len(entries)):
        current_date = entries[i].created_at.date()
        prev_date = entries[i-1].created_at.date()
        
        if current_date == prev_date + timedelta(days=1):
            current_streak += 1
        elif current_date != prev_date:
            current_streak = 1
        
        longest_streak = max(longest_streak, current_streak)
    
    return max(longest_streak, 1)

def get_goal_achievement_history(user_id):
    """Get goal achievement history for the last 30 days"""
    from datetime import datetime, timedelta
    
    history = []
    today = datetime.now().date()
    
    for i in range(30):
        date = today - timedelta(days=i)
        
        # Daily entries on this date
        daily_entries = Entry.query.filter(
            Entry.user_id == user_id,
            func.date(Entry.created_at) == date
        ).count()
        
        # Week entries for this date's week
        week_start = date - timedelta(days=date.weekday())
        week_entries = Entry.query.filter(
            Entry.user_id == user_id,
            func.date(Entry.created_at) >= week_start,
            func.date(Entry.created_at) <= date
        ).count()
        
        history.append({
            'date': date,
            'daily_entries': daily_entries,
            'week_entries': week_entries
        })
    
    return history

def check_recent_achievements(user, today_entries, week_entries, current_streak):
    """Check for recent achievements and milestones"""
    achievements = []
    
    # Daily goal achievements
    if today_entries >= user.daily_goal:
        if today_entries == user.daily_goal:
            achievements.append({
                'type': 'daily_goal',
                'title': f'Daily Goal Achieved!',
                'description': f'You wrote {today_entries} entries today',
                'icon': 'bi-calendar-check',
                'color': 'success'
            })
        elif today_entries > user.daily_goal * 2:
            achievements.append({
                'type': 'daily_exceeded',
                'title': f'Amazing Progress!',
                'description': f'You wrote {today_entries} entries today - double your goal!',
                'icon': 'bi-trophy',
                'color': 'warning'
            })
    
    # Weekly goal achievements
    if week_entries >= user.weekly_goal:
        achievements.append({
            'type': 'weekly_goal',
            'title': f'Weekly Goal Achieved!',
            'description': f'You wrote {week_entries} entries this week',
            'icon': 'bi-calendar-week',
            'color': 'info'
        })
    
    # Streak achievements
    if current_streak == 7:
        achievements.append({
            'type': 'streak_week',
            'title': 'One Week Streak!',
            'description': 'You have written for 7 consecutive days',
            'icon': 'bi-fire',
            'color': 'danger'
        })
    elif current_streak == 30:
        achievements.append({
            'type': 'streak_month',
            'title': 'One Month Streak!',
            'description': 'You have written for 30 consecutive days',
            'icon': 'bi-star',
            'color': 'primary'
        })
    elif current_streak > 0 and current_streak % 10 == 0:
        achievements.append({
            'type': 'streak_milestone',
            'title': f'{current_streak} Day Streak!',
            'description': f'You have written for {current_streak} consecutive days',
            'icon': 'bi-award',
            'color': 'success'
        })
    
    return achievements

@main_bp.route('/mood-insights')
@login_required
def mood_insights():
    """Mood tracking with emotional insights and patterns"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Get mood distribution
        mood_data = db.session.query(
            Entry.mood,
            func.count(Entry.id).label('count')
        ).filter(
            Entry.user_id == current_user.id,
            Entry.mood.isnot(None)
        ).group_by(Entry.mood).all()
        
        # Mood trends over time (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        mood_trends = db.session.query(
            func.date(Entry.created_at).label('date'),
            Entry.mood,
            func.count(Entry.id).label('count')
        ).filter(
            Entry.user_id == current_user.id,
            Entry.created_at >= thirty_days_ago,
            Entry.mood.isnot(None)
        ).group_by(func.date(Entry.created_at), Entry.mood).all()
        
        # Organize mood trends by date
        mood_by_date = {}
        for trend in mood_trends:
            date_str = trend.date.strftime('%Y-%m-%d')
            if date_str not in mood_by_date:
                mood_by_date[date_str] = {}
            mood_by_date[date_str][trend.mood] = trend.count
        
        # Mood patterns by day of week
        mood_by_weekday = db.session.query(
            extract('dow', Entry.created_at).label('weekday'),
            Entry.mood,
            func.count(Entry.id).label('count')
        ).filter(
            Entry.user_id == current_user.id,
            Entry.mood.isnot(None)
        ).group_by(extract('dow', Entry.created_at), Entry.mood).all()
        
        # Organize by weekday
        weekday_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        mood_weekday_data = {i: {} for i in range(7)}
        for data in mood_by_weekday:
            weekday = int(data.weekday)
            mood_weekday_data[weekday][data.mood] = data.count
        
        # Recent mood entries
        recent_mood_entries = Entry.query.filter(
            Entry.user_id == current_user.id,
            Entry.mood.isnot(None)
        ).order_by(Entry.created_at.desc()).limit(10).all()
        
        # Mood insights and recommendations
        insights = generate_mood_insights(mood_data, mood_trends, mood_by_date)
        
        return render_template('mood_insights.html',
                             mood_data=mood_data,
                             mood_by_date=mood_by_date,
                             mood_weekday_data=mood_weekday_data,
                             weekday_names=weekday_names,
                             recent_mood_entries=recent_mood_entries,
                             insights=insights)
        
    except Exception as e:
        current_app.logger.error(f'Error loading mood insights: {str(e)}', exc_info=True)
        flash('Mood insights unavailable. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

def generate_mood_insights(mood_data, mood_trends, mood_by_date):
    """Generate personalized mood insights and recommendations"""
    insights = []
    
    # Most common mood
    if mood_data:
        most_common = max(mood_data, key=lambda x: x.count)
        insights.append({
            'type': 'pattern',
            'title': 'Your Most Common Mood',
            'description': f'You most often feel {most_common.mood.lower()} ({most_common.count} times)',
            'icon': 'bi-graph-up',
            'color': 'primary'
        })
    
    # Mood stability
    if len(mood_data) > 1:
        mood_counts = [mood.count for mood in mood_data]
        avg_count = sum(mood_counts) / len(mood_counts)
        variance = sum((count - avg_count) ** 2 for count in mood_counts) / len(mood_counts)
        
        if variance < avg_count * 0.5:
            insights.append({
                'type': 'stability',
                'title': 'Emotionally Balanced',
                'description': 'Your moods are quite balanced and stable',
                'icon': 'bi-balance-scale',
                'color': 'success'
            })
        else:
            insights.append({
                'type': 'variability',
                'title': 'Emotionally Dynamic',
                'description': 'You experience a wide range of emotions',
                'icon': 'bi-rainbow',
                'color': 'info'
            })
    
    # Recent mood trend
    if mood_by_date:
        recent_dates = sorted(mood_by_date.keys())[-7:]  # Last 7 days
        recent_moods = []
        for date in recent_dates:
            if mood_by_date[date]:
                most_common_mood = max(mood_by_date[date].items(), key=lambda x: x[1])[0]
                recent_moods.append(most_common_mood)
        
        if len(set(recent_moods)) == 1 and recent_moods:
            insights.append({
                'type': 'trend',
                'title': 'Consistent Mood Pattern',
                'description': f'You\'ve been feeling {recent_moods[0].lower()} consistently lately',
                'icon': 'bi-arrow-right-circle',
                'color': 'warning'
            })
    
    # Recommendations based on mood patterns
    positive_moods = ['happy', 'excited', 'calm']
    negative_moods = ['sad', 'anxious', 'angry']
    
    positive_count = sum(mood.count for mood in mood_data if mood.mood in positive_moods)
    negative_count = sum(mood.count for mood in mood_data if mood.mood in negative_moods)
    
    if negative_count > positive_count * 1.5:
        insights.append({
            'type': 'recommendation',
            'title': 'Self-Care Recommendation',
            'description': 'Consider focusing on activities that bring you joy and relaxation',
            'icon': 'bi-heart',
            'color': 'danger'
        })
    elif positive_count > negative_count * 1.5:
        insights.append({
            'type': 'positive',
            'title': 'Great Emotional Health',
            'description': 'You maintain a positive outlook on life',
            'icon': 'bi-sunshine',
            'color': 'success'
        })
    
    return insights

@main_bp.route('/backup')
@login_required
def backup_data():
    """Create backup of user data and settings"""
    try:
        from datetime import datetime
        import json
        from io import BytesIO
        import zipfile
        
        # Get all user data
        entries = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.created_at.desc()).all()
        
        # Create comprehensive backup data
        backup_data = {
            'backup_info': {
                'created_at': datetime.utcnow().isoformat(),
                'version': '1.0',
                'user_email': current_user.email,
                'user_username': current_user.username
            },
            'user_settings': {
                'theme_preference': getattr(current_user, 'theme_preference', 'system'),
                'daily_goal': getattr(current_user, 'daily_goal', 1),
                'weekly_goal': getattr(current_user, 'weekly_goal', 7),
                'created_at': current_user.created_at.isoformat()
            },
            'entries': [],
            'tags': [],
            'statistics': {
                'total_entries': len(entries),
                'total_words': sum(len(entry.content.split()) for entry in entries),
                'date_range': {
                    'first_entry': entries[-1].created_at.isoformat() if entries else None,
                    'last_entry': entries[0].created_at.isoformat() if entries else None
                }
            }
        }
        
        # Add entries with full data
        for entry in entries:
            entry_data = {
                'id': entry.id,
                'title': entry.title,
                'content': entry.content,
                'mood': entry.mood,
                'created_at': entry.created_at.isoformat(),
                'updated_at': entry.updated_at.isoformat() if entry.updated_at else None,
                'tags': [tag.name for tag in entry.tags]
            }
            backup_data['entries'].append(entry_data)
        
        # Get all tags used by user
        user_tags = set()
        for entry in entries:
            user_tags.update(tag.name for tag in entry.tags)
        
        backup_data['tags'] = sorted(list(user_tags))
        
        # Create ZIP file with multiple formats
        buffer = BytesIO()
        
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add JSON backup
            json_str = json.dumps(backup_data, indent=2, ensure_ascii=False)
            zip_file.writestr(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", json_str)
            
            # Add plain text export
            txt_content = generate_text_backup(backup_data)
            zip_file.writestr(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", txt_content)
            
            # Add CSV export for entries
            csv_content = generate_csv_backup(backup_data['entries'])
            zip_file.writestr(f"entries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", csv_content)
            
            # Add README file
            readme_content = generate_backup_readme()
            zip_file.writestr("README.txt", readme_content)
        
        buffer.seek(0)
        
        response = current_app.response_class(
            buffer.getvalue(),
            mimetype='application/zip',
            direct_passthrough=True
        )
        
        filename = f"my_diary_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        response.headers.set('Content-Disposition', f'attachment; filename={filename}')
        
        return response
        
    except Exception as e:
        current_app.logger.error(f'Error creating backup: {str(e)}', exc_info=True)
        flash('Backup failed. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/restore', methods=['GET', 'POST'])
@login_required
def restore_data():
    """Restore user data from backup"""
    if request.method == 'GET':
        return render_template('restore.html')
    
    try:
        if 'backup_file' not in request.files:
            flash('No backup file selected', 'error')
            return redirect(url_for('main.restore'))
        
        file = request.files['backup_file']
        if file.filename == '':
            flash('No backup file selected', 'error')
            return redirect(url_for('main.restore'))
        
        if not file.filename.endswith('.zip'):
            flash('Invalid backup file. Please select a ZIP backup file.', 'error')
            return redirect(url_for('main.restore'))
        
        # Read ZIP file
        import zipfile
        import json
        from io import BytesIO
        
        buffer = BytesIO()
        file.save(buffer)
        buffer.seek(0)
        
        with zipfile.ZipFile(buffer, 'r') as zip_file:
            # Find JSON backup file
            json_files = [f for f in zip_file.namelist() if f.endswith('.json')]
            if not json_files:
                flash('Invalid backup file format', 'error')
                return redirect(url_for('main.restore'))
            
            # Read backup data
            with zip_file.open(json_files[0]) as json_file:
                backup_data = json.load(json_file)
        
        # Validate backup data
        if not validate_backup_data(backup_data):
            flash('Invalid backup data format', 'error')
            return redirect(url_for('main.restore'))
        
        # Check if this is the correct user
        if backup_data['backup_info']['user_email'] != current_user.email:
            flash('This backup belongs to a different user account', 'error')
            return redirect(url_for('main.restore'))
        
        # Restore data
        restore_success = perform_restore(backup_data, current_user.id)
        
        if restore_success:
            flash('Data restored successfully! Your diary has been updated.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Restore completed with some warnings. Check your entries.', 'warning')
            return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        current_app.logger.error(f'Error restoring backup: {str(e)}', exc_info=True)
        flash('Restore failed. Please check your backup file and try again.', 'error')
        return redirect(url_for('main.restore'))

def generate_text_backup(backup_data):
    """Generate plain text backup"""
    lines = []
    lines.append("=" * 60)
    lines.append("MY DIARY BACKUP")
    lines.append("=" * 60)
    lines.append(f"Created: {backup_data['backup_info']['created_at']}")
    lines.append(f"User: {backup_data['backup_info']['user_username']} ({backup_data['backup_info']['user_email']})")
    lines.append(f"Total Entries: {backup_data['statistics']['total_entries']}")
    lines.append("")
    
    lines.append("USER SETTINGS")
    lines.append("-" * 30)
    settings = backup_data['user_settings']
    lines.append(f"Theme: {settings.get('theme_preference', 'system')}")
    lines.append(f"Daily Goal: {settings.get('daily_goal', 1)} entries")
    lines.append(f"Weekly Goal: {settings.get('weekly_goal', 7)} entries")
    lines.append("")
    
    lines.append("TAGS USED")
    lines.append("-" * 30)
    for tag in backup_data['tags']:
        lines.append(f"#{tag}")
    lines.append("")
    
    lines.append("ENTRIES")
    lines.append("=" * 60)
    
    for entry in backup_data['entries']:
        lines.append(f"Title: {entry['title'] or 'Untitled'}")
        lines.append(f"Date: {entry['created_at']}")
        if entry['mood']:
            lines.append(f"Mood: {entry['mood']}")
        if entry['tags']:
            lines.append(f"Tags: {', '.join(entry['tags'])}")
        lines.append("-" * 40)
        lines.append(entry['content'])
        lines.append("")
        lines.append("=" * 60)
        lines.append("")
    
    return "\n".join(lines)

def generate_csv_backup(entries):
    """Generate CSV backup of entries"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Title', 'Content', 'Mood', 'Created At', 'Updated At', 'Tags'])
    
    # Write entries
    for entry in entries:
        writer.writerow([
            entry['id'],
            entry['title'] or '',
            entry['content'],
            entry['mood'] or '',
            entry['created_at'],
            entry['updated_at'] or '',
            ', '.join(entry['tags'])
        ])
    
    return output.getvalue()

def generate_backup_readme():
    """Generate README file for backup"""
    content = """MY DIARY BACKUP README
==================

This backup contains your complete diary data and settings.

FILES INCLUDED:
- backup_YYYYMMDD_HHMMSS.json: Complete backup in JSON format
- backup_YYYYMMDD_HHMMSS.txt: Human-readable text backup
- entries_YYYYMMDD_HHMMSS.csv: Entries in CSV format
- README.txt: This file

BACKUP FORMAT:
The JSON backup contains:
- Backup information (creation date, version, user info)
- User settings (theme, goals, preferences)
- All entries with content, metadata, and tags
- Statistics and summary information

RESTORING:
To restore this backup, use the Restore feature in your diary application.
The backup can only be restored to the same user account it was created from.

IMPORTANT:
- Keep this backup file safe and secure
- It contains your personal thoughts and feelings
- Store it in a secure location
- Regular backups are recommended

Created with My Diary App
"""
    return content

def validate_backup_data(backup_data):
    """Validate backup data structure"""
    required_keys = ['backup_info', 'user_settings', 'entries', 'tags', 'statistics']
    
    for key in required_keys:
        if key not in backup_data:
            return False
    
    # Check backup info
    backup_info = backup_data['backup_info']
    if not all(k in backup_info for k in ['created_at', 'user_email', 'user_username']):
        return False
    
    # Check entries structure
    entries = backup_data['entries']
    for entry in entries:
        if not all(k in entry for k in ['id', 'title', 'content', 'created_at']):
            return False
    
    return True

def perform_restore(backup_data, user_id):
    """Perform the actual data restoration"""
    try:
        from app.models.tag import Tag
        from datetime import datetime
        
        # Restore user settings
        settings = backup_data['user_settings']
        user = User.query.get(user_id)
        
        if hasattr(user, 'theme_preference'):
            user.theme_preference = settings.get('theme_preference', 'system')
        if hasattr(user, 'daily_goal'):
            user.daily_goal = settings.get('daily_goal', 1)
        if hasattr(user, 'weekly_goal'):
            user.weekly_goal = settings.get('weekly_goal', 7)
        
        # Restore entries
        for entry_data in backup_data['entries']:
            # Check if entry already exists
            existing_entry = Entry.query.filter_by(id=entry_data['id'], user_id=user_id).first()
            
            if existing_entry:
                # Update existing entry
                existing_entry.title = entry_data['title']
                existing_entry.content = entry_data['content']
                existing_entry.mood = entry_data['mood']
                existing_entry.updated_at = datetime.utcnow()
            else:
                # Create new entry
                entry = Entry(
                    id=entry_data['id'],
                    user_id=user_id,
                    title=entry_data['title'],
                    content=entry_data['content'],
                    mood=entry_data['mood'],
                    created_at=datetime.fromisoformat(entry_data['created_at'])
                )
                db.session.add(entry)
            
            # Handle tags
            if entry_data['tags']:
                for tag_name in entry_data['tags']:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    
                    # Add tag to entry (this will be handled by the relationship)
        
        db.session.commit()
        return True
        
    except Exception as e:
        current_app.logger.error(f'Restore error: {str(e)}', exc_info=True)
        db.session.rollback()
        return False

@main_bp.route('/notifications')
@login_required
def notifications():
    """Notification and reminder management"""
    try:
        from datetime import datetime, timedelta
        
        # Get user notification preferences
        reminder_enabled = getattr(current_user, 'reminder_enabled', False)
        reminder_time = getattr(current_user, 'reminder_time', '09:00')
        reminder_days = getattr(current_user, 'reminder_days', '0,1,2,3,4')  # Mon-Fri default
        
        # Parse reminder days
        selected_days = [int(day.strip()) for day in reminder_days.split(',') if day.strip()]
        
        # Check if user wrote today
        today = datetime.now().date()
        today_entry = Entry.query.filter(
            Entry.user_id == current_user.id,
            func.date(Entry.created_at) == today
        ).first()
        
        # Recent notifications
        recent_notifications = []
        
        # Generate reminder notifications
        if reminder_enabled and not today_entry:
            current_time = datetime.now().time()
            reminder_hour, reminder_min = map(int, reminder_time.split(':'))
            reminder_time_obj = datetime.strptime(reminder_time, '%H:%M').time()
            
            # Check if it's past reminder time and user hasn't written today
            if datetime.now().time() > reminder_time_obj:
                current_weekday = datetime.now().weekday()
                if current_weekday in selected_days:
                    recent_notifications.append({
                        'type': 'reminder',
                        'title': 'Daily Journal Reminder',
                        'message': f'You haven\'t written today. Take a moment to reflect on your day!',
                        'time': datetime.now().strftime('%I:%M %p'),
                        'icon': 'bi-bell',
                        'color': 'warning',
                        'action_url': url_for('main.new_entry')
                    })
        
        # Achievement notifications
        entries = Entry.query.filter_by(user_id=current_user.id).order_by(Entry.created_at.desc()).limit(5).all()
        for entry in entries:
            if entry.created_at.date() == today:
                recent_notifications.append({
                    'type': 'achievement',
                    'title': 'Great Job!',
                    'message': f'You wrote "{entry.title or "an entry"}" today',
                    'time': entry.created_at.strftime('%I:%M %p'),
                    'icon': 'bi-trophy',
                    'color': 'success',
                    'action_url': url_for('main.view_entry', id=entry.id)
                })
                break
        
        # Goal progress notifications
        current_streak = calculate_writing_streak(entries)
        if current_streak >= 7:
            recent_notifications.append({
                'type': 'milestone',
                'title': f'{current_streak} Day Streak!',
                'message': 'Keep up the amazing work with your journaling habit!',
                'time': datetime.now().strftime('%I:%M %p'),
                'icon': 'bi-fire',
                'color': 'danger',
                'action_url': url_for('main.goals')
            })
        
        return render_template('notifications.html',
                             reminder_enabled=reminder_enabled,
                             reminder_time=reminder_time,
                             selected_days=selected_days,
                             today_entry=today_entry,
                             recent_notifications=recent_notifications)
        
    except Exception as e:
        current_app.logger.error(f'Error loading notifications: {str(e)}', exc_info=True)
        flash('Notifications unavailable. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/notifications/update', methods=['POST'])
@login_required
def update_notifications():
    """Update notification preferences"""
    try:
        reminder_enabled = request.form.get('reminder_enabled') == 'on'
        reminder_time = request.form.get('reminder_time', '09:00')
        reminder_days = request.form.getlist('reminder_days')
        
        # Validate reminder time
        try:
            datetime.strptime(reminder_time, '%H:%M')
        except ValueError:
            flash('Invalid reminder time format', 'error')
            return redirect(url_for('main.notifications'))
        
        # Update user preferences
        if hasattr(current_user, 'reminder_enabled'):
            current_user.reminder_enabled = reminder_enabled
        if hasattr(current_user, 'reminder_time'):
            current_user.reminder_time = reminder_time
        if hasattr(current_user, 'reminder_days'):
            current_user.reminder_days = ','.join(reminder_days)
        
        db.session.commit()
        
        flash('Notification preferences updated successfully!', 'success')
        return redirect(url_for('main.notifications'))
        
    except Exception as e:
        current_app.logger.error(f'Error updating notifications: {str(e)}', exc_info=True)
        flash('Failed to update preferences. Please try again.', 'error')
        return redirect(url_for('main.notifications'))

@main_bp.route('/api/notifications/check')
@login_required
def check_notifications():
    """API endpoint to check for new notifications"""
    try:
        from datetime import datetime
        
        notifications = []
        
        # Check if user wrote today
        today = datetime.now().date()
        today_entry = Entry.query.filter(
            Entry.user_id == current_user.id,
            func.date(Entry.created_at) == today
        ).first()
        
        # Check reminder settings
        reminder_enabled = getattr(current_user, 'reminder_enabled', False)
        reminder_time = getattr(current_user, 'reminder_time', '09:00')
        reminder_days = getattr(current_user, 'reminder_days', '0,1,2,3,4')
        
        if reminder_enabled and not today_entry:
            current_time = datetime.now().time()
            reminder_time_obj = datetime.strptime(reminder_time, '%H:%M').time()
            
            # Check if it's past reminder time
            if datetime.now().time() > reminder_time_obj:
                current_weekday = datetime.now().weekday()
                selected_days = [int(day.strip()) for day in reminder_days.split(',') if day.strip()]
                
                if current_weekday in selected_days:
                    notifications.append({
                        'type': 'reminder',
                        'title': 'Daily Journal Reminder',
                        'message': 'You haven\'t written today. Take a moment to reflect!',
                        'icon': 'bi-bell',
                        'color': 'warning',
                        'action_url': url_for('main.new_entry')
                    })
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'count': len(notifications)
        })
        
    except Exception as e:
        current_app.logger.error(f'Error checking notifications: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error checking notifications'}), 500
