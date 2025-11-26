import json
import os
from typing import Dict, Optional, Any
from flask import session, request
from datetime import datetime

# Translation data (simplified - in production, use proper i18n framework)
TRANSLATIONS = {
    'en': {
        'common': {
            'save': 'Save',
            'cancel': 'Cancel',
            'delete': 'Delete',
            'edit': 'Edit',
            'close': 'Close',
            'loading': 'Loading...',
            'error': 'Error',
            'success': 'Success',
            'warning': 'Warning',
            'info': 'Information',
            'yes': 'Yes',
            'no': 'No',
            'ok': 'OK',
            'search': 'Search',
            'filter': 'Filter',
            'settings': 'Settings',
            'profile': 'Profile',
            'logout': 'Logout',
            'back': 'Back',
            'next': 'Next',
            'previous': 'Previous',
            'submit': 'Submit',
            'confirm': 'Confirm'
        },
        'navigation': {
            'dashboard': 'Dashboard',
            'productivity': 'Productivity',
            'community': 'Community',
            'calendar': 'Calendar',
            'new_entry': 'New Entry',
            'privacy_settings': 'Privacy Settings',
            'security_settings': 'Security Settings'
        },
        'diary': {
            'title': 'My Diary',
            'entry_title': 'Entry Title',
            'your_thoughts': 'Your Thoughts',
            'mood': 'Mood',
            'tags': 'Tags',
            'private': 'Private',
            'public': 'Public',
            'save_entry': 'Save Entry',
            'save_draft': 'Save Draft',
            'word_count': 'Word Count',
            'character_count': 'Character Count'
        },
        'moods': {
            'happy': '😊 Happy',
            'sad': '😢 Sad',
            'angry': '😡 Angry',
            'tired': '😴 Tired',
            'excited': '😃 Excited',
            'anxious': '😰 Anxious',
            'grateful': '🙏 Grateful',
            'peaceful': '😌 Peaceful'
        },
        'dashboard': {
            'welcome': 'Welcome back',
            'recent_entries': 'Recent Entries',
            'mood_heatmap': 'Mood Heatmap',
            'productivity_pulse': 'Productivity Pulse',
            'writing_patterns': 'Writing Patterns',
            'insights': 'Insights',
            'statistics': 'Statistics',
            'streak': 'Streak',
            'total_entries': 'Total Entries',
            'this_month': 'This Month'
        },
        'productivity': {
            'productivity_dashboard': 'Productivity Dashboard',
            'productivity_score': 'Productivity Score',
            'current_streak': 'Current Streak',
            'longest_streak': 'Longest Streak',
            'daily_goal': 'Daily Goal',
            'weekly_goal': 'Weekly Goal',
            'writing_patterns': 'Writing Patterns',
            'most_productive_time': 'Most Productive Time',
            'recommendations': 'Recommendations',
            'set_goals': 'Set Your Writing Goals'
        },
        'community': {
            'community_feed': 'Community Feed',
            'anonymous': 'Anonymous',
            'share_to_community': 'Share to Community',
            'trending_topics': 'Trending Topics',
            'inspiration': 'Need Writing Inspiration?',
            'recent_public_entries': 'Recent Public Entries',
            'like': 'Like',
            'report': 'Report',
            'views': 'views',
            'words': 'words'
        },
        'security': {
            'security_settings': 'Security Settings',
            'two_factor_auth': 'Two-Factor Authentication',
            'enable_2fa': 'Enable 2FA',
            'disable_2fa': 'Disable 2FA',
            'data_encryption': 'Data Encryption',
            'backup_restore': 'Backup & Restore',
            'create_backup': 'Create Backup',
            'restore_backup': 'Restore Backup',
            'account_status': 'Account Security Status'
        },
        'privacy': {
            'privacy_settings': 'Privacy Settings',
            'community_sharing': 'Community & Sharing',
            'default_privacy': 'Default Privacy',
            'auto_share_anonymous': 'Auto-share Anonymous Entries',
            'show_in_community': 'Show in Community',
            'allow_public_search': 'Allow Public Search'
        },
        'messages': {
            'entry_saved': 'Your diary entry has been saved!',
            'entry_deleted': 'Entry deleted successfully',
            'settings_updated': 'Settings updated successfully',
            'password_changed': 'Password changed successfully',
            'login_required': 'Please log in to continue',
            'access_denied': 'Access denied',
            'not_found': 'Page not found',
            'server_error': 'Server error occurred',
            'network_error': 'Network error occurred'
        },
        'validation': {
            'required_field': 'This field is required',
            'invalid_email': 'Please enter a valid email address',
            'password_too_short': 'Password must be at least 12 characters long',
            'passwords_dont_match': 'Passwords do not match',
            'invalid_date': 'Please enter a valid date',
            'invalid_number': 'Please enter a valid number',
            'file_too_large': 'File size exceeds limit',
            'invalid_file_type': 'Invalid file type'
        },
        'dates': {
            'today': 'Today',
            'yesterday': 'Yesterday',
            'tomorrow': 'Tomorrow',
            'this_week': 'This Week',
            'last_week': 'Last Week',
            'this_month': 'This Month',
            'last_month': 'Last Month',
            'this_year': 'This Year',
            'last_year': 'Last Year'
        }
    },
    'es': {
        'common': {
            'save': 'Guardar',
            'cancel': 'Cancelar',
            'delete': 'Eliminar',
            'edit': 'Editar',
            'close': 'Cerrar',
            'loading': 'Cargando...',
            'error': 'Error',
            'success': 'Éxito',
            'warning': 'Advertencia',
            'info': 'Información',
            'yes': 'Sí',
            'no': 'No',
            'ok': 'OK',
            'search': 'Buscar',
            'filter': 'Filtrar',
            'settings': 'Configuración',
            'profile': 'Perfil',
            'logout': 'Cerrar sesión',
            'back': 'Atrás',
            'next': 'Siguiente',
            'previous': 'Anterior',
            'submit': 'Enviar',
            'confirm': 'Confirmar'
        },
        'navigation': {
            'dashboard': 'Panel',
            'productivity': 'Productividad',
            'community': 'Comunidad',
            'calendar': 'Calendario',
            'new_entry': 'Nueva Entrada',
            'privacy_settings': 'Configuración de Privacidad',
            'security_settings': 'Configuración de Seguridad'
        },
        'diary': {
            'title': 'Mi Diario',
            'entry_title': 'Título de la Entrada',
            'your_thoughts': 'Tus Pensamientos',
            'mood': 'Estado de Ánimo',
            'tags': 'Etiquetas',
            'private': 'Privado',
            'public': 'Público',
            'save_entry': 'Guardar Entrada',
            'save_draft': 'Guardar Borrador',
            'word_count': 'Recuento de Palabras',
            'character_count': 'Recuento de Caracteres'
        },
        'moods': {
            'happy': '😊 Feliz',
            'sad': '😢 Triste',
            'angry': '😡 Enojado',
            'tired': '😴 Cansado',
            'excited': '😃 Emocionado',
            'anxious': '😰 Ansioso',
            'grateful': '🙏 Agradecido',
            'peaceful': '😌 Pacífico'
        },
        'dashboard': {
            'welcome': 'Bienvenido de nuevo',
            'recent_entries': 'Entradas Recientes',
            'mood_heatmap': 'Mapa de Calor de Ánimo',
            'productivity_pulse': 'Pulso de Productividad',
            'writing_patterns': 'Patrones de Escritura',
            'insights': 'Perspectivas',
            'statistics': 'Estadísticas',
            'streak': 'Racha',
            'total_entries': 'Total de Entradas',
            'this_month': 'Este Mes'
        },
        'productivity': {
            'productivity_dashboard': 'Panel de Productividad',
            'productivity_score': 'Puntuación de Productividad',
            'current_streak': 'Racha Actual',
            'longest_streak': 'Racha Más Larga',
            'daily_goal': 'Objetivo Diario',
            'weekly_goal': 'Objetivo Semanal',
            'writing_patterns': 'Patrones de Escritura',
            'most_productive_time': 'Hora Más Productiva',
            'recommendations': 'Recomendaciones',
            'set_goals': 'Establece Tus Objetivos de Escritura'
        },
        'community': {
            'community_feed': 'Feed de la Comunidad',
            'anonymous': 'Anónimo',
            'share_to_community': 'Compartir con la Comunidad',
            'trending_topics': 'Temas Trending',
            'inspiration': '¿Necesitas Inspiración para Escribir?',
            'recent_public_entries': 'Entradas Públicas Recientes',
            'like': 'Me gusta',
            'report': 'Reportar',
            'views': 'vistas',
            'words': 'palabras'
        },
        'security': {
            'security_settings': 'Configuración de Seguridad',
            'two_factor_auth': 'Autenticación de Dos Factores',
            'enable_2fa': 'Activar 2FA',
            'disable_2fa': 'Desactivar 2FA',
            'data_encryption': 'Cifrado de Datos',
            'backup_restore': 'Copia de Seguridad y Restauración',
            'create_backup': 'Crear Copia de Seguridad',
            'restore_backup': 'Restaurar Copia de Seguridad',
            'account_status': 'Estado de Seguridad de la Cuenta'
        },
        'privacy': {
            'privacy_settings': 'Configuración de Privacidad',
            'community_sharing': 'Comunidad y Compartir',
            'default_privacy': 'Privacidad Predeterminada',
            'auto_share_anonymous': 'Compartir Anónimamente',
            'show_in_community': 'Mostrar en Comunidad',
            'allow_public_search': 'Permitir Búsqueda Pública'
        },
        'messages': {
            'entry_saved': '¡Tu entrada de diario ha sido guardada!',
            'entry_deleted': 'Entrada eliminada exitosamente',
            'settings_updated': 'Configuración actualizada exitosamente',
            'password_changed': 'Contraseña cambiada exitosamente',
            'login_required': 'Por favor inicia sesión para continuar',
            'access_denied': 'Acceso denegado',
            'not_found': 'Página no encontrada',
            'server_error': 'Ocurrió un error del servidor',
            'network_error': 'Ocurrió un error de red'
        },
        'validation': {
            'required_field': 'Este campo es requerido',
            'invalid_email': 'Por favor ingresa un correo electrónico válido',
            'password_too_short': 'La contraseña debe tener al menos 12 caracteres',
            'passwords_dont_match': 'Las contraseñas no coinciden',
            'invalid_date': 'Por favor ingresa una fecha válida',
            'invalid_number': 'Por favor ingresa un número válido',
            'file_too_large': 'El tamaño del archivo excede el límite',
            'invalid_file_type': 'Tipo de archivo inválido'
        },
        'dates': {
            'today': 'Hoy',
            'yesterday': 'Ayer',
            'tomorrow': 'Mañana',
            'this_week': 'Esta Semana',
            'last_week': 'Semana Pasada',
            'this_month': 'Este Mes',
            'last_month': 'Mes Pasado',
            'this_year': 'Este Año',
            'last_year': 'Año Pasado'
        }
    },
    'fr': {
        'common': {
            'save': 'Sauvegarder',
            'cancel': 'Annuler',
            'delete': 'Supprimer',
            'edit': 'Modifier',
            'close': 'Fermer',
            'loading': 'Chargement...',
            'error': 'Erreur',
            'success': 'Succès',
            'warning': 'Avertissement',
            'info': 'Information',
            'yes': 'Oui',
            'no': 'Non',
            'ok': 'OK',
            'search': 'Rechercher',
            'filter': 'Filtrer',
            'settings': 'Paramètres',
            'profile': 'Profil',
            'logout': 'Déconnexion',
            'back': 'Retour',
            'next': 'Suivant',
            'previous': 'Précédent',
            'submit': 'Soumettre',
            'confirm': 'Confirmer'
        },
        'navigation': {
            'dashboard': 'Tableau de bord',
            'productivity': 'Productivité',
            'community': 'Communauté',
            'calendar': 'Calendrier',
            'new_entry': 'Nouvelle Entrée',
            'privacy_settings': 'Paramètres de Confidentialité',
            'security_settings': 'Paramètres de Sécurité'
        },
        'diary': {
            'title': 'Mon Journal',
            'entry_title': 'Titre de l\'Entrée',
            'your_thoughts': 'Vos Pensées',
            'mood': 'Humeur',
            'tags': 'Étiquettes',
            'private': 'Privé',
            'public': 'Public',
            'save_entry': 'Sauvegarder l\'Entrée',
            'save_draft': 'Sauvegarder le Brouillon',
            'word_count': 'Nombre de Mots',
            'character_count': 'Nombre de Caractères'
        },
        'moods': {
            'happy': '😊 Heureux',
            'sad': '😢 Triste',
            'angry': '😡 En colère',
            'tired': '😴 Fatigué',
            'excited': '😃 Excité',
            'anxious': '😰 Anxieux',
            'grateful': '🙏 Reconnaissant',
            'peaceful': '😌 Paisible'
        },
        'dashboard': {
            'welcome': 'Bon retour',
            'recent_entries': 'Entrées Récentes',
            'mood_heatmap': 'Carte de Chaleur de l\'Humeur',
            'productivity_pulse': 'Pouls de Productivité',
            'writing_patterns': 'Modèles d\'Écriture',
            'insights': 'Aperçus',
            'statistics': 'Statistiques',
            'streak': 'Série',
            'total_entries': 'Total des Entrées',
            'this_month': 'Ce Mois'
        },
        'productivity': {
            'productivity_dashboard': 'Tableau de Bord de Productivité',
            'productivity_score': 'Score de Productivité',
            'current_streak': 'Série Actuelle',
            'longest_streak': 'Plus Longue Série',
            'daily_goal': 'Objectif Quotidien',
            'weekly_goal': 'Objectif Hebdomadaire',
            'writing_patterns': 'Modèles d\'Écriture',
            'most_productive_time': 'Moment le Plus Productif',
            'recommendations': 'Recommandations',
            'set_goals': 'Définissez Vos Objectifs d\'Écriture'
        },
        'community': {
            'community_feed': 'Fil de la Communauté',
            'anonymous': 'Anonyme',
            'share_to_community': 'Partager avec la Communauté',
            'trending_topics': 'Sujets Tendances',
            'inspiration': 'Besoin d\'Inspiration pour Écrire?',
            'recent_public_entries': 'Entrées Publiques Récentes',
            'like': 'J\'aime',
            'report': 'Signaler',
            'views': 'vues',
            'words': 'mots'
        },
        'security': {
            'security_settings': 'Paramètres de Sécurité',
            'two_factor_auth': 'Authentification à Deux Facteurs',
            'enable_2fa': 'Activer 2FA',
            'disable_2fa': 'Désactiver 2FA',
            'data_encryption': 'Chiffrement des Données',
            'backup_restore': 'Sauvegarde et Restauration',
            'create_backup': 'Créer une Sauvegarde',
            'restore_backup': 'Restaurer une Sauvegarde',
            'account_status': 'État de Sécurité du Compte'
        },
        'privacy': {
            'privacy_settings': 'Paramètres de Confidentialité',
            'community_sharing': 'Communauté et Partage',
            'default_privacy': 'Confidentialité par Défaut',
            'auto_share_anonymous': 'Partager Anonymement',
            'show_in_community': 'Afficher dans la Communauté',
            'allow_public_search': 'Permettre la Recherche Publique'
        },
        'messages': {
            'entry_saved': 'Votre entrée de journal a été sauvegardée!',
            'entry_deleted': 'Entrée supprimée avec succès',
            'settings_updated': 'Paramètres mis à jour avec succès',
            'password_changed': 'Mot de passe changé avec succès',
            'login_required': 'Veuillez vous connecter pour continuer',
            'access_denied': 'Accès refusé',
            'not_found': 'Page non trouvée',
            'server_error': 'Une erreur serveur s\'est produite',
            'network_error': 'Une erreur réseau s\'est produite'
        },
        'validation': {
            'required_field': 'Ce champ est requis',
            'invalid_email': 'Veuillez entrer une adresse email valide',
            'password_too_short': 'Le mot de passe doit contenir au moins 12 caractères',
            'passwords_dont_match': 'Les mots de passe ne correspondent pas',
            'invalid_date': 'Veuillez entrer une date valide',
            'invalid_number': 'Veuillez entrer un nombre valide',
            'file_too_large': 'La taille du fichier dépasse la limite',
            'invalid_file_type': 'Type de fichier invalide'
        },
        'dates': {
            'today': 'Aujourd\'hui',
            'yesterday': 'Hier',
            'tomorrow': 'Demain',
            'this_week': 'Cette Semaine',
            'last_week': 'Semaine Dernière',
            'this_month': 'Ce Mois',
            'last_month': 'Mois Dernier',
            'this_year': 'Cette Année',
            'last_year': 'Année Dernière'
        }
    }
}

SUPPORTED_LANGUAGES = {
    'en': {'name': 'English', 'native_name': 'English'},
    'es': {'name': 'Spanish', 'native_name': 'Español'},
    'fr': {'name': 'French', 'native_name': 'Français'}
}

RTL_LANGUAGES = {'ar', 'he', 'fa', 'ur'}  # Right-to-left languages

def get_current_language() -> str:
    """Get current user language preference."""
    # Check session first
    if 'language' in session:
        return session['language']
    
    # Check user preference if logged in
    if hasattr(request, 'current_user') and request.current_user.is_authenticated:
        user_lang = getattr(request.current_user, 'preferred_language', None)
        if user_lang in SUPPORTED_LANGUAGES:
            return user_lang
    
    # Check browser preference
    if hasattr(request, 'accept_languages'):
        browser_lang = request.accept_languages.best_match(SUPPORTED_LANGUAGES.keys())
        if browser_lang:
            return browser_lang
    
    # Default to English
    return 'en'

def set_language(language: str) -> bool:
    """Set user language preference."""
    if language not in SUPPORTED_LANGUAGES:
        return False
    
    session['language'] = language
    
    # Update user preference if logged in
    if hasattr(request, 'current_user') and request.current_user.is_authenticated:
        request.current_user.preferred_language = language
        db.session.commit()
    
    return True

def translate(key: str, language: str = None, **kwargs) -> str:
    """Translate a key to the specified language."""
    if language is None:
        language = get_current_language()
    
    # Get translation dictionary
    translations = TRANSLATIONS.get(language, TRANSLATIONS['en'])
    
    # Navigate through nested keys (e.g., 'common.save')
    keys = key.split('.')
    value = translations
    
    try:
        for k in keys:
            value = value[k]
    except (KeyError, TypeError):
        # Fallback to English
        value = TRANSLATIONS['en']
        for k in keys:
            try:
                value = value[k]
            except (KeyError, TypeError):
                return key  # Return the key if not found
    
    # Handle string formatting with kwargs
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value
    
    return value

def get_language_direction(language: str = None) -> str:
    """Get text direction for language (ltr or rtl)."""
    if language is None:
        language = get_current_language()
    
    return 'rtl' if language in RTL_LANGUAGES else 'ltr'

def get_supported_languages() -> Dict[str, Dict[str, str]]:
    """Get list of supported languages."""
    return SUPPORTED_LANGUAGES

def format_date(date_obj: datetime, format_type: str = 'medium', language: str = None) -> str:
    """Format date according to language preferences."""
    if language is None:
        language = get_current_language()
    
    # Simplified date formatting - in production, use proper i18n library
    formats = {
        'en': {
            'short': '%m/%d/%Y',
            'medium': '%b %d, %Y',
            'long': '%B %d, %Y',
            'time': '%I:%M %p'
        },
        'es': {
            'short': '%d/%m/%Y',
            'medium': '%d de %b de %Y',
            'long': '%d de %B de %Y',
            'time': '%H:%M'
        },
        'fr': {
            'short': '%d/%m/%Y',
            'medium': '%d %b %Y',
            'long': '%d %B %Y',
            'time': '%H:%M'
        }
    }
    
    lang_formats = formats.get(language, formats['en'])
    format_string = lang_formats.get(format_type, lang_formats['medium'])
    
    return date_obj.strftime(format_string)

def format_number(number: float, format_type: str = 'decimal', language: str = None) -> str:
    """Format number according to language preferences."""
    if language is None:
        language = get_current_language()
    
    # Simplified number formatting - in production, use proper i18n library
    if language == 'en':
        return f"{number:,.2f}" if format_type == 'decimal' else f"{number:,}"
    elif language == 'es':
        return f"{number:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if format_type == 'decimal' else f"{number:,}".replace(',', 'X').replace('.', ',').replace('X', '.')
    elif language == 'fr':
        return f"{number:,.2f}".replace(',', ' ').replace('.', ',') if format_type == 'decimal' else f"{number:,}".replace(',', ' ')
    else:
        return str(number)

def get_currency_symbol(currency: str = 'USD', language: str = None) -> str:
    """Get currency symbol for language."""
    if language is None:
        language = get_current_language()
    
    symbols = {
        'en': {'USD': '$', 'EUR': '€', 'GBP': '£'},
        'es': {'USD': '$', 'EUR': '€', 'GBP': '£'},
        'fr': {'USD': '$', 'EUR': '€', 'GBP': '£'}
    }
    
    return symbols.get(language, symbols['en']).get(currency, '$')

def localize_content(content: str, language: str = None) -> str:
    """Localize content placeholders."""
    if language is None:
        language = get_current_language()
    
    # Replace common placeholders with localized versions
    replacements = {
        'en': {
            '{app_name}': 'My Diary',
            '{support_email}': 'support@mydiary.com'
        },
        'es': {
            '{app_name}': 'Mi Diario',
            '{support_email}': 'soporte@mydiary.com'
        },
        'fr': {
            '{app_name}': 'Mon Journal',
            '{support_email}': 'support@mydiary.com'
        }
    }
    
    lang_replacements = replacements.get(language, replacements['en'])
    
    for placeholder, replacement in lang_replacements.items():
        content = content.replace(placeholder, replacement)
    
    return content
