"""AdSense integration service for managing advertisements."""

import logging
from flask import current_app, session
from datetime import datetime, timedelta

class AdSenseService:
    """Service for managing Google AdSense integration."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def is_ads_enabled(self, user=None):
        """Check if ads should be displayed for the current user/session."""
        
        # Check if AdSense is configured
        if not current_app.config.get('ADSENSE_CLIENT_ID'):
            return False
        
        # If no user provided, check session
        if user is None:
            return session.get('allow_ads', False)
        
        # Check user preference
        return getattr(user, 'allow_ads', False)
    
    def get_ad_config(self):
        """Get AdSense configuration."""
        return {
            'client_id': current_app.config.get('ADSENSE_CLIENT_ID'),
            'slot_id': current_app.config.get('ADSENSE_SLOT_ID'),
            'enabled': bool(current_app.config.get('ADSENSE_CLIENT_ID'))
        }
    
    def should_show_ad(self, ad_type, user=None, context=None):
        """Determine if a specific ad type should be shown."""
        
        if not self.is_ads_enabled(user):
            return False
        
        # Different ad placement rules
        ad_rules = {
            'dashboard': self._should_show_dashboard_ad,
            'sidebar': self._should_show_sidebar_ad,
            'in_feed': self._should_show_in_feed_ad,
            'footer': self._should_show_footer_ad,
            'header': self._should_show_header_ad
        }
        
        rule_func = ad_rules.get(ad_type, lambda u, c: False)
        return rule_func(user, context)
    
    def _should_show_dashboard_ad(self, user, context):
        """Rules for dashboard ads."""
        if not user:
            return False
        
        # Only show if user has entries
        entry_count = context.get('entry_count', 0) if context else 0
        return entry_count > 0
    
    def _should_show_sidebar_ad(self, user, context):
        """Rules for sidebar ads."""
        return True  # Always show if ads enabled
    
    def _should_show_in_feed_ad(self, user, context):
        """Rules for in-feed ads."""
        return True  # Always show if ads enabled
    
    def _should_show_footer_ad(self, user, context):
        """Rules for footer ads."""
        return True  # Always show if ads enabled
    
    def _should_show_header_ad(self, user, context):
        """Rules for header ads."""
        return False  # Typically don't show header ads
    
    def get_ad_attributes(self, ad_type, slot_override=None):
        """Get ad attributes for a specific ad type."""
        config = self.get_ad_config()
        
        if not config['enabled']:
            return {}
        
        base_attrs = {
            'class': 'adsbygoogle',
            'style': 'display:block'
        }
        
        # Ad type specific configurations
        ad_configs = {
            'dashboard': {
                'data-ad-client': config['client_id'],
                'data-ad-slot': slot_override or config['slot_id'],
                'data-ad-format': 'auto',
                'data-full-width-responsive': 'true'
            },
            'sidebar': {
                'data-ad-client': config['client_id'],
                'data-ad-slot': 'sidebar-skyscraper',
                'data-ad-format': 'vertical',
                'data-full-width-responsive': 'true'
            },
            'in_feed': {
                'data-ad-client': config['client_id'],
                'data-ad-slot': 'in-feed-ads',
                'data-ad-format': 'fluid',
                'data-full-width-responsive': 'true'
            },
            'footer': {
                'data-ad-client': config['client_id'],
                'data-ad-slot': 'footer-banner',
                'data-ad-format': 'auto',
                'data-full-width-responsive': 'true'
            }
        }
        
        attrs = ad_configs.get(ad_type, ad_configs['dashboard'])
        base_attrs.update(attrs)
        
        return base_attrs
    
    def render_ad(self, ad_type, user=None, context=None, **kwargs):
        """Render an ad unit."""
        if not self.should_show_ad(ad_type, user, context):
            return ''
        
        attrs = self.get_ad_attributes(ad_type, kwargs.get('slot_override'))
        
        # Build HTML
        attr_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items()])
        
        html = f'''
        <div class="ad-container ad-{ad_type}" data-ad-type="{ad_type}">
            <small class="text-muted d-block mb-2 text-center">Advertisement</small>
            <ins {attr_str}></ins>
        </div>
        '''
        
        return html
    
    def update_user_preference(self, user, allow_ads):
        """Update user's ad preference."""
        try:
            user.allow_ads = allow_ads
            from app import db
            db.session.commit()
            
            # Update session
            session['allow_ads'] = allow_ads
            
            self.logger.info(f"Updated ad preference for user {user.id}: {allow_ads}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update ad preference: {str(e)}")
            return False
    
    def get_ad_stats(self, user=None):
        """Get ad-related statistics."""
        stats = {
            'ads_enabled': self.is_ads_enabled(user),
            'total_impressions': 0,  # Would be tracked in database
            'total_clicks': 0,      # Would be tracked in database
            'revenue': 0.0,         # Would be calculated from AdSense API
            'last_updated': datetime.utcnow().isoformat()
        }
        
        return stats
    
    def validate_adSense_config(self):
        """Validate AdSense configuration."""
        config = self.get_ad_config()
        
        errors = []
        
        if not config['client_id']:
            errors.append("ADSENSE_CLIENT_ID not configured")
        
        if not config['client_id'].startswith('ca-pub-'):
            errors.append("ADSENSE_CLIENT_ID format is invalid (should start with 'ca-pub-')")
        
        if len(config['client_id']) < 20:
            errors.append("ADSENSE_CLIENT_ID appears to be too short")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'config': config
        }
    
    def get_ad_blocking_status(self):
        """Check if ad blocking is detected."""
        # This would typically be implemented with JavaScript
        # For now, return a placeholder
        return {
            'detected': False,
            'message': 'Ad blocking detection not implemented'
        }
    
    def get_ad_safety_settings(self):
        """Get ad safety and content filtering settings."""
        return {
            'safe_for_work': True,
            'content_filtering': True,
            'adult_content': False,
            'violence_content': False,
            'political_content': False
        }

# Create global instance
adsense_service = AdSenseService()
