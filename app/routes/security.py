from flask import Blueprint
from flask_login import login_required

security_bp = Blueprint('security', __name__, url_prefix='/security')


@security_bp.route('/health')
def health():
    return {'status': 'ok'}, 200


@security_bp.route('/settings')
@login_required
def security_settings():
    return "Security settings coming soon.", 200

