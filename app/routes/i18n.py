from flask import Blueprint, render_template, request, jsonify, session, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.i18n import I18nService
from app.models.user import User
from app import db
import json
import logging

# Create blueprint
i18n_bp = Blueprint('i18n', __name__, url_prefix='/i18n')

# Initialize i18n service
i18n_service = I18nService()

@i18n_bp.route('/languages')
def languages():
    """Get available languages"""
    languages = i18n_service.get_available_languages()
    return jsonify(languages)

@i18n_bp.route('/set_language', methods=['POST'])
def set_language():
    """Set user language preference"""
    try:
        data = request.get_json()
        language_code = data.get('language_code')
        
        if not language_code:
            return jsonify({'error': 'Language code is required'}), 400
        
        # Validate language
        languages = i18n_service.get_available_languages()
        if language_code not in languages:
            return jsonify({'error': 'Unsupported language'}), 400
        
        # Set session language
        session['language'] = language_code
        
        # Save to database if user is logged in
        if current_user.is_authenticated:
            current_user.language_preference = language_code
            db.session.commit()
        
        return jsonify({'success': True, 'language': language_code})
        
    except Exception as e:
        logging.error(f"Error setting language: {str(e)}")
        return jsonify({'error': 'Failed to set language'}), 500

@i18n_bp.route('/translate')
def translate():
    """Get translation for a specific key"""
    try:
        key = request.args.get('key')
        language_code = request.args.get('language', session.get('language', 'en'))
        
        if not key:
            return jsonify({'error': 'Translation key is required'}), 400
        
        translation = i18n_service.translate(key, language_code)
        return jsonify({'translation': translation})
        
    except Exception as e:
        logging.error(f"Error getting translation: {str(e)}")
        return jsonify({'error': 'Failed to get translation'}), 500

@i18n_bp.route('/translate_bulk', methods=['POST'])
def translate_bulk():
    """Get multiple translations"""
    try:
        data = request.get_json()
        keys = data.get('keys', [])
        language_code = data.get('language', session.get('language', 'en'))
        
        if not keys:
            return jsonify({'error': 'Translation keys are required'}), 400
        
        translations = {}
        for key in keys:
            translations[key] = i18n_service.translate(key, language_code)
        
        return jsonify({'translations': translations})
        
    except Exception as e:
        logging.error(f"Error getting bulk translations: {str(e)}")
        return jsonify({'error': 'Failed to get translations'}), 500

@i18n_bp.route('/format_date')
def format_date():
    """Format date according to locale"""
    try:
        date_string = request.args.get('date')
        language_code = request.args.get('language', session.get('language', 'en'))
        format_type = request.args.get('format', 'medium')
        
        if not date_string:
            return jsonify({'error': 'Date string is required'}), 400
        
        formatted_date = i18n_service.format_date(date_string, language_code, format_type)
        return jsonify({'formatted_date': formatted_date})
        
    except Exception as e:
        logging.error(f"Error formatting date: {str(e)}")
        return jsonify({'error': 'Failed to format date'}), 500

@i18n_bp.route('/format_number')
def format_number():
    """Format number according to locale"""
    try:
        number = request.args.get('number')
        language_code = request.args.get('language', session.get('language', 'en'))
        format_type = request.args.get('format', 'decimal')
        
        if number is None:
            return jsonify({'error': 'Number is required'}), 400
        
        try:
            number = float(number)
        except ValueError:
            return jsonify({'error': 'Invalid number format'}), 400
        
        formatted_number = i18n_service.format_number(number, language_code, format_type)
        return jsonify({'formatted_number': formatted_number})
        
    except Exception as e:
        logging.error(f"Error formatting number: {str(e)}")
        return jsonify({'error': 'Failed to format number'}), 500

@i18n_bp.route('/format_currency')
def format_currency():
    """Format currency according to locale"""
    try:
        amount = request.args.get('amount')
        currency_code = request.args.get('currency', 'USD')
        language_code = request.args.get('language', session.get('language', 'en'))
        
        if amount is None:
            return jsonify({'error': 'Amount is required'}), 400
        
        try:
            amount = float(amount)
        except ValueError:
            return jsonify({'error': 'Invalid amount format'}), 400
        
        formatted_currency = i18n_service.format_currency(amount, currency_code, language_code)
        return jsonify({'formatted_currency': formatted_currency})
        
    except Exception as e:
        logging.error(f"Error formatting currency: {str(e)}")
        return jsonify({'error': 'Failed to format currency'}), 500

@i18n_bp.route('/detect_locale')
def detect_locale():
    """Detect user's preferred locale"""
    try:
        locale = i18n_service.detect_locale(request)
        return jsonify({'locale': locale})
        
    except Exception as e:
        logging.error(f"Error detecting locale: {str(e)}")
        return jsonify({'error': 'Failed to detect locale'}), 500

@i18n_bp.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    """Manage user language preferences"""
    if request.method == 'GET':
        # Get current preferences
        preferences = {
            'language': current_user.language_preference or session.get('language', 'en'),
            'timezone': current_user.timezone or 'UTC',
            'date_format': current_user.date_format or 'medium',
            'time_format': current_user.time_format or '24h',
            'currency': current_user.currency or 'USD'
        }
        
        available_languages = i18n_service.get_available_languages()
        
        return render_template('i18n/preferences.html', 
                             preferences=preferences,
                             available_languages=available_languages)
    
    else:  # POST
        try:
            data = request.get_json()
            
            # Update preferences
            current_user.language_preference = data.get('language', current_user.language_preference)
            current_user.timezone = data.get('timezone', current_user.timezone)
            current_user.date_format = data.get('date_format', current_user.date_format)
            current_user.time_format = data.get('time_format', current_user.time_format)
            current_user.currency = data.get('currency', current_user.currency)
            
            db.session.commit()
            
            # Update session
            session['language'] = current_user.language_preference
            
            return jsonify({'success': True, 'message': 'Preferences updated successfully!'})
            
        except Exception as e:
            logging.error(f"Error updating preferences: {str(e)}")
            return jsonify({'error': 'Failed to update preferences'}), 500

@i18n_bp.route('/js_translations')
def js_translations():
    """Get translations for JavaScript"""
    try:
        language_code = request.args.get('language', session.get('language', 'en'))
        
        # Get commonly used translations for JavaScript
        js_keys = [
            'common.save', 'common.cancel', 'common.delete', 'common.edit',
            'common.loading', 'common.error', 'common.success', 'common.warning',
            'entries.no_entries', 'analytics.no_data', 'goals.no_goals',
            'errors.try_again', 'success.saved', 'success.updated', 'success.deleted'
        ]
        
        translations = {}
        for key in js_keys:
            translations[key] = i18n_service.translate(key, language_code)
        
        return jsonify(translations)
        
    except Exception as e:
        logging.error(f"Error getting JS translations: {str(e)}")
        return jsonify({'error': 'Failed to get translations'}), 500

@i18n_bp.route('/language_switcher')
def language_switcher():
    """Render language switcher component"""
    try:
        current_language = session.get('language', 'en')
        available_languages = i18n_service.get_available_languages()
        
        return render_template('i18n/language_switcher.html',
                             current_language=current_language,
                             available_languages=available_languages)
        
    except Exception as e:
        logging.error(f"Error rendering language switcher: {str(e)}")
        return jsonify({'error': 'Failed to render language switcher'}), 500

@i18n_bp.route('/export_translations')
@login_required
def export_translations():
    """Export all translations for a language"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        language_code = request.args.get('language', 'en')
        
        # Load all translations for the language
        translations = i18n_service.load_translations(language_code)
        
        return jsonify(translations)
        
    except Exception as e:
        logging.error(f"Error exporting translations: {str(e)}")
        return jsonify({'error': 'Failed to export translations'}), 500

@i18n_bp.route('/health')
def health_check():
    """Health check for i18n service"""
    try:
        # Test basic functionality
        test_translation = i18n_service.translate('common.app_name', 'en')
        available_languages = i18n_service.get_available_languages()
        
        return jsonify({
            'status': 'healthy',
            'test_translation': test_translation,
            'available_languages_count': len(available_languages),
            'current_language': session.get('language', 'en')
        })
        
    except Exception as e:
        logging.error(f"I18n health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
