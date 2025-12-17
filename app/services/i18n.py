"""
Internationalization (i18n) and Localization Services for My Diary App
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import request, session, current_app
from babel import Locale, dates, numbers
from babel.support import Translations
from babel.core import UnknownLocaleError
import logging

logger = logging.getLogger(__name__)


class I18nService:
    """Internationalization service"""
    
    def __init__(self):
        self.default_locale = 'en'
        # Full catalog; will be filtered by config in init_app
        self.catalog_locales = {
            'en': {'name': 'English', 'native_name': 'English', 'flag': '🇺🇸'},
            'es': {'name': 'Spanish', 'native_name': 'Español', 'flag': '🇪🇸'},
            'fr': {'name': 'French', 'native_name': 'Français', 'flag': '🇫🇷'},
            'de': {'name': 'German', 'native_name': 'Deutsch', 'flag': '🇩🇪'},
            'it': {'name': 'Italian', 'native_name': 'Italiano', 'flag': '🇮🇹'},
            'pt': {'name': 'Portuguese', 'native_name': 'Português', 'flag': '🇵🇹'},
            'ru': {'name': 'Russian', 'native_name': 'Русский', 'flag': '🇷🇺'},
            'zh': {'name': 'Chinese', 'native_name': '中文', 'flag': '🇨🇳'},
            'ja': {'name': 'Japanese', 'native_name': '日本語', 'flag': '🇯🇵'},
            'ko': {'name': 'Korean', 'native_name': '한국어', 'flag': '🇰🇷'},
            'ar': {'name': 'Arabic', 'native_name': 'العربية', 'flag': '🇸🇦'},
            'hi': {'name': 'Hindi', 'native_name': 'हिन्दी', 'flag': '🇮🇳'}
        }
        self.supported_locales = {'en': self.catalog_locales['en']}
        self.translations = {}
    
    def init_app(self, app):
        with app.app_context():
            configured_locales = app.config.get('I18N_LOCALES', 'en')
            if isinstance(configured_locales, str):
                configured_locales = [code.strip() for code in configured_locales.split(',') if code.strip()]
            # Filter to allowed locales; always keep English as a fallback
            self.supported_locales = {
                code: meta
                for code, meta in self.catalog_locales.items()
                if code in configured_locales or code == 'en'
            } or {'en': self.catalog_locales['en']}

        self.load_translations(app)
        app.jinja_env.globals['get_locale'] = self.get_locale
        app.jinja_env.globals['is_rtl'] = self.is_rtl
    
    def load_translations(self, app=None):
        """Load translation files"""
        try:
            root_path = getattr(app, 'root_path', None) or current_app.root_path
            translations_dir = os.path.join(root_path, 'translations')
            
            for locale_code in self.supported_locales:
                translation_file = os.path.join(translations_dir, f'{locale_code}.json')
                
                if os.path.exists(translation_file):
                    with open(translation_file, 'r', encoding='utf-8') as f:
                        self.translations[locale_code] = json.load(f)
                else:
                    # Fallback to empty translations without noisy warnings
                    self.translations[locale_code] = {}
                    logger.info(f"Translation file not found (using empty translations): {translation_file}")
            
            logger.info(f"Loaded translations for {len(self.translations)} locales")
            
        except Exception as e:
            logger.error(f"Error loading translations: {str(e)}")
    
    def get_locale(self) -> str:
        """Get current locale"""
        # Priority: session > user preference > browser > default
        if 'language' in session:
            return session['language']

        if 'locale' in session:
            return session['locale']
        
        # Check user preference if logged in
        if hasattr(request, 'current_user') and request.current_user.is_authenticated:
            user_locale = getattr(request.current_user, 'preferred_language', None)
            if user_locale and user_locale in self.supported_locales:
                return user_locale
        
        # Check browser language
        browser_lang = request.accept_languages.best_match(
            list(self.supported_locales.keys())
        )
        if browser_lang:
            return browser_lang
        
        return self.default_locale
    
    def set_locale(self, locale_code: str):
        """Set current locale"""
        if locale_code in self.supported_locales:
            session['language'] = locale_code
            session['locale'] = locale_code
            return True
        return False
    
    def translate(self, key: str, locale: str = None, **kwargs) -> str:
        """Translate a key"""
        if not locale:
            locale = self.get_locale()
        
        # Get translation
        translation = self.get_nested_value(
            self.translations.get(locale, {}),
            key
        )
        
        # Fallback to default locale
        if not translation and locale != self.default_locale:
            translation = self.get_nested_value(
                self.translations.get(self.default_locale, {}),
                key
            )
        
        # Fallback to key itself
        if not translation:
            translation = key
        
        # Format with kwargs
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Translation formatting error for key '{key}': {str(e)}")
        
        return translation
    
    def get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[str]:
        """Get nested value from dictionary using dot notation"""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def format_date(self, date_obj: datetime, format_type: str = 'medium', locale: str = None) -> str:
        """Format date according to locale"""
        if not locale:
            locale = self.get_locale()
        
        try:
            locale_obj = Locale(locale)
            return dates.format_date(date_obj, format=format_type, locale=locale_obj)
        except (UnknownLocaleError, ValueError) as e:
            logger.warning(f"Date formatting error for locale '{locale}': {str(e)}")
            return date_obj.strftime('%Y-%m-%d')
    
    def format_datetime(self, datetime_obj: datetime, format_type: str = 'medium', locale: str = None) -> str:
        """Format datetime according to locale"""
        if not locale:
            locale = self.get_locale()
        
        try:
            locale_obj = Locale(locale)
            return dates.format_datetime(datetime_obj, format=format_type, locale=locale_obj)
        except (UnknownLocaleError, ValueError) as e:
            logger.warning(f"Datetime formatting error for locale '{locale}': {str(e)}")
            return datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
    
    def format_time(self, time_obj: datetime, format_type: str = 'medium', locale: str = None) -> str:
        """Format time according to locale"""
        if not locale:
            locale = self.get_locale()
        
        try:
            locale_obj = Locale(locale)
            return dates.format_time(time_obj, format=format_type, locale=locale_obj)
        except (UnknownLocaleError, ValueError) as e:
            logger.warning(f"Time formatting error for locale '{locale}': {str(e)}")
            return time_obj.strftime('%H:%M:%S')
    
    def format_number(self, number: float, locale: str = None) -> str:
        """Format number according to locale"""
        if not locale:
            locale = self.get_locale()
        
        try:
            locale_obj = Locale(locale)
            return numbers.format_decimal(number, locale=locale_obj)
        except (UnknownLocaleError, ValueError) as e:
            logger.warning(f"Number formatting error for locale '{locale}': {str(e)}")
            return str(number)
    
    def format_currency(self, amount: float, currency: str = 'USD', locale: str = None) -> str:
        """Format currency according to locale"""
        if not locale:
            locale = self.get_locale()
        
        try:
            locale_obj = Locale(locale)
            return numbers.format_currency(amount, currency, locale=locale_obj)
        except (UnknownLocaleError, ValueError) as e:
            logger.warning(f"Currency formatting error for locale '{locale}': {str(e)}")
            return f"{currency} {amount:.2f}"
    
    def get_supported_locales(self) -> Dict[str, Dict[str, str]]:
        """Get supported locales"""
        return self.supported_locales

    def get_available_languages(self):
        """Backward-compatible alias used by older routes/templates."""
        return self.get_supported_locales()
    
    def is_rtl(self, locale: str = None) -> bool:
        """Check if locale is right-to-left"""
        if not locale:
            locale = self.get_locale()
        
        rtl_locales = ['ar', 'he', 'fa', 'ur']
        return locale in rtl_locales
    
    def get_timezone_offset(self, timezone: str) -> str:
        """Get timezone offset"""
        try:
            import pytz
            tz = pytz.timezone(timezone)
            offset = datetime.now(tz).utcoffset()
            hours = offset.total_seconds() // 3600
            return f"UTC{hours:+d}"
        except Exception as e:
            logger.warning(f"Timezone offset error for '{timezone}': {str(e)}")
            return "UTC"


class LocalizationService:
    """Localization service for content and UI"""
    
    def __init__(self):
        self.i18n_service = I18nService()
        self.content_localizations = {}
        
    def init_app(self, app):
        with app.app_context():
            self.load_content_localizations()
    
    def load_content_localizations(self):
        """Load content-specific localizations"""
        try:
            # Load mood translations
            mood_file = os.path.join(current_app.root_path, 'translations', 'moods.json')
            if os.path.exists(mood_file):
                with open(mood_file, 'r', encoding='utf-8') as f:
                    self.content_localizations['moods'] = json.load(f)
            
            # Load category translations
            category_file = os.path.join(current_app.root_path, 'translations', 'categories.json')
            if os.path.exists(category_file):
                with open(category_file, 'r', encoding='utf-8') as f:
                    self.content_localizations['categories'] = json.load(f)
            
            logger.info("Loaded content localizations")
            
        except Exception as e:
            logger.error(f"Error loading content localizations: {str(e)}")
    
    def localize_mood(self, mood: str, locale: str = None) -> str:
        """Localize mood name"""
        if not locale:
            locale = self.i18n_service.get_locale()
        
        moods = self.content_localizations.get('moods', {})
        return moods.get(locale, {}).get(mood, mood)
    
    def localize_category(self, category: str, locale: str = None) -> str:
        """Localize category name"""
        if not locale:
            locale = self.i18n_service.get_locale()
        
        categories = self.content_localizations.get('categories', {})
        return categories.get(locale, {}).get(category, category)
    
    def get_localized_moods(self, locale: str = None) -> Dict[str, str]:
        """Get all localized moods"""
        if not locale:
            locale = self.i18n_service.get_locale()
        
        moods = self.content_localizations.get('moods', {})
        return moods.get(locale, {})
    
    def get_localized_categories(self, locale: str = None) -> Dict[str, str]:
        """Get all localized categories"""
        if not locale:
            locale = self.i18n_service.get_locale()
        
        categories = self.content_localizations.get('categories', {})
        return categories.get(locale, {})


class TranslationService:
    """Translation service for dynamic content"""
    
    def __init__(self):
        self.auto_translate_enabled = False
        self.translation_api_key = None
        self.translation_service_name = None
        
    def init_app(self, app):
        with app.app_context():
            self.auto_translate_enabled = app.config.get('AUTO_TRANSLATE_ENABLED', False)
            self.translation_api_key = app.config.get('TRANSLATION_API_KEY')
            self.translation_service_name = app.config.get('TRANSLATION_SERVICE', 'google')
    
    def translate_text(self, text: str, target_locale: str, source_locale: str = 'en') -> Optional[str]:
        """Translate text using external service"""
        if not self.auto_translate_enabled or not self.translation_api_key:
            return None
        
        try:
            if self.translation_service_name == 'google':
                return self._translate_google(text, target_locale, source_locale)
            elif self.translation_service_name == 'deepl':
                return self._translate_deepl(text, target_locale, source_locale)
            else:
                logger.warning(f"Unsupported translation service: {self.translation_service_name}")
                return None
                
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return None
    
    def _translate_google(self, text: str, target_locale: str, source_locale: str) -> Optional[str]:
        """Translate using Google Translate API"""
        try:
            from google.cloud import translate_v2 as translate
            
            translate_client = translate.Client(api_key=self.translation_api_key)
            result = translate_client.translate(
                text,
                target_language=target_locale,
                source_language=source_locale
            )
            
            return result['translatedText']
            
        except ImportError:
            logger.error("Google Translate library not installed")
            return None
        except Exception as e:
            logger.error(f"Google Translate error: {str(e)}")
            return None
    
    def _translate_deepl(self, text: str, target_locale: str, source_locale: str) -> Optional[str]:
        """Translate using DeepL API"""
        try:
            import deepl
            
            translator = deepl.Translator(self.translation_api_key)
            result = translator.translate_text(
                text,
                target_lang=target_locale.upper(),
                source_lang=source_locale.upper()
            )
            
            return result.text
            
        except ImportError:
            logger.error("DeepL library not installed")
            return None
        except Exception as e:
            logger.error(f"DeepL error: {str(e)}")
            return None
    
    def detect_language(self, text: str) -> Optional[str]:
        """Detect language of text"""
        if not self.auto_translate_enabled or not self.translation_api_key:
            return None
        
        try:
            if self.translation_service_name == 'google':
                from google.cloud import translate_v2 as translate
                
                translate_client = translate.Client(api_key=self.translation_api_key)
                result = translate_client.detect_language(text)
                return result['language']
                
        except Exception as e:
            logger.error(f"Language detection error: {str(e)}")
            return None


class LocalePreferencesService:
    """User locale preferences service"""
    
    @staticmethod
    def get_user_locale_preferences(user_id: int) -> Dict[str, Any]:
        """Get user's locale preferences"""
        try:
            from app.models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return {}
            
            return {
                'language': user.preferred_language or 'en',
                'timezone': user.timezone or 'UTC',
                'date_format': user.date_format or 'medium',
                'time_format': user.time_format or '24h',
                'number_format': user.number_format or 'default',
                'currency': user.currency or 'USD'
            }
            
        except Exception as e:
            logger.error(f"Get locale preferences error: {str(e)}")
            return {}
    
    @staticmethod
    def update_user_locale_preferences(user_id: int, preferences: Dict[str, Any]) -> bool:
        """Update user's locale preferences"""
        try:
            from app.models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Update preferences
            if 'language' in preferences:
                user.preferred_language = preferences['language']
            if 'timezone' in preferences:
                user.timezone = preferences['timezone']
            if 'date_format' in preferences:
                user.date_format = preferences['date_format']
            if 'time_format' in preferences:
                user.time_format = preferences['time_format']
            if 'number_format' in preferences:
                user.number_format = preferences['number_format']
            if 'currency' in preferences:
                user.currency = preferences['currency']
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Update locale preferences error: {str(e)}")
            db.session.rollback()
            return False


# Template filters for Jinja2
i18n_service = I18nService()
localization_service = LocalizationService()
translation_service = TranslationService()
locale_preferences_service = LocalePreferencesService()

def translate_filter(key: str, **kwargs) -> str:
    """Jinja2 filter for translation"""
    # This will now use the global i18n_service instance
    return i18n_service.translate(key, **kwargs)


def format_date_filter(date_obj: datetime, format_type: str = 'medium') -> str:
    """Jinja2 filter for date formatting"""
    return i18n_service.format_date(date_obj, format_type)


def format_datetime_filter(datetime_obj: datetime, format_type: str = 'medium') -> str:
    """Jinja2 filter for datetime formatting"""
    return i18n_service.format_datetime(datetime_obj, format_type)


def format_number_filter(number: float) -> str:
    """Jinja2 filter for number formatting"""
    return i18n_service.format_number(number)


def format_currency_filter(amount: float, currency: str = 'USD') -> str:
    """Jinja2 filter for currency formatting"""
    return i18n_service.format_currency(amount, currency)

    return i18n_service.format_datetime(datetime_obj, format_type)


def format_number_filter(number: float) -> str:
    """Jinja2 filter for number formatting"""
    return i18n_service.format_number(number)


def format_currency_filter(amount: float, currency: str = 'USD') -> str:
    """Jinja2 filter for currency formatting"""
    return i18n_service.format_currency(amount, currency)


class LocalizationService:
    """Localization service for content and UI"""
    
    def __init__(self):
        self.i18n_service = I18nService()
        self.content_localizations = {}
        
    def init_app(self, app):
        with app.app_context():
            self.load_content_localizations()
    
    def load_content_localizations(self):
        """Load content-specific localizations"""
        try:
            # Load mood translations
            mood_file = os.path.join(current_app.root_path, 'translations', 'moods.json')
            if os.path.exists(mood_file):
                with open(mood_file, 'r', encoding='utf-8') as f:
                    self.content_localizations['moods'] = json.load(f)
            
            # Load category translations
            category_file = os.path.join(current_app.root_path, 'translations', 'categories.json')
            if os.path.exists(category_file):
                with open(category_file, 'r', encoding='utf-8') as f:
                    self.content_localizations['categories'] = json.load(f)
            
            logger.info("Loaded content localizations")
        except Exception as e:
            logger.error(f"Error loading content localizations: {str(e)}")
    
    def localize_mood(self, mood: str, locale: str = None) -> str:
        """Localize mood name"""
        if not locale:
            locale = self.i18n_service.get_locale()
        
        if 'moods' in self.content_localizations:
            mood_translations = self.content_localizations['moods']
            if locale in mood_translations and mood in mood_translations[locale]:
                return mood_translations[locale][mood]
        
        return mood.title()
    

    def localize_category(self, category: str, locale: str = None) -> str:
        """Localize category name"""
        if not locale:
            locale = self.i18n_service.get_locale()
        
        categories = self.content_localizations.get('categories', {})
        return categories.get(locale, {}).get(category, category)

    

    def get_localized_moods(self, locale: str = None) -> Dict[str, str]:

        """Get all localized moods"""

        if not locale:

            locale = self.i18n_service.get_locale()

        

        moods = self.content_localizations.get('moods', {})

        return moods.get(locale, {})

    

    def get_localized_categories(self, locale: str = None) -> Dict[str, str]:

        """Get all localized categories"""

        if not locale:

            locale = self.i18n_service.get_locale()

        

        categories = self.content_localizations.get('categories', {})

        return categories.get(locale, {})





class TranslationService:

    """Translation service for dynamic content"""

    

    def __init__(self):

        self.auto_translate_enabled = current_app.config.get('AUTO_TRANSLATE_ENABLED', False)

        self.translation_api_key = current_app.config.get('TRANSLATION_API_KEY')

        self.translation_service = current_app.config.get('TRANSLATION_SERVICE', 'google')

    

    def translate_text(self, text: str, target_locale: str, source_locale: str = 'en') -> Optional[str]:

        """Translate text using external service"""

        if not self.auto_translate_enabled or not self.translation_api_key:

            return None

        

        try:

            if self.translation_service == 'google':

                return self._translate_google(text, target_locale, source_locale)

            elif self.translation_service == 'deepl':

                return self._translate_deepl(text, target_locale, source_locale)

            else:

                logger.warning(f"Unsupported translation service: {self.translation_service}")

                return None

                

        except Exception as e:

            logger.error(f"Translation error: {str(e)}")

            return None

    

    def _translate_google(self, text: str, target_locale: str, source_locale: str) -> Optional[str]:

        """Translate using Google Translate API"""

        try:

            from google.cloud import translate_v2 as translate

            

            translate_client = translate.Client(api_key=self.translation_api_key)

            result = translate_client.translate(

                text,

                target_language=target_locale,

                source_language=source_locale

            )

            

            return result['translatedText']

            

        except ImportError:

            logger.error("Google Translate library not installed")

            return None

        except Exception as e:

            logger.error(f"Google Translate error: {str(e)}")

            return None

    

    def _translate_deepl(self, text: str, target_locale: str, source_locale: str) -> Optional[str]:

        """Translate using DeepL API"""

        try:

            import deepl

            

            translator = deepl.Translator(self.translation_api_key)

            result = translator.translate_text(

                text,

                target_lang=target_locale.upper(),

                source_lang=source_locale.upper()

            )

            

            return result.text

            

        except ImportError:

            logger.error("DeepL library not installed")

            return None

        except Exception as e:

            logger.error(f"DeepL error: {str(e)}")

            return None

    

    def detect_language(self, text: str) -> Optional[str]:

        """Detect language of text"""

        if not self.auto_translate_enabled or not self.translation_api_key:

            return None

        

        try:

            if self.translation_service == 'google':

                from google.cloud import translate_v2 as translate

                

                translate_client = translate.Client(api_key=self.translation_api_key)

                result = translate_client.detect_language(text)

                return result['language']

                

        except Exception as e:

            logger.error(f"Language detection error: {str(e)}")

            return None





class LocalePreferencesService:

    """User locale preferences service"""

    

    @staticmethod

    def get_user_locale_preferences(user_id: int) -> Dict[str, Any]:

        """Get user's locale preferences"""

        try:

            from app.models.user import User

            

            user = User.query.get(user_id)

            if not user:

                return {}

            

            return {

                'language': user.preferred_language or 'en',

                'timezone': user.timezone or 'UTC',

                'date_format': user.date_format or 'medium',

                'time_format': user.time_format or '24h',

                'number_format': user.number_format or 'default',

                'currency': user.currency or 'USD'

            }

            

        except Exception as e:

            logger.error(f"Get locale preferences error: {str(e)}")

            return {}

    

    @staticmethod

    def update_user_locale_preferences(user_id: int, preferences: Dict[str, Any]) -> bool:

        """Update user's locale preferences"""

        try:

            from app.models.user import User

            

            user = User.query.get(user_id)

            if not user:

                return False

            

            # Update preferences

            if 'language' in preferences:

                user.preferred_language = preferences['language']

            if 'timezone' in preferences:

                user.timezone = preferences['timezone']

            if 'date_format' in preferences:

                user.date_format = preferences['date_format']

            if 'time_format' in preferences:

                user.time_format = preferences['time_format']

            if 'number_format' in preferences:

                user.number_format = preferences['number_format']

            if 'currency' in preferences:

                user.currency = preferences['currency']

            

            db.session.commit()

            return True

            

        except Exception as e:

            logger.error(f"Update locale preferences error: {str(e)}")

            db.session.rollback()

            return False





# Template filters for Jinja2

def translate_filter(key: str, **kwargs) -> str:

    """Jinja2 filter for translation"""

    i18n_service = I18nService()

    return i18n_service.translate(key, **kwargs)





def format_date_filter(date_obj: datetime, format_type: str = 'medium') -> str:

    """Jinja2 filter for date formatting"""

    i18n_service = I18nService()

    return i18n_service.format_date(date_obj, format_type)





def format_datetime_filter(datetime_obj: datetime, format_type: str = 'medium') -> str:

    """Jinja2 filter for datetime formatting"""

    i18n_service = I18nService()

    return i18n_service.format_datetime(datetime_obj, format_type)





def format_number_filter(number: float) -> str:

    """Jinja2 filter for number formatting"""

    i18n_service = I18nService()

    return i18n_service.format_number(number)





def format_currency_filter(amount: float, currency: str = 'USD') -> str:

    """Jinja2 filter for currency formatting"""

    i18n_service = I18nService()

    return i18n_service.format_currency(amount, currency)

# Services will be initialized lazily when needed



