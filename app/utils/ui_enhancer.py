"""
UI/UX Enhancement System
Provides comprehensive UI improvements and user experience optimizations
"""

import re
from datetime import datetime
from flask import current_app, request
from typing import Dict, List, Any, Optional

class UIEnhancer:
    """Comprehensive UI/UX enhancement system"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize UI/UX enhancements"""
        # Add template context processors
        @app.context_processor
        def inject_ui_helpers():
            return {
                'ui_helper': UIHelper(),
                'format_date_ago': self.format_date_ago,
                'format_file_size': self.format_file_size,
                'get_theme_class': self.get_theme_class,
                'is_mobile': self.is_mobile_request,
                'get_animation_classes': self.get_animation_classes
            }
    
    def format_date_ago(self, date):
        """Format date as 'X time ago'"""
        if not date:
            return 'Never'
        
        now = datetime.utcnow()
        diff = now - date
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours} hour{"s" if hours != 1 else ""} ago'
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days} day{"s" if days != 1 else ""} ago'
        else:
            return date.strftime('%b %d, %Y')
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def get_theme_class(self):
        """Get current theme CSS classes"""
        theme = request.cookies.get('theme', 'light')
        return f'theme-{theme}'
    
    def is_mobile_request(self):
        """Check if request is from mobile device"""
        user_agent = request.headers.get('User-Agent', '').lower()
        mobile_patterns = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
        return any(pattern in user_agent for pattern in mobile_patterns)
    
    def get_animation_classes(self, animation_type='fade'):
        """Get animation CSS classes"""
        animations = {
            'fade': 'animate-fade-in',
            'slide': 'animate-slide-up',
            'bounce': 'animate-bounce-in',
            'scale': 'animate-scale-in'
        }
        return animations.get(animation_type, 'animate-fade-in')

class UIHelper:
    """UI helper functions for templates"""
    
    @staticmethod
    def get_mood_emoji(mood):
        """Get emoji for mood"""
        mood_emojis = {
            'happy': '😊',
            'sad': '😢',
            'angry': '😠',
            'anxious': '😰',
            'excited': '🎉',
            'grateful': '🙏',
            'peaceful': '😌',
            'motivated': '💪',
            'tired': '😴',
            'confused': '😕',
            'neutral': '😐'
        }
        return mood_emojis.get(mood.lower(), '😐')
    
    @staticmethod
    def get_mood_color(mood):
        """Get color for mood"""
        mood_colors = {
            'happy': 'success',
            'sad': 'info',
            'angry': 'danger',
            'anxious': 'warning',
            'excited': 'primary',
            'grateful': 'success',
            'peaceful': 'info',
            'motivated': 'primary',
            'tired': 'secondary',
            'confused': 'warning',
            'neutral': 'light'
        }
        return mood_colors.get(mood.lower(), 'secondary')
    
    @staticmethod
    def truncate_text(text, length=100, suffix='...'):
        """Truncate text to specified length"""
        if len(text) <= length:
            return text
        return text[:length].rsplit(' ', 1)[0] + suffix
    
    @staticmethod
    def word_count(text):
        """Count words in text"""
        if not text:
            return 0
        return len(re.findall(r'\b\w+\b', text))
    
    @staticmethod
    def reading_time(text):
        """Estimate reading time in minutes"""
        words = UIHelper.word_count(text)
        # Average reading speed: 200 words per minute
        minutes = max(1, round(words / 200))
        return f"{minutes} min read"
    
    @staticmethod
    def get_progress_percentage(current, total):
        """Calculate progress percentage"""
        if total == 0:
            return 0
        return round((current / total) * 100)
    
    @staticmethod
    def get_streak_badge(streak_count):
        """Get streak badge HTML"""
        if streak_count >= 30:
            return '<span class="badge bg-danger">🔥 {streak} days</span>'
        elif streak_count >= 14:
            return '<span class="badge bg-warning">⭐ {streak} days</span>'
        elif streak_count >= 7:
            return '<span class="badge bg-info">📈 {streak} days</span>'
        elif streak_count >= 3:
            return '<span class="badge bg-success">📝 {streak} days</span>'
        else:
            return '<span class="badge bg-secondary">{streak} days</span>'
    
    @staticmethod
    def format_search_highlight(text, query):
        """Highlight search query in text"""
        if not query:
            return text
        
        # Escape HTML special characters
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Highlight matching terms
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        highlighted = pattern.sub(f'<mark>{query}</mark>', text)
        
        return highlighted
    
    @staticmethod
    def get_entry_preview(entry, max_length=200):
        """Get formatted entry preview"""
        preview = entry.content
        if len(preview) > max_length:
            preview = preview[:max_length].rsplit(' ', 1)[0] + '...'
        
        # Add mood indicator
        mood_emoji = UIHelper.get_mood_emoji(entry.mood)
        
        return f"{mood_emoji} {preview}"
    
    @staticmethod
    def get_entry_tags_html(tags):
        """Get formatted tags HTML"""
        if not tags:
            return ''
        
        tag_html = []
        for tag in tags[:5]:  # Limit to 5 tags
            tag_html.append(f'<span class="badge bg-light text-dark me-1">#{tag.name}</span>')
        
        return ' '.join(tag_html)
    
    @staticmethod
    def get_activity_feed_html(activities):
        """Get formatted activity feed HTML"""
        feed_html = []
        
        for activity in activities[:10]:  # Show last 10 activities
            icon = UIHelper.get_activity_icon(activity['type'])
            time_ago = UIHelper.format_time_ago(activity['timestamp'])
            
            feed_html.append(f'''
                <div class="d-flex align-items-center mb-3">
                    <div class="me-3">{icon}</div>
                    <div class="flex-grow-1">
                        <div class="small">{activity['description']}</div>
                        <div class="text-muted tiny">{time_ago}</div>
                    </div>
                </div>
            ''')
        
        return ''.join(feed_html)
    
    @staticmethod
    def get_activity_icon(activity_type):
        """Get icon for activity type"""
        icons = {
            'entry_created': '📝',
            'entry_updated': '✏️',
            'entry_deleted': '🗑️',
            'goal_achieved': '🎯',
            'milestone_reached': '🏆',
            'login': '👤',
            'settings_updated': '⚙️'
        }
        return icons.get(activity_type, '📌')
    
    @staticmethod
    def format_time_ago(timestamp):
        """Format timestamp as time ago"""
        if not timestamp:
            return 'Never'
        
        now = datetime.utcnow()
        diff = now - timestamp
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'{minutes}m ago'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours}h ago'
        else:
            days = int(seconds / 86400)
            return f'{days}d ago'

class ResponsiveHelper:
    """Responsive design helper"""
    
    @staticmethod
    def get_grid_cols(items_count, max_cols=4):
        """Get optimal grid columns for item count"""
        if items_count <= 1:
            return 1
        elif items_count <= 2:
            return 2
        elif items_count <= 4:
            return min(items_count, max_cols)
        else:
            return max_cols
    
    @staticmethod
    def get_card_size(content_size='medium'):
        """Get appropriate card size based on content"""
        sizes = {
            'small': 'col-md-4 col-lg-3',
            'medium': 'col-md-6 col-lg-4',
            'large': 'col-md-8 col-lg-6',
            'full': 'col-12'
        }
        return sizes.get(content_size, 'col-md-6 col-lg-4')
    
    @staticmethod
    def get_breakpoint_class():
        """Get current breakpoint class"""
        user_agent = request.headers.get('User-Agent', '').lower()
        
        if 'mobile' in user_agent:
            return 'device-mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            return 'device-tablet'
        else:
            return 'device-desktop'

class AnimationHelper:
    """Animation and transition helper"""
    
    @staticmethod
    def get_transition_classes(transition_type='fade'):
        """Get transition CSS classes"""
        transitions = {
            'fade': 'transition-fade',
            'slide': 'transition-slide',
            'scale': 'transition-scale',
            'rotate': 'transition-rotate'
        }
        return transitions.get(transition_type, 'transition-fade')
    
    @staticmethod
    def get_animation_delay(index, base_delay=100):
        """Get staggered animation delay"""
        delay = index * base_delay
        return f'style="animation-delay: {delay}ms"'
    
    @staticmethod
    def get_loading_animation():
        """Get loading animation HTML"""
        return '''
            <div class="loading-spinner">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        '''

class AccessibilityHelper:
    """Accessibility enhancements"""
    
    @staticmethod
    def get_aria_labels(element_type, content):
        """Get appropriate ARIA labels"""
        labels = {
            'button': f"Button: {content}",
            'link': f"Link: {content}",
            'input': f"Input field: {content}",
            'menu': f"Menu: {content}",
            'navigation': f"Navigation: {content}"
        }
        return labels.get(element_type, content)
    
    @staticmethod
    def get_keyboard_shortcuts():
        """Get keyboard shortcuts help"""
        shortcuts = {
            'Ctrl+N': 'New Entry',
            'Ctrl+S': 'Save Entry',
            'Ctrl+F': 'Search',
            'Escape': 'Close Modal',
            'Enter': 'Submit Form',
            'Tab': 'Navigate',
            'Shift+Tab': 'Navigate Backwards'
        }
        return shortcuts
    
    @staticmethod
    def get_color_contrast_ratio(foreground, background):
        """Calculate color contrast ratio (simplified)"""
        # This is a simplified version - in production, use a proper color library
        return 4.5  # Assume good contrast for demo

# Initialize UI enhancer
ui_enhancer = UIEnhancer()
