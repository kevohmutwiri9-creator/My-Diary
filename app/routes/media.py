from flask import Blueprint

media_bp = Blueprint('media', __name__, url_prefix='/media')

@media_bp.route('/health')
def health():
    return {'status': 'ok'}, 200
