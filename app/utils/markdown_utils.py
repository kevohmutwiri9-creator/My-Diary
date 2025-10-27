"""Markdown processing utilities."""
import markdown
import bleach
from flask import Markup

def allowed_tags():
    """Return a list of allowed HTML tags for markdown rendering."""
    return [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'b', 'i', 'strong', 'em', 'tt',
        'p', 'br', 'span', 'div', 'blockquote', 'code', 'hr',
        'ul', 'ol', 'li', 'dd', 'dt', 'dl',
        'img', 'a', 'sub', 'sup', 's', 'u', 'pre',
        'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ]

def allowed_attributes():
    """Return a dictionary of allowed HTML attributes."""
    return {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'div': ['class'],
        'span': ['class'],
        'code': ['class'],
        'pre': ['class'],
        'p': ['class'],
        'table': ['class', 'border', 'cellpadding', 'cellspacing'],
        'th': ['scope']
    }

def render_markdown(text):
    """Render markdown text to HTML with XSS protection."""
    if not text:
        return ''
    
    # Convert markdown to HTML
    html = markdown.markdown(
        text,
        extensions=[
            'fenced_code',
            'codehilite',
            'tables',
            'footnotes',
            'toc'
        ],
        output_format='html5'
    )
    
    # Clean HTML to prevent XSS
    cleaned_html = bleach.clean(
        html,
        tags=allowed_tags(),
        attributes=allowed_attributes(),
        protocols=['http', 'https', 'mailto', 'tel'],
        strip=True
    )
    
    return Markup(cleaned_html)

def sanitize_input(text):
    """Sanitize user input to prevent XSS and other attacks."""
    if not text:
        return ''
    return bleach.clean(text, strip=True)
