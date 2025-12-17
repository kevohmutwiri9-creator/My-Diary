from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.services.media_service import save_media

media_bp = Blueprint('media', __name__, url_prefix='/media')

@media_bp.route('/health')
def health():
    return {'status': 'ok'}, 200


@media_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'GET':
        return (
            "<html><body><h1>Upload</h1>"
            "<form method='post' enctype='multipart/form-data'>"
            "<input type='file' name='file' required />"
            "<button type='submit'>Upload</button>"
            "</form></body></html>",
            200,
        )

    file = request.files.get('file')
    entry_id = request.form.get('entry_id')
    try:
        entry_id = int(entry_id) if entry_id not in (None, '') else None
    except (TypeError, ValueError):
        entry_id = None

    media, error = save_media(file, user_id=current_user.id, entry_id=entry_id)
    if error:
        return jsonify({'error': error}), 400

    return jsonify({'media': media.to_dict()}), 200
