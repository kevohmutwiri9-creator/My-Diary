#!/usr/bin/env python
"""Validate dashboard template."""
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import os

def validate_template():
    """Validate the dashboard template."""
    templates_dir = 'templates'
    env = Environment(loader=FileSystemLoader(templates_dir))

    # Register the markdown filter like in the Flask app
    from app.utils.filters import markdown_to_html
    env.filters['markdown_to_html'] = markdown_to_html

    try:
        template = env.get_template('dashboard.html')
        print('✅ Dashboard template loaded successfully')
        print(f'Template name: {template.name}')
        print(f'Template filename: {template.filename}')
        return True
    except TemplateNotFound as e:
        print(f'❌ Template not found: {e}')
        return False
    except Exception as e:
        print(f'❌ Template error: {e}')
        return False

if __name__ == '__main__':
    validate_template()
