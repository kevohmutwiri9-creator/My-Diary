from markdown import markdown
import bleach
from bleach.css_sanitizer import CSSSanitizer
from flask import current_app
import itertools

# Markdown and HTML sanitization settings
ALLOWED_TAGS = {
    *bleach.sanitizer.ALLOWED_TAGS,
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'pre', 'code', 'hr',
    'span', 'div', 'blockquote', 'img', 'a', 'ul', 'ol', 'li', 'strong',
    'em', 'u', 's', 'sub', 'sup', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
}

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title'],
    '*': ['class', 'id', 'style'],
}

CSS_SANITIZER = CSSSanitizer(
    allowed_css_properties=[
        'color', 'background-color', 'font-weight', 'font-style', 'text-decoration',
        'text-align', 'margin', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
        'padding', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right'
    ],
    allowed_svg_properties=[],
)

def markdown_to_html(content):
    """Convert markdown to safe HTML."""
    try:
        if not content:
            current_app.logger.debug('Empty content provided to markdown_to_html')
            return ""
            
        current_app.logger.debug('Converting markdown to HTML')
        # Convert markdown to HTML
        html = markdown(content, extensions=[
            'extra',
            'codehilite',
            'tables',
            'fenced_code',
            'nl2br',
            'sane_lists'
        ])
        # Sanitize HTML to prevent XSS
        clean_html = bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            css_sanitizer=CSS_SANITIZER
        )
        return clean_html
    except Exception as e:
        current_app.logger.error(f'Error converting markdown to HTML: {str(e)}', exc_info=True)
        return "<p>Error rendering content</p>"

def zip_filter(*iterables):
    """Zip filter for Jinja2 templates - combines multiple iterables."""
    try:
        return zip(*iterables)
    except Exception as e:
        current_app.logger.error(f'Error in zip filter: {str(e)}')
        return []

def datetimefilter(value, format='%Y-%m-%d %H:%M'):
    """Format datetime for display."""
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    return value.strftime(format)
