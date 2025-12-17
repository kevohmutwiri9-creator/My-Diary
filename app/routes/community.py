from flask import Blueprint, render_template

community_bp = Blueprint('community', __name__, url_prefix='/community')

@community_bp.route('/')
def home():
    try:
        return render_template('community/home.html')
    except Exception:
        return "Community page coming soon.", 200


@community_bp.route('/health')
def health():
    return {'status': 'ok'}, 200

