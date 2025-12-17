from flask import Blueprint
security_bp = Blueprint('security', __name__, url_prefix='/security')


@security_bp.route('/health')
def health():
    return {'status': 'ok'}, 200

